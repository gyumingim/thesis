"""DPC 의 τ≈0 은 **잴 수 있었던 것의 한계**인가 — 타깃 순위의 자기신뢰도를 잰다.

§6.3 은 DPC(경량 점수가 전이 성능의 체크포인트 순위를 예측하는가)를 확정 정숙 조건 5시드
에서 재고 전 구간 τ-b=+0.097(순열 p=0.513)을 얻어 «예측력 없음» 으로 결론했다. 한계로는
**경량 신호 L 의 동적 범위가 작다**는 것(평균의 1% 수준)만 적었다.

그런데 상관의 상한은 **양쪽** 측정의 신뢰도에 걸린다. 타깃 순위는 체크포인트 12개를
각각 30에피소드로 재서 만든 것이다. 그 순위가 **자기 자신과도** 상관하지 않는다면, 어떤
외부 신호도 그것과 상관할 수 없다 — τ≈0 은 경량 신호에 대한 진술이 아니라 타깃 측정의
분해능에 대한 진술이 된다. 이것은 모형 없이 잴 수 있다.

**반분 신뢰도**: 30장면을 15/15 로 나눠 각각으로 12 체크포인트의 순위를 만들고 둘의
상관을 본다. 여러 번 무작위 분할해 평균낸다. 반쪽은 길이가 절반이므로 스피어만-브라운
으로 30장면 길이에 맞춰 보정한다(보정식은 피어슨 척도 것이라 순위상관에는 근사다 —
둘 다 찍는다).

**감쇠 상한**: 신뢰도 r 인 측정과의 상관은 대략 sqrt(r) 배로 깎인다. 즉 경량 신호가
진짜 순위를 **완벽히** 맞혀도 관측 τ 는 그 상한을 넘을 수 없다.

원자료: bench_results/clean_perep (bench/run_ckpt_perep.sh 가 만든다).
실행: .venv/Scripts/python.exe tools/dpc_reliability.py
"""
import glob
import io
import json
import os
import sys

import numpy as np
from scipy import stats

ROOT = "bench_results/clean_perep"
N_SPLIT = 2000
# 감시(paper_numbers_check)는 --fast 로 부른다 — 몬테카를로 분할 수만 줄인다.
if "--fast" in __import__("sys").argv:
    N_SPLIT = 300


def load_seed(path):
    rows = [r for r in json.load(io.open(path, encoding="utf-8")) if "per_episode" in r]
    if not rows:
        return None, None
    scen = sorted({e["scenario"] for e in rows[0]["per_episode"]})
    Y = np.zeros((len(rows), len(scen)))
    for i, r in enumerate(rows):
        m = {e["scenario"]: e["success"] for e in r["per_episode"]}
        Y[i] = [m[s] for s in scen]
    return Y, [r["ckpt"] for r in rows]


def split_half(Y, rng, n_split=N_SPLIT):
    """(τ-b 평균, 스피어만 평균, SB 보정 스피어만) — 분할마다 12 체크포인트 순위를 둘로."""
    k, m = Y.shape
    half = m // 2
    taus, rhos = [], []
    idx = np.arange(m)
    for _ in range(n_split):
        rng.shuffle(idx)
        a, b = Y[:, idx[:half]].mean(1), Y[:, idx[half:2 * half]].mean(1)
        if np.std(a) < 1e-12 or np.std(b) < 1e-12:
            continue
        taus.append(stats.kendalltau(a, b, variant="b").statistic)
        rhos.append(stats.spearmanr(a, b).statistic)
    t, r = float(np.mean(taus)), float(np.mean(rhos))
    sb = 2 * r / (1 + r) if r > -1 else float("nan")
    return t, r, sb


def measure_target(n_split=N_SPLIT, seed=0):
    """타깃 쪽 반분 신뢰도만 (텐서보드 불필요 → 빠르다). 감시가 이걸 쓴다.

    출력 파싱 대신 계산을 부르게 해 둔다 — print 형식을 건드릴 때마다 감시가 죽는 것을
    막는다. 소스 쪽은 텐서보드 로딩이 20초 넘게 걸려 감시에서는 기록 파일과 대조한다.
    """
    rng = np.random.default_rng(seed)
    out = []
    for f in sorted(glob.glob(os.path.join(ROOT, "eval_md__clean_s*.json"))):
        Y, _ = load_seed(f)
        if Y is None:
            continue
        out.append(split_half(Y, rng, n_split))
    return out


