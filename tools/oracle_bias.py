"""오라클 체크포인트 이득이 신호인가 최댓값 편향인가 — 승자의 저주 몬테카를로.

§6.2 는 "시드별 최적 체크포인트를 사후에 고르면 64.7%로 완주 49.3% 보다 15.4%p 높다"를
보고했고, §7 은 그로부터 "완주보다 체크포인트 선택이 낫다"를 권고했다. 그런데 12개
체크포인트를 30에피소드로 평가하고 그중 최댓값을 고르면, **진짜 성능이 전 구간 완전히
일정해도** 평가 잡음만으로 상당한 이득이 나온다.

귀무가설을 그대로 시뮬레이션한다: 모든 체크포인트의 진짜 성공률 = 완주 성공률(상수),
각 평가 = Binomial(30, p). 시드마다 12개 중 최댓값을 고르고 시드 평균을 낸다.
관측 오라클 값이 이 널 분포 안에 들어가면 15.4%p 는 신호가 아니다.

실행: python tools/oracle_bias.py
"""
import glob
import json
import math
import sys

import numpy as np

N_EP = 30
N_MC = 20000
# 같은 30 시나리오(500000~500029)를 12개 체크포인트가 **모두** 본다. 따라서 체크포인트
# 점수는 독립이 아니라 시나리오 난이도를 공유해 양의 상관을 갖는다. 상관이 커질수록
# 최댓값 편향은 작아지므로, 독립 가정만으로 "이득 전부가 편향" 이라고 말할 수 없다.
# 잠재 프로빗 모형으로 급내 상관 ρ 를 넣어 편향이 얼마나 줄어드는지 함께 본다.
RHOS = (0.0, 0.1, 0.2, 0.3, 0.5, 0.7)


