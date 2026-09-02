"""표 5 (§6.6 방향별 분해) 감사 — 미공개 필터, 파생 열의 자기모순, 분모의 착시.

구판 표 5 는 세 가지를 잘못 말했다. 이 도구는 셋을 각각 원자료에서 재현한다.

1. **미공개 필터.** 「경로 최소 반경」은 곡률 미검출 시 999 센티널이 들어가고(직진의 절반),
   「진입 속도」는 교차로 진입 지점을 밟기 전에 끝났거나 스폰 지점이 이미 교차로 안이면
   0 이 된다(우회전의 69%). 두 열은 서로 다른 부분표본이며, 그 결측이 결과와 상관한다.
2. **파생 열의 자기모순.** 「필요 횡가속」에서 좌회전(0.83 g)이 우회전(0.80 g)보다 높은데
   성공률도 높다. 따라서 "우회전이 0.8 g 거버너 한계에 붙어서 어렵다" 는 설명은 성립하지
   않는다 — 같은 논리라면 좌회전이 더 어려워야 한다.
3. **분모의 착시.** "좌회전은 아홉 정책 모두 균일" 은 정책당 좌회전이 **3건**뿐이라
   해상도가 33%p 인 데서 온다. 정책 간 분산을 이항 잡음 기대치와 대면 우회전만
   잡음을 넘는다(2.1배). 좌회전은 1.1배로 사실상 전부 잡음이다.

대신 무엇이 남는가: 정책을 단위로 좌·우를 **대응**시켜 부호 순열로 검정하면
좌−우 차이 +23.6%p, 9정책 중 역전 0, 양측 p=0.031. 우회전 취약성 자체는 유지된다.

실행: python tools/table5_filters.py [bench_results/carla/seed_sweep]
"""
import collections
import glob
import io
import itertools
import json
import math
import os
import statistics
import sys

G = 9.80665
SENTINEL = 999.0
ORDER = ["직진", "우회전", "좌회전", "유턴"]


def maneuver(r):
    """실행된 총 회전각으로 기동을 정한다(carla_ab_analysis 와 같은 규약).

    본 자료는 부호 보존 재수집분이므로 CARLA 좌수 좌표계대로 양수 = 우회전이다.
    """
    a = abs(r["turn_deg"])
    if a >= 150:
        return "유턴"
    if a < 30:
        return "직진"
    return "우회전" if r["turn_deg"] > 0 else "좌회전"


def wilson(k, n, z=1.96):
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return 100 * max(0.0, c - h), 100 * min(1.0, c + h)


def load(root):
    """라운드 중복(결정론 반복)을 제거해 정책당 20 에피소드만 남긴다."""
    pol = {}
    for f in sorted(glob.glob(os.path.join(root, "*.json"))):
        parts = os.path.basename(f)[:-5].split("_")
        key = "_".join(t for t in parts if not (t.startswith("r") and t[1:].isdigit()))
        if key not in pol:
            pol[key] = json.load(io.open(f, encoding="utf-8"))
    return pol


def sign_perm(diffs):
    """대응 표본의 정확 검정 — 각 쌍의 부호를 뒤집는 2^n 가지를 전수 조사한다."""
    obs = abs(statistics.mean(diffs))
    hit = sum(abs(statistics.mean(a * b for a, b in zip(diffs, s))) >= obs - 1e-12
              for s in itertools.product([1, -1], repeat=len(diffs)))
    return statistics.mean(diffs), hit / 2 ** len(diffs), 2 ** len(diffs)


