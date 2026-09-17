"""블록 간 난이도 차이는 **어디서 오는가** — §7 표 6 이 남긴 두 번째 한계.

표 6 은 블록마다 격차가 −12.7 ~ −22.0%p 로 움직인다는 것을 보였지만, 「어떤 시나리오가
어려운가」는 미규명으로 남겼다. 블록별 JSON 에 에피소드별 결과(`per_episode`)가 이미
들어 있으므로 추가 평가 없이 답할 수 있다.

묻는 것:
  (1) 시나리오 난이도의 **분포** — 고르게 어려운가, 소수의 불가능한 장면이 있는가
  (2) 두 팔이 **같은 장면**을 어려워하는가 — 난이도 순위의 상관.
      상관이 높으면 격차는 **균일한 이동**이고, 낮으면 팔마다 다른 것에서 진다.
  (3) 팔별 **실패 양상**(충돌 대 이탈). §5.2 에서 지지집합 위반의 주된 피해가 도로
      이탈이었으므로, 경량 팔이 이탈로 더 많이 진다면 두 결과가 연결된다.
  (4) 블록 격차가 소수 장면에 의해 좌우되는가 — 블록별 «경량 전멸» 장면 수와 함께 본다.

단위 주의: 시나리오는 팔 안에서 정책 5개가 공유하므로 «장면당 성공 수»(0~5)가 자연스러운
집계 단위다. 장면 간에는 공유되는 것이 없어 장면을 독립으로 보는 것은 무리가 없다.

실행: .venv/Scripts/python.exe tools/scenario_difficulty.py
"""
import glob
import io
import json
import os
import random
import statistics as st
import sys

ROOT = "bench_results/scenario_blocks"
# 시드 목록 — 2026-09-17 에 팔당 5 → 10 으로 보강했다(bench/run_seeds6to10.sh).
# ARM_SEEDS=5 로 옛 표본을 그대로 재현할 수 있게 남겨 둔다 — 논문이 n=5 행과 n=10 행을
# 나란히 싣기 때문이고, 「바뀐 것은 표본뿐」임을 언제든 다시 보일 수 있어야 한다.
# ★ 기본값은 **5(8월 배치)** 다. 2026-09-17 에 팔당 10시드를 채웠지만 9월 배치는
#   처리량이 다르고(경량 +15.3%, 네이티브 +7.3%) 그 차이가 팔마다 다르므로, 묶으면
#   조건 효과가 섞인다(§7 배치 효과, tools/batch_effect.py). 조건이 통제된 표본은
#   **8월 배치**이고 논문의 모든 수치가 그것이다. ARM_SEEDS=10 은 묶은 값을 보고
#   싶을 때만 쓰며, 그 값은 헤드라인으로 쓸 수 없다.
_NS = int(os.environ.get("ARM_SEEDS", "5"))
LIGHT = ["clean_s%d" % s for s in range(1, 1 + _NS)]
NATIVE = ["nd_s%d" % s for s in range(2, 2 + _NS)]
FLAG = {1: "충돌", 2: "이탈", 3: "성공", 4: "타임아웃"}


def load():
    """(팔, 시나리오) → 플래그 리스트."""
    out = {}
    for tag in LIGHT + NATIVE:
        arm = "경량" if tag in LIGHT else "네이티브"
        for f in glob.glob(os.path.join(ROOT, "eval_md__%s__b*.json" % tag)):
            rows = json.load(io.open(f, encoding="utf-8"))
            r = [x for x in rows if x["ckpt"] == "final.pt"]
            if not r:
                continue
            for e in r[0]["per_episode"]:
                out.setdefault((arm, int(e["scenario"])), []).append(int(e["flag"]))
    return out


def kendall_tau_b(x, y):
    n = len(x)
    c = d = tx = ty = 0
    for i in range(n):
        for j in range(i + 1, n):
            a, b = x[i] - x[j], y[i] - y[j]
            if a == 0 and b == 0:
                tx += 1
                ty += 1
            elif a == 0:
                tx += 1
            elif b == 0:
                ty += 1
            elif (a > 0) == (b > 0):
                c += 1
            else:
                d += 1
    # τ-b 의 분모는 «전체 쌍 − x 동률 쌍» 과 «전체 쌍 − y 동률 쌍» 의 기하평균이다.
    # 첫 판은 c+d+tx 를 썼는데 그것은 y 동률만 빠진 값이라 틀린다 — scipy 와 대조하는
    # assert 가 바로 잡아냈다. 자체 구현을 남겨 두는 이유가 이것이다.
    tot = n * (n - 1) / 2
    a1, a2 = tot - tx, tot - ty
    return (c - d) / ((a1 * a2) ** 0.5) if a1 > 0 and a2 > 0 else float("nan")


def perm_p(x, y, tau, iters=2000, seed=0):
    rng = random.Random(seed)
    z = list(y)
    hit = 0
    for _ in range(iters):
        rng.shuffle(z)
        if abs(kendall_tau_b(x, z)) >= abs(tau) - 1e-12:
            hit += 1
    return (hit + 1) / (iters + 1)


