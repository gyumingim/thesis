"""§6.2 헤드라인 격차의 검정력·최소검출효과·동등성 — "유의하지 않다" 가 무엇을 뜻하는지.

논문은 경량 49.3%±16.1 대 네이티브 62.0%±14.5(각 n=5)에서 p=0.227 을 얻고 "유의하지
않다" 고 적었다. 그 서술은 옳지만, 초고는 거기에 **"표본을 늘려도 쉽게 유의해지지
않는다"** 를 덧붙였다. 그것은 관측된 p 값에서 미래의 검정력을 역추론한 것으로,
사후 검정력의 오류다 — 시드를 3→5 로 늘렸을 때 p 가 0.385→0.227 로 움직인 것은
**참 효과가 있을 때 기대되는 거동 그 자체**다.

이 도구가 대신 답한다:
  (a) 관측 효과크기에서 n=5 의 검정력은 얼마인가 — 즉 이 실험이 애초에 무엇을 볼 수
      있었는가.
  (b) n=5 에서 80% 검정력으로 검출 가능한 최소 격차(MDE)는 얼마인가.
  (c) 관측 격차를 80% 로 검출하려면 팔당 몇 시드가 필요한가.
  (d) 동등성(TOST): 이 자료로 "차이가 ±Δ 안" 이라고 말할 수 있는 가장 좁은 Δ 는?

실행: python tools/power_mde.py
"""
import sys

import numpy as np
from scipy import stats

# §6.2 확정 정숙 조건, 동일 데스크톱
LIGHT = (49.3, 16.1, 5)      # 평균, 표본 SD, 시드 수
NATIVE = (62.0, 14.5, 5)
ALPHA = 0.05
N_MC = 200000


def power_welch(d, n, alpha=ALPHA, n_mc=N_MC, seed=0):
    """효과크기 d(=Δ/pooled SD), 팔당 n 에서 Welch 양측 검정의 검정력 — 몬테카를로."""
    rng = np.random.default_rng(seed)
    a = rng.standard_normal((n_mc, n))
    b = rng.standard_normal((n_mc, n)) + d
    va, vb = a.var(axis=1, ddof=1), b.var(axis=1, ddof=1)
    se = np.sqrt(va / n + vb / n)
    t = (b.mean(axis=1) - a.mean(axis=1)) / se
    df = (va / n + vb / n) ** 2 / ((va / n) ** 2 / (n - 1) + (vb / n) ** 2 / (n - 1))
    return float((np.abs(t) > stats.t.ppf(1 - alpha / 2, df)).mean())


def main():
    (m1, s1, n1), (m2, s2, n2) = LIGHT, NATIVE
    diff = m2 - m1
    sp = np.sqrt((s1 ** 2 + s2 ** 2) / 2)
    d = diff / sp
    se = np.sqrt(s1 ** 2 / n1 + s2 ** 2 / n2)
    df = se ** 4 / ((s1 ** 2 / n1) ** 2 / (n1 - 1) + (s2 ** 2 / n2) ** 2 / (n2 - 1))
    t = diff / se
    p = 2 * (1 - stats.t.cdf(abs(t), df))
    tc = stats.t.ppf(1 - ALPHA / 2, df)
    print("관측: 경량 %.1f±%.1f (n=%d) vs 네이티브 %.1f±%.1f (n=%d)" % (m1, s1, n1, m2, s2, n2))
    print("  격차 %+.1f%%p  Welch t=%.2f df=%.1f p=%.3f  95%% CI [%.1f, %.1f]"
          % (diff, t, df, p, diff - tc * se, diff + tc * se))
    print("  pooled SD %.1f%%p → Cohen d = %.3f\n" % (sp, d))

    print("(a) 이 실험의 검정력 — 관측 효과크기가 참값이라면")
    for n in (5, 8, 10, 15, 20, 30):
        print("      팔당 n=%-3d 검정력 %.3f%s" % (n, power_welch(d, n),
                                              "   ← 실제 수행" if n == 5 else ""))
    print("      n=5 에서 검정력이 0.2 대라는 것은, 참 효과가 이 크기로 실재해도")
    print("      다섯 번 중 네 번은 «유의하지 않음» 이 나온다는 뜻이다.\n")

    print("(b) n=5 에서 80% 검정력의 최소검출효과(MDE)")
    lo, hi = 0.0, 5.0
    for _ in range(40):
        mid = (lo + hi) / 2
        if power_welch(mid, 5, n_mc=40000, seed=1) < 0.80:
            lo = mid
        else:
            hi = mid
    print("      d=%.2f → 격차 %.1f%%p — 관측 격차 %.1f%%p 의 %.1f배\n"
          % (hi, hi * sp, diff, hi * sp / diff))

    print("(c) 관측 격차를 80% 로 검출하려면")
    for n in range(5, 61):
        if power_welch(d, n, n_mc=40000, seed=2) >= 0.80:
            print("      팔당 %d 시드 (총 %d 런 = %d 시간의 벽시계 예산)\n" % (n, 2 * n, 2 * n))
            break

    print("(d) 동등성(TOST) — 이 자료가 배제할 수 있는 격차의 크기")
    print("      양측 90%% 구간이 곧 TOST 경계다: [%.1f, %.1f]%%p"
          % (diff - stats.t.ppf(0.95, df) * se, diff + stats.t.ppf(0.95, df) * se))
    print("      즉 «두 팔이 ±Δ 안에서 같다» 를 주장하려면 Δ ≥ %.1f%%p 여야 하는데,"
          % max(abs(diff - stats.t.ppf(0.95, df) * se), abs(diff + stats.t.ppf(0.95, df) * se)))
    print("      그 폭은 격차 자체보다 크므로 **동등성도 주장할 수 없다**.")
    print("      비유의는 «같다» 가 아니라 «이 표본으로는 구별하지 못한다» 이다.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