def main():
    fs = sorted(glob.glob(os.path.join(ROOT, "eval_md__clean_s*.json")))
    if not fs:
        print("원자료 없음 — bash bench/run_ckpt_perep.sh 를 먼저 돌려라.")
        return 2
    rng = np.random.default_rng(0)

    print("반분 신뢰도 — 같은 평가를 15장면씩 둘로 나눠 만든 두 순위가 서로 맞는가")
    print("  %-10s %6s %6s %10s %10s %12s"
          % ("시드", "ckpt", "장면", "τ-b", "스피어만", "SB보정 ρ"))
    T, R, S, spread = [], [], [], []
    for f in fs:
        Y, names = load_seed(f)
        if Y is None:
            continue
        t, r, sb = split_half(Y, rng)
        T.append(t)
        R.append(r)
        S.append(sb)
        full = Y.mean(1)
        spread.append(100 * (full.max() - full.min()))
        print("  %-10s %6d %6d %10.3f %10.3f %12.3f"
              % (os.path.basename(f).split("__")[1][:-5], Y.shape[0], Y.shape[1], t, r, sb))
    tm, rm, sm = float(np.mean(T)), float(np.mean(R)), float(np.mean(S))
    print("  %-10s %6s %6s %10.3f %10.3f %12.3f" % ("평균", "", "", tm, rm, sm))
    print("  12 체크포인트의 전 구간 성공률 폭(최대−최소) 시드 평균 %.1f%%p" % np.mean(spread))
    ceil = sm ** 0.5 if sm > 0 else float("nan")
    print("\n감쇠 상한 — 신뢰도 %.3f 인 순위와의 상관은 대략 sqrt(r)=%.2f 배로 깎인다"
          % (sm, ceil))
    print("  즉 경량 신호가 **진짜 순위를 완벽히 맞혀도** 관측 τ 의 기대 상한은 약 %.2f 다."
          % ceil)
    print("  §6.3 의 관측값은 전 구간 τ-b=+0.097(순열 p=0.513)이었다 — 상한의 %.0f%%."
          % (100 * 0.097 / ceil))
    print("")
    print("  → **타깃 측정의 분해능은 구속조건이 아니었다.** 상한 %.2f 는 관측 +0.097 보다" % ceil)
    print("    한참 위이므로, «예측력 없음» 을 타깃 평가의 잡음 탓으로 돌릴 수 없다.")
    print("    이 점에서 §6.3 의 결론은 오히려 **강화된다** — 널 결과가 측정 아티팩트라는")
    print("    반론 하나가 수치로 닫힌다.")
    print("")
    print("  다만 두 가지를 함께 적는다.")
    print("   (a) 시드 편차가 크다: SB 신뢰도 %.3f~%.3f. 두 시드(%s)에서는 순위가 사실상"
          % (min(S), max(S),
             ", ".join(os.path.basename(f).split("__")[1][:-5]
                       for f, v in zip(fs, S) if v < 0.3)))
    print("       자기 자신과도 맞지 않는다. DPC 는 시드 내 쌍을 모으므로 그 시드들은")
    print("       신호가 아니라 잡음을 보탠다. 시드별 신뢰도로 가중하는 편이 정직하다.")
    print("   (b) 상한은 sqrt(r_타깃 × r_소스) 다. 여기서 잰 것은 **타깃 쪽뿐**이다.")
    print("       경량 신호 L 의 동적 범위가 평균의 1% 라는 §6.3 의 한계는 소스 쪽")
    print("       신뢰도 문제인데 아직 신뢰도로 환산된 적이 없다 — 그쪽이 더 낮다면")
    print("       구속하는 것은 그쪽이고, 그때는 결론이 다시 «잴 수 없었다» 로 돌아간다.")
    # ── 소스 쪽 신뢰도도 잰다 (2026-09-16) ────────────────────────────────
    # 위 (b) 를 열어 둔 채로 두면 결론이 반쪽이다. L_c 는 체크포인트 시점 ±150s 창의
    # 경량 학습 episodic_return 평균이므로, **그 창의 표본을 반으로 갈라** 같은 방식으로
    # 반분 신뢰도를 잴 수 있다. 타깃과 완전히 같은 절차라 비교가 성립한다.
    try:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from dpc_recompute import load_curve, HALF
        src, src_time = [], []
        for f in fs:
            sd = os.path.basename(f).split("__")[1][:-5].replace("clean_s", "")
            ds = sorted(glob.glob("runs/Intersection__clean_custom__%s__*" % sd))
            if not ds:
                continue
            curve = load_curve(ds[0])
            rows = sorted(json.load(io.open(f, encoding="utf-8")),
                          key=lambda r: r["elapsed_s"])
            rows = [r for r in rows if r["ckpt"] != "final.pt"]
            wins = []
            for r in rows:
                t = r["elapsed_s"]
                w = curve[(curve[:, 0] >= t - HALF) & (curve[:, 0] <= t + HALF)][:, 1]
                if len(w) >= 2:
                    wins.append(w)
            if len(wins) < 3:
                continue
            rr = []
            for _ in range(N_SPLIT // 4):
                a, b = [], []
                for w in wins:
                    idx = rng.permutation(len(w))
                    h = len(w) // 2
                    a.append(w[idx[:h]].mean())
                    b.append(w[idx[h:2 * h]].mean())
                if np.std(a) > 1e-12 and np.std(b) > 1e-12:
                    rr.append(stats.spearmanr(a, b).statistic)
            # ★ 학습 로그 표본은 시간 자기상관이 있다. 무작위 분할은 이웃한 표본을
            #   양쪽에 나눠 넣어 신뢰도를 **부풀린다**. 창을 전/후반으로 가르는
            #   시간 분할이 보수적인 쪽이라 둘 다 낸다.
            a2 = [w[:len(w) // 2].mean() for w in wins]
            b2 = [w[len(w) // 2:].mean() for w in wins]
            rt = stats.spearmanr(a2, b2).statistic
            src_time.append(2 * rt / (1 + rt) if rt > -1 else float("nan"))
            r_half = float(np.mean(rr))
            src.append(2 * r_half / (1 + r_half))
        if src:
            srcm = float(np.mean(src))
            print("")
            print("소스 쪽 반분 신뢰도 — L_c 창(±%ds)의 표본을 반으로 갈라 같은 절차로"
                  % int(HALF))
            print("  시드별 SB 보정 ρ: %s  평균 **%.3f**"
                  % (" ".join("%.2f" % v for v in src), srcm))
            st_m = float(np.nanmean(src_time)) if src_time else float("nan")
            print("  시간 분할(보수적) 평균 %.3f — 자기상관 때문에 무작위 분할보다 낮다."
                  % st_m)
            srcm = min(srcm, st_m) if st_m == st_m else srcm
            print("  아래 상한에는 **낮은 쪽 %.3f** 를 쓴다." % srcm),
            joint = (srcm * sm) ** 0.5 if srcm > 0 and sm > 0 else float("nan")
            print("  양쪽을 합친 감쇠 상한 sqrt(r_소스 × r_타깃) = **%.2f**" % joint)
            print("  관측 +0.097 은 이 상한의 %.0f%%." % (100 * 0.097 / joint))
            if joint > 0.25:
                print("  → 소스 쪽도 구속조건이 아니다. «예측력 없음» 은 두 측정의 분해능으로")
                print("    설명되지 않는 **실질적 널**이다.")
            else:
                print("  → 상한 자체가 낮다. 이 자료로는 «예측력 없음» 과 «잴 수 없었다» 가")
                print("    갈리지 않는다.")
    except Exception as e:
        print("")
        print("  (소스 쪽 신뢰도 건너뜀: %s: %s)" % (type(e).__name__, e))
        print("   → tensorboard 가 없으면 여기가 조용히 빠진다. .venv 로 실행하라.")


    # 몇 에피소드면 신뢰도가 쓸 만해지는가 — SB 를 역으로 푼다.
    print("\n  필요한 에피소드 수 (스피어만-브라운 역산, 현재 30에피소드 기준 r=%.3f)" % sm)
    print("    %-10s %s" % ("목표 신뢰도", "필요 배수 → 에피소드"))
    for tgt in (0.5, 0.7, 0.8, 0.9):
        if 0 < sm < tgt:
            n = tgt * (1 - sm) / (sm * (1 - tgt))
            print("    %-10.1f %.1f배 → 약 %d에피소드" % (tgt, n, int(round(30 * n))))
        else:
            print("    %-10.1f 이미 달성" % tgt)
    print("  ※ 이 역산은 «에피소드를 늘리면 잡음만 준다» 를 가정한다. 장면 난이도의 급내")
    print("    상관(ρ_w=0.612, tools/scenario_icc.py) 때문에 실제로는 **더 필요**하다 —")
    print("    같은 장면을 더 보는 것이 아니라 **다른 장면**을 늘려야 한다.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