def main():
    data = load()
    if not data:
        print("원자료 없음 — bench/run_scenario_blocks.sh 를 먼저 돌려라.")
        return 2
    scen = sorted({s for (_, s) in data})
    blocks = sorted({s - s % 10000 for s in scen})
    print("장면 %d개 (블록 %d개), 팔당 정책 5종" % (len(scen), len(blocks)))

    succ = {arm: {s: sum(f == 3 for f in data.get((arm, s), [])) for s in scen}
            for arm in ("경량", "네이티브")}
    npol = {arm: {s: len(data.get((arm, s), [])) for s in scen} for arm in ("경량", "네이티브")}
    bad = [s for s in scen if npol["경량"][s] != 5 or npol["네이티브"][s] != 5]
    if bad:
        print("  ★ 정책 수가 5가 아닌 장면 %d개 — 결측이 있다. 결과를 믿지 마라." % len(bad))

    # (1) 난이도 분포
    print("\n(1) 장면 난이도 분포 — 5개 정책 중 몇 개가 성공했는가")
    print("  %-8s %s" % ("성공 정책수", "".join("%7d" % k for k in range(6))))
    for arm in ("경량", "네이티브"):
        h = [sum(1 for s in scen if succ[arm][s] == k) for k in range(6)]
        print("  %-8s %s   (전멸 %d장면 = %.0f%%)"
              % (arm, "".join("%7d" % v for v in h), h[0], 100.0 * h[0] / len(scen)))
    print("  양 끝(0 또는 5)에 몰리면 장면이 정책을 **가른다**기보다 장면 자체가")
    print("  쉽거나 불가능하다는 뜻이다 — 그만큼 평가의 분해능이 낮다.")

    # (2) 두 팔이 같은 장면을 어려워하는가
    x = [succ["경량"][s] for s in scen]
    y = [succ["네이티브"][s] for s in scen]
    from scipy import stats as _sp
    tau, p = _sp.kendalltau(x, y, variant="b")      # 동률이 많아(값이 0~5) τ-b 를 쓴다
    assert abs(tau - kendall_tau_b(x, y)) < 1e-9, "자체 구현과 scipy 가 어긋난다"
    print("\n(2) 두 팔의 장면 난이도 상관  Kendall τ-b = %+.3f (점근 p=%.2g, n=%d장면)"
          % (tau, p, len(scen)))
    print("  (동률이 많아 τ-b. p 는 scipy 의 점근 근사이고 장면 독립을 가정한다.)")
    both = sum(1 for s in scen if succ["경량"][s] == 0 and succ["네이티브"][s] == 0)
    only_l = sum(1 for s in scen if succ["경량"][s] == 0 and succ["네이티브"][s] > 0)
    only_n = sum(1 for s in scen if succ["네이티브"][s] == 0 and succ["경량"][s] > 0)
    print("  양 팔 전멸 %d장면 | 경량만 전멸 %d | 네이티브만 전멸 %d"
          % (both, only_l, only_n))
    print("  상관이 높으면 격차는 **균일한 이동**이고, 낮으면 팔마다 다른 데서 진다.")

    # (3) 실패 양상
    print("\n(3) 팔별 실패 양상 (전체 에피소드 풀)")
    print("  %-10s %8s %8s %8s %8s" % ("팔", "성공", "충돌", "이탈", "타임아웃"))
    comp = {}
    for arm in ("경량", "네이티브"):
        fl = [f for (a, _), v in data.items() if a == arm for f in v]
        comp[arm] = [100.0 * sum(f == k for f in fl) / len(fl) for k in (3, 1, 2, 4)]
        print("  %-10s %7.1f%% %7.1f%% %7.1f%% %7.1f%%  (n=%d)"
              % (arm, *comp[arm], len(fl)))
    dO = comp["경량"][2] - comp["네이티브"][2]
    dC = comp["경량"][1] - comp["네이티브"][1]
    print("  경량−네이티브: 충돌 %+.1f%%p, 이탈 %+.1f%%p" % (dC, dO))
    print("  §5.2 에서 지지집합 위반의 주된 피해는 **이탈**이었다. 경량 팔의 초과 실패가")
    print("  이탈 쪽에 쏠리면 두 결과가 같은 기제를 가리킨다.")

    # (4) 블록 격차와 전멸 장면 수
    print("\n(4) 블록별 격차와 «전멸» 장면 수")
    print("  %-10s %9s %9s %9s %9s" % ("블록", "경량", "네이티브", "격차", "경량전멸"))
    gaps = []
    for b in blocks:
        ss = [s for s in scen if s - s % 10000 == b]
        lm = 100.0 * sum(succ["경량"][s] for s in ss) / (5 * len(ss))
        nm = 100.0 * sum(succ["네이티브"][s] for s in ss) / (5 * len(ss))
        z = sum(1 for s in ss if succ["경량"][s] == 0)
        gaps.append(lm - nm)
        print("  b%-9d %8.1f%% %8.1f%% %+8.1f %8d/%d" % (b, lm, nm, lm - nm, z, len(ss)))
    print("  격차의 블록 간 σ %.1f%%p (블록 %d개)" % (st.stdev(gaps), len(gaps)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
