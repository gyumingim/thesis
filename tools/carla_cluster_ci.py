"""CARLA 반복 라운드는 독립 표본이 아니다 — 군집(앵커) 단위 신뢰구간으로 다시 계산한다.

시드 스윕에서 "여섯 라운드가 바이트 단위로 동일" 을 잡아내고도(§6.6 표본 고지) 그 진단을
표 2·3·4 에는 적용하지 않았다. 원자료를 열어 보면 evolve·evolve5 의 반복은 시드 스윕만큼
완전한 복제는 **아니지만** 독립도 아니다:

  * `turn_deg`·`min_R` 은 라운드 간 **완전히 동일**하다 — 매 라운드가 같은 20개 경로를 돈다.
  * `entry_kmh`·`max_lat`·`steps` 는 라운드마다 다르다 — 주행 자체에는 잡음이 있다.
  * `outcome` 은 조건에 따라 1~4종이다 — 대부분의 앵커가 매번 같은 결과를 낸다.

즉 라운드는 **앵커 모집단에서의 새 추출이 아니라 같은 앵커에 대한 반복 측정**이다.
n = 라운드 × 20 으로 이항 구간을 그리면 앵커 내 상관을 무시해 구간이 좁아진다.
이 도구는 앵커를 분석 단위로 삼아(각 앵커의 성공 비율을 하나의 관측으로) t 구간을 구하고,
설계효과 deff 와 유효 표본 크기를 함께 낸다.

실행: python tools/carla_cluster_ci.py bench_results/carla/evolve5
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

# t 분포 양측 97.5% 분위 (df 1..30, 이후 정규 근사) — scipy 없이 쓰기 위한 표
T975 = [12.706, 4.303, 3.182, 2.776, 2.571, 2.447, 2.365, 2.306, 2.262, 2.228,
        2.201, 2.179, 2.160, 2.145, 2.131, 2.120, 2.110, 2.101, 2.093, 2.086,
        2.080, 2.074, 2.069, 2.064, 2.060, 2.056, 2.052, 2.048, 2.045, 2.042]


def tcrit(df):
    return T975[df - 1] if 1 <= df <= 30 else 1.96


def wilson(k, n, z=1.96):
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return 100 * max(0.0, c - h), 100 * min(1.0, c + h)


def load(root):
    """조건 → 앵커(ep) → 라운드별 성공 여부."""
    cond = collections.defaultdict(lambda: collections.defaultdict(list))
    for f in sorted(glob.glob(os.path.join(root, "*.json"))):
        parts = os.path.basename(f)[:-5].split("_")
        rs = [t for t in parts if t.startswith("r") and t[1:].isdigit()]
        if not rs:
            continue
        key = "_".join(t for t in parts if t != rs[0])
        rows = json.load(io.open(f, encoding="utf-8"))
        if not rows or not isinstance(rows[0], dict):
            continue
        for r in rows:
            cond[key][r.get("ep")].append(r.get("outcome") == "성공")
    return cond


def cluster_ci(anchors):
    """앵커별 성공 비율을 단위로 한 t 구간과 설계효과."""
    means = [sum(v) / len(v) for v in anchors.values()]
    n_a = len(means)
    n_ep = sum(len(v) for v in anchors.values())
    p = sum(sum(v) for v in anchors.values()) / n_ep
    if n_a < 2:
        return p, float("nan"), float("nan"), float("nan"), n_a, n_ep
    se_c = statistics.stdev(means) / math.sqrt(n_a)
    h = tcrit(n_a - 1) * se_c
    se_naive = math.sqrt(p * (1 - p) / n_ep)
    deff = (se_c / se_naive) ** 2 if se_naive > 0 else float("nan")
    return p, 100 * max(0.0, p - h), 100 * min(1.0, p + h), deff, n_a, n_ep


def main():
    root = sys.argv[1] if len(sys.argv) > 1 else "bench_results/carla/evolve5"
    cond = load(root)
    if not cond:
        print("원자료 없음:", root)
        return 2
    print("경로: %s" % root)
    print("  %-28s %6s %5s %5s %-18s %-18s %6s %6s" %
          ("조건", "성공률", "ep", "앵커", "이항 Wilson CI", "앵커 군집 t CI",
           "deff", "유효n"))
    for k in sorted(cond):
        anchors = cond[k]
        if max(len(v) for v in anchors.values()) < 2:
            continue                      # 라운드가 하나면 군집 보정이 무의미하다
        p, lo, hi, deff, n_a, n_ep = cluster_ci(anchors)
        ok = round(p * n_ep)
        wl, wh = wilson(ok, n_ep)
        eff = n_ep / deff if deff and deff == deff else float("nan")
        print("  %-28s %5.1f%% %5d %5d [%5.1f, %5.1f] %s [%5.1f, %5.1f] %6.2f %6.1f" %
              (k, 100 * p, n_ep, n_a, wl, wh, " " * 3, lo, hi, deff, eff))
    print()
    print("  deff > 1 이면 이항 구간이 그만큼 좁다. 유효n = ep / deff.")
    print("  라운드가 같은 앵커의 반복 측정이므로 앵커 군집 t 구간이 정직한 쪽이다.")
    if len(sys.argv) <= 2 or sys.argv[2] != "--no-paired":
        paired_section()
    return 0


# ---------------------------------------------------------------------------
# 같은 20 앵커를 모든 조건이 공유하므로, 조건 간 비교는 **대응 표본**이다.
# 주변 비율의 구간이 겹치는지 보는 것보다 앵커별 차이를 검정하는 쪽이 정직하고 강력하다.
# ---------------------------------------------------------------------------

def rate(cond, k, e):
    v = cond[k][e]
    return sum(v) / len(v)


def sign_perm(d):
    """대응 차이의 정확 검정 — 0 이 아닌 쌍의 부호를 전수 뒤집는다."""
    nz = [x for x in d if abs(x) > 1e-12]
    base = sum(x for x in d if abs(x) <= 1e-12)
    obs = abs(statistics.mean(d))
    hit = sum(1 for s in itertools.product([1, -1], repeat=len(nz))
              if abs((base + sum(x * y for x, y in zip(nz, s))) / len(d)) >= obs - 1e-12)
    return statistics.mean(d), hit / 2 ** len(nz), len(nz)


GOV_ON, GOV_OFF = "v4_전체_npc3_g0.8_%s", "v4_전체_npc3_g0_%s"


def paired_section():
    A = load("bench_results/carla/evolve")
    B = load("bench_results/carla/evolve5")
    if not A or not B:
        return
    print()
    print("[대응 검정] 모든 조건이 같은 20 앵커를 돈다 — 조건 간 비교는 대응 표본이다")
    for tag, cond in (("표 2 구성 A", A), ("표 3 구성 B", B)):
        for mk in ("nomask", "mask"):
            on, off = GOV_ON % mk, GOV_OFF % mk
            eps = sorted(set(cond[on]) & set(cond[off]))
            d = [rate(cond, on, e) - rate(cond, off, e) for e in eps]
            m, p, nz = sign_perm(d)
            print("  %-10s 거버너 ON−OFF (%-6s) %+6.1f%%p  앵커 %d(불일치 %2d)  p=%.4f%s"
                  % (tag, mk, 100 * m, len(eps), nz, p, "  ← 유의" if p < 0.05 else ""))
        for gv in ("g0.8", "g0"):
            mk_on = "v4_전체_npc3_%s_mask" % gv
            mk_off = "v4_전체_npc3_%s_nomask" % gv
            eps = sorted(set(cond[mk_on]) & set(cond[mk_off]))
            d = [rate(cond, mk_on, e) - rate(cond, mk_off, e) for e in eps]
            m, p, nz = sign_perm(d)
            print("  %-10s 마스킹 ON−OFF (%-6s) %+6.1f%%p  앵커 %d(불일치 %2d)  p=%.4f%s"
                  % (tag, gv, 100 * m, len(eps), nz, p, "  ← 유의" if p < 0.05 else ""))
    print()
    print("[상호작용] 거버너 효과가 구성 A → 구성 B 에서 사라지는가")
    for mk in ("nomask", "mask"):
        on, off = GOV_ON % mk, GOV_OFF % mk
        eps = sorted(set(A[on]) & set(A[off]) & set(B[on]) & set(B[off]))
        dA = [rate(A, on, e) - rate(A, off, e) for e in eps]
        dB = [rate(B, on, e) - rate(B, off, e) for e in eps]
        m, p, nz = sign_perm([b - a for a, b in zip(dA, dB)])
        print("  %-6s 구성A %+5.1f%%p → 구성B %+5.1f%%p  차이 %+6.1f%%p  불일치 %2d  p=%.4f%s"
              % (mk, 100 * statistics.mean(dA), 100 * statistics.mean(dB), 100 * m, nz, p,
                 "  ← 유의" if p < 0.05 else ""))
    print("  → 지지집합이 깨진 조건(구성 B·마스킹 OFF)에서 거버너 효과가 0 으로 사라진다.")


if __name__ == "__main__":
    sys.exit(main())
