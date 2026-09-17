"""스텝을 맞춘 배치 비교를 **8블록**으로 다시 — 단일 블록으로는 분해능이 모자랐다.

§7: 9월 배치가 8월보다 높다. 8블록 평균으로 보면 경량 +16.1%p(p=0.025)로 **유의**하고
네이티브는 +5.4%p(p=0.55)로 아니다. 처리량으로 설명되는지 보려고 스텝을 맞춰 비교했는데,
체크포인트 단위로 저장된 전이 점수가 **b500000 한 블록 30에피소드뿐**이라 어느 비교도
유의하지 않았다(경량 +10.9%p, p=0.216). 즉 그 검정은 «설명되지 않는다» 를 보인 것이
아니라 **아무것도 가리지 못한** 것이다.

고칠 수 있다. 전 체크포인트를 8블록으로 평가하면 1,540회라 비싸지만, **스텝을 맞춘
그 한 점만** 평가하면 20런 × 7블록 = 140회면 된다(b500000 은 이미 있다). 재학습 없음.

방법: 팔마다 두 배치가 모두 도달한 공통 스텝 예산을 잡고(=8월 런들의 마지막 체크포인트
스텝의 최솟값), 런마다 **그 예산에 가장 가까운 체크포인트**를 골라 나머지 7블록에서
평가한다. 고른 체크포인트의 실제 스텝도 함께 기록해 정렬 오차를 눈으로 볼 수 있게 한다.

실행: .venv/Scripts/python.exe bench/run_step_aligned.py
"""
import glob
import io
import json
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "bench_results", "step_aligned")
PY_EXE = os.path.join(ROOT, ".venv", "Scripts", "python.exe")
EVAL = os.path.join(ROOT, "bench", "evaluate.py")
BLOCKS = (510000, 520000, 530000, 540000, 550000, 560000, 570000)
SRC = {
    ("clean", "8월"): ("bench_results/clean/eval_md__clean_s%d.json", range(1, 6)),
    ("clean", "9월"): ("bench_results/seeds6to10/eval_md__clean_s%d.json", range(6, 11)),
    ("nd", "8월"): ("bench_results/native_desktop/eval_md__nd_s%d.json", range(2, 7)),
    ("nd", "9월"): ("bench_results/seeds6to10/eval_md__nd_s%d.json", range(7, 12)),
}
EXP = {"clean": "clean_custom", "nd": "nd_md"}


def ckpts(path):
    f = os.path.join(ROOT, path)
    if not os.path.exists(f):
        return None
    rows = [r for r in json.load(io.open(f, encoding="utf-8")) if r["ckpt"] != "final.pt"]
    rows.sort(key=lambda r: r["global_step"])
    return rows


def main():
    os.makedirs(OUT, exist_ok=True)
    plan = []
    for tag in ("clean", "nd"):
        runs = {}
        for batch in ("8월", "9월"):
            pat, seeds = SRC[(tag, batch)]
            for s in seeds:
                r = ckpts(pat % s)
                if r:
                    runs[(batch, s)] = r
        # 공통 예산 = 8월 런들이 모두 도달한 최대 스텝
        aug = [v for (b, _), v in runs.items() if b == "8월"]
        budget = min(v[-1]["global_step"] for v in aug)
        print("[%s] 공통 스텝 예산 %.1f Msteps" % (tag, budget / 1e6))
        for (batch, s), rows in sorted(runs.items()):
            best = min(rows, key=lambda r: abs(r["global_step"] - budget))
            d = sorted(glob.glob(os.path.join(ROOT, "runs",
                                              "Intersection__%s__%d__*" % (EXP[tag], s))))
            if not d:
                print("  런 없음 %s s%d" % (tag, s))
                continue
            plan.append((tag, batch, s, best["ckpt"], best["global_step"],
                         os.path.join(d[0], "ckpt", best["ckpt"])))
            print("  %-6s %-4s s%-2d → %s (%.1fM, 예산 대비 %+.1fM)"
                  % (tag, batch, s, best["ckpt"], best["global_step"] / 1e6,
                     (best["global_step"] - budget) / 1e6))
    with io.open(os.path.join(OUT, "plan.json"), "w", encoding="utf-8") as f:
        json.dump([{"tag": t, "batch": b, "seed": s, "ckpt": c, "step": g}
                   for t, b, s, c, g, _ in plan], f, ensure_ascii=False, indent=1)

    if "--plan-only" in sys.argv:          # 계획만 확인하고 멈춘다
        print("--plan-only: 평가는 돌리지 않는다.")
        return 0
    total = len(plan) * len(BLOCKS)
    print("\n평가 %d회 (런 %d × 블록 %d). b500000 은 이미 있으므로 제외."
          % (total, len(plan), len(BLOCKS)))
    done = 0
    for tag, batch, s, ck, step, path in plan:
        for b in BLOCKS:
            out = os.path.join(OUT, "eval_md__%s_s%d__b%d.json" % (tag, s, b))
            done += 1
            if os.path.exists(out):
                continue
            if not os.path.exists(path):
                print("  체크포인트 없음: %s" % path)
                continue
            res = subprocess.run(
                [PY_EXE, EVAL, "--ckpt", path, "--target", "metadrive",
                 "--episodes", "30", "--seed", str(b), "--out", out],
                cwd=ROOT, capture_output=True, text=True,
                # ★ text=True 는 **콘솔 기본 코덱**(한국어 윈도우 = cp949)으로 푼다.
                #   자식이 UTF-8 로 한글을 찍으면 리더 스레드가 UnicodeDecodeError 로
                #   죽는다 — 본 프로세스는 살아서 «성공한 것처럼» 보이지만 실패 진단문을
                #   통째로 잃는다. 인코딩을 명시하고 깨진 바이트는 대체한다.
                encoding="utf-8", errors="replace",
                env=dict(os.environ, PYTHONUTF8="1"))
            print("  %s s%d b%d %s (%d/%d)"
                  % (tag, s, b, "OK" if res.returncode == 0 else "FAIL", done, total),
                  flush=True)
            if res.returncode != 0:
                print("    stderr: %s" % (res.stderr or "")[-400:], flush=True)
    print("STEPALIGNED_DONE")
    return 0


if __name__ == "__main__":
    sys.exit(main())