def main():
    fs = sorted(glob.glob("bench_results/clean/eval_md__clean_s*.json"))
    if not fs:
        print("원자료 없음")
        return 2
    finals, oracles, n_ck = [], [], None
    for f in fs:
        rows = json.load(open(f))
        finals.append(100 * [r for r in rows if r["ckpt"] == "final.pt"][0]["success_rate"])
        oracles.append(max(100 * r["success_rate"] for r in rows))
        n_ck = len(rows)
    n_seed = len(fs)
    p = np.mean(finals) / 100.0

    rng = np.random.default_rng(0)
    null = np.empty(N_MC)
    for i in range(N_MC):
        draws = rng.binomial(N_EP, p, size=(n_seed, n_ck)) / N_EP * 100
        null[i] = draws.max(axis=1).mean()
    lo, hi = np.percentile(null, [2.5, 97.5])
    obs = float(np.mean(oracles))

    print("귀무가설: 전 체크포인트의 진짜 성공률이 완주값 %.1f%% 로 일정, 평가는 Binomial(%d, p)"
          % (100 * p, N_EP))
    print("  시드 %d · 체크포인트 %d · 몬테카를로 %d회" % (n_seed, n_ck, N_MC))
    print("  널 분포에서의 오라클 기대값 %.1f%%  95%% 구간 [%.1f, %.1f]" % (null.mean(), lo, hi))
    print("  관측 오라클 %s → 평균 %.1f%%" % ([round(v, 1) for v in oracles], obs))
    print("  관측 이상이 나올 확률 p = %.3f" % float((null >= obs).mean()))
    print()
    gain = obs - float(np.mean(finals))
    null_gain = null.mean() - 100 * p
    print("  겉보기 이득 %.1f%%p 중 최댓값 편향으로 설명되는 몫 %.1f%%p (%.0f%%)"
          % (gain, null_gain, 100 * null_gain / gain if gain else 0))
    if lo <= obs <= hi:
        print("  → 관측이 널 구간 안이다. **이 이득은 신호가 아니라 선택 편향이다.**")
    else:
        print("  → 관측이 널 구간 밖이다. 편향을 넘는 몫이 있다.")

    # --- 시나리오 공유를 넣으면 편향은 얼마나 줄어드는가 -------------------------
    from math import erf, sqrt

    def phi_inv(q):                        # 이항 확률 → 잠재 임계값 (이분 탐색)
        lo_, hi_ = -8.0, 8.0
        for _ in range(80):
            mid = (lo_ + hi_) / 2
            if 0.5 * (1 + erf(mid / sqrt(2))) < q:
                lo_ = mid
            else:
                hi_ = mid
        return (lo_ + hi_) / 2

    thr = phi_inv(p)
    n_mc2 = max(2000, N_MC // 5)
    print()
    print("  같은 30 시나리오를 12 체크포인트가 공유한다 — 급내 상관 ρ 를 넣은 널")
    print("    %5s %12s %12s %s" % ("ρ", "널 오라클", "편향 몫", "관측 %.1f%% 설명" % obs))
    for rho in RHOS:
        a_, b_ = math.sqrt(rho), math.sqrt(1 - rho)
        acc = np.empty(n_mc2)
        for i in range(n_mc2):
            u = rng.standard_normal(N_EP)                       # 시나리오 난이도(전 조건 공유)
            e = rng.standard_normal((n_seed, n_ck, N_EP))
            hit = (a_ * u + b_ * e < thr).mean(axis=2) * 100
            acc[i] = hit.max(axis=1).mean()
        nb = acc.mean() - 100 * p
        print("    %5.2f %11.1f%% %11.1f%%p %s"
              % (rho, acc.mean(), nb,
                 "%.0f%%" % (100 * nb / gain) if gain else "-"))
    print("  ρ 가 커질수록 편향 몫이 줄어든다. 위 표는 **가정한 격자**다 — 아래에서 잰다.")

    # --- 실측 ρ 로 다시 (2026-09-16) -----------------------------------------
    # tools/scenario_icc.py 가 에피소드 단위 결과에서 사분상관을 쟀다. 구조가 하나가
    # 아니라 **둘**이었다: 같은 시드의 체크포인트끼리 ρ_w=0.612, 다른 시드끼리는
    # ρ_b=0.139. 즉 장면 난이도의 대부분은 **정책마다 다르다**(내재 난이도가 아니다).
    # 위 표의 한 모수 모형은 둘을 같다고 놓은 것이라 구조를 틀리게 본다.
    #   잠재 = sqrt(ρ_b)·u(장면)  +  sqrt(ρ_w−ρ_b)·v(시드,장면)  +  sqrt(1−ρ_w)·ε
    RHO_W, RHO_B = 0.612, 0.139            # scenario_icc.py 실측 (5시드 × 12ckpt × 30장면)
    print("")
    print("  **실측 구조**로 다시 — 시드 내 ρ_w=%.3f, 시드 간 ρ_b=%.3f (scenario_icc.py)"
          % (RHO_W, RHO_B))
    cb, cw, ce = math.sqrt(RHO_B), math.sqrt(RHO_W - RHO_B), math.sqrt(1 - RHO_W)
    acc = np.empty(n_mc2)
    for i in range(n_mc2):
        u = rng.standard_normal(N_EP)                       # 내재 장면 난이도
        v = rng.standard_normal((n_seed, N_EP))             # 정책별 장면 난이도
        e = rng.standard_normal((n_seed, n_ck, N_EP))       # 평가 잡음
        lat = cb * u + cw * v[:, None, :] + ce * e
        acc[i] = (lat < thr).mean(axis=2).max(axis=1).mean() * 100
    nlo, nhi = np.percentile(acc, [2.5, 97.5])
    nb = acc.mean() - 100 * p
    print("    널 오라클 %.1f%%  95%% 구간 [%.1f, %.1f]  편향 몫 %.1f%%p (%.0f%%)"
          % (acc.mean(), nlo, nhi, nb, 100 * nb / gain if gain else 0))
    print("    관측 오라클 %.1f%% → %s"
          % (obs, "널 구간 **안**" if nlo <= obs <= nhi else "널 구간 밖"))
    print("  가정이 아니라 측정으로 같은 판정에 도달한다. 한 모수 격자에서 ρ=0.6 근방을",)
    print("  읽던 것과 결론은 같지만, 근거가 «어느 ρ 에서도» 에서 «잰 ρ 에서» 로 바뀐다.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