def main():
    root = sys.argv[1] if len(sys.argv) > 1 else "bench_results/carla/seed_sweep"
    pol = load(root)
    if not pol:
        print("원자료 없음:", root)
        return 2
    rows = [r for rs in pol.values() for r in rs]
    by = collections.defaultdict(list)
    for r in rows:
        by[maneuver(r)].append(r)
    print("정책 %d종 × 20 에피소드 = %d건 (라운드 중복 제거 후)\n" % (len(pol), len(rows)))

    print("[1] 기동별 미공개 필터")
    for m in ORDER:
        rs = by[m]
        n = len(rs)
        sen = sum(r["min_R"] >= SENTINEL for r in rs)
        z = [r for r in rs if r["entry_kmh"] == 0]
        nz = [r for r in rs if r["entry_kmh"] > 0]
        zr = 100 * sum(r["outcome"] == "성공" for r in z) / len(z) if z else float("nan")
        nzr = 100 * sum(r["outcome"] == "성공" for r in nz) / len(nz) if nz else float("nan")
        print("  %-4s n=%-3d  min_R 센티널 %2d/%-2d(%4.1f%%)  entry=0 %2d/%-2d(%4.1f%%)"
              "  성공률 entry=0 %5.1f%% vs entry>0 %5.1f%%"
              % (m, n, sen, n, 100 * sen / n, len(z), n, 100 * len(z) / n, zr, nzr))
    print("  → 두 열의 중앙값은 서로 다른 부분표본에서 오며, 결측이 결과와 상관한다.\n")

    print("[2] 파생 열 「필요 횡가속」 — 좌회전이 더 높은데 더 잘 간다")
    print("  %-4s %8s %10s %10s %10s %8s" %
          ("기동", "성공률", "중앙 R(m)", "중앙 v(km/h)", "v²/gR", "에피소드별"))
    for m in ORDER:
        rs = by[m]
        ok = sum(r["outcome"] == "성공" for r in rs)
        R = [r["min_R"] for r in rs if r["min_R"] < SENTINEL]
        V = [r["entry_kmh"] for r in rs if r["entry_kmh"] > 0]
        pair = [(r["entry_kmh"] / 3.6) ** 2 / (G * r["min_R"])
                for r in rs if r["min_R"] < SENTINEL and r["entry_kmh"] > 0]
        mr, mv = statistics.median(R), statistics.median(V)
        print("  %-4s %7.1f%% %10.1f %10.1f %9.2fg %7.2fg (n=%d)"
              % (m, 100 * ok / len(rs), mr, mv, (mv / 3.6) ** 2 / (G * mr),
                 statistics.median(pair), len(pair)))
    print("  → 좌회전 0.83 g / 77.8% 와 우회전 0.80 g / 54.2% 는 «거버너 한계»로 설명되지 않는다.\n")

    print("[3] 정책 간 분산 — 잡음을 넘는 것은 우회전뿐")
    print("  %-4s %6s %8s %10s %10s %6s" %
          ("기동", "정책당", "평균", "관측 SD", "이항 기대 SD", "초과배"))
    rates = {}
    for m in ORDER:
        v = []
        for k in sorted(pol):
            rs = [r for r in pol[k] if maneuver(r) == m]
            if rs:
                v.append(100 * sum(r["outcome"] == "성공" for r in rs) / len(rs))
        k_ep = len(by[m]) // len(pol)
        p = statistics.mean(v) / 100
        exp = 100 * math.sqrt(p * (1 - p) / k_ep) if k_ep else float("nan")
        obs = statistics.pstdev(v)
        rates[m] = v
        print("  %-4s %6d %7.1f%% %9.1f%%p %9.1f%%p %5.2f배"
              % (m, k_ep, 100 * p, obs, exp, obs / exp if exp else float("nan")))
    print("  → 좌회전의 «균일함»은 정책당 3건이라는 분모의 산물이다(해상도 33%p).\n")

    print("[4] 그래도 남는 것 — 정책 대응 좌·우 비교")
    diffs = [rates["좌회전"][i] - rates["우회전"][i] for i in range(len(pol))]
    for i, k in enumerate(sorted(pol)):
        print("  %-14s 우 %5.1f%%  좌 %5.1f%%  차이 %+6.1f%%p"
              % (k, rates["우회전"][i], rates["좌회전"][i], diffs[i]))
    d, p, tot = sign_perm(diffs)
    print("  평균 차이 %+.1f%%p | 역전 %d/%d | 부호 순열 %d가지, 양측 p=%.4f%s"
          % (d, sum(x < 0 for x in diffs), len(diffs), tot, p, "  ← 유의" if p < 0.05 else ""))
    for m in ("우회전", "좌회전"):
        rs = by[m]
        ok = sum(r["outcome"] == "성공" for r in rs)
        print("  참고 %s 전수 %d/%d = %.1f%%  Wilson [%.1f, %.1f] "
              "(정책 %d × 앵커 %d — 군집 무시 시 과신)"
              % (m, ok, len(rs), 100 * ok / len(rs), *wilson(ok, len(rs)),
                 len(pol), len(rs) // len(pol)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
