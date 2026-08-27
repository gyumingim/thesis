"""DPC 방어 분석 D1+D3 (docs/DPC_STAT_DEFENSE.md 절차, 2026-08-27).

D1: 전반/후반 창별 L·M 분산, u-ratio, 시드별 후반 τ-b — "후반 L 분산 비축소" 실증.
D3: 코풀라 검정력 — 진짜 τ=+0.57 이 후반에도 존속했다면 관측 τ-b 분포가 어땠을지
   (가우시안 코풀라, 주변분포는 관측 그대로: L=관측 궤적, M=30시행 이항) 10,000회.
사용: python tools/dpc_defense.py <tb_dir> <eval_dir>
"""
import sys

import numpy as np

sys.path.insert(0, "tools")
from dpc_metric import load_seed, strat_tau  # noqa: E402


def main(tb_dir, ev_dir):
    import glob, os
    seeds = []
    for s in (1, 2, 3, 4, 5):
        tb = os.path.join(tb_dir, f"tb_{s}.csv")
        ej = glob.glob(os.path.join(ev_dir, f"eval_md__final_custom_s{s}.json"))
        if os.path.exists(tb) and ej:
            seeds.append(load_seed(tb, ej[0]))
    # D1
    print("=== D1: 창별 분산 · u-ratio · 시드별 후반 τ-b ===")
    from scipy.stats import kendalltau
    uLs, uMs = [], []
    for i, (T, L, M) in enumerate(seeds, 1):
        e, l = T <= 1800, T > 1800
        uL = L[l].std() / L.std() if L.std() else float("nan")
        uM = M[l].std() / M.std() if M.std() else float("nan")
        uLs.append(uL); uMs.append(uM)
        tl, _ = kendalltau(L[l], M[l])
        print(f"s{i}: SD_L 전반 {L[e].std():.1f} 후반 {L[l].std():.1f} (u_L {uL:.2f}) | "
              f"SD_M 전반 {M[e].std():.3f} 후반 {M[l].std():.3f} (u_M {uM:.2f}) | 후반 τ-b {tl:+.2f}")
    print(f"u_L 평균 {np.mean(uLs):.2f} (1 근방 = L측 range restriction 부재), u_M 평균 {np.mean(uMs):.2f}")
    # D3
    print("\n=== D3: 코풀라 검정력 (H1: 후반에도 τ=+0.57 존속) ===")
    rho = np.sin(np.pi * 0.569 / 2)
    rng = np.random.default_rng(0)
    obs_post = [(L[T > 1800], M[T > 1800]) for T, L, M in seeds]
    obs_tau = strat_tau(obs_post)
    sims = []
    for _ in range(10000):
        sim_pairs = []
        for L, M in obs_post:
            n = len(L)
            z = rng.multivariate_normal([0, 0], [[1, rho], [rho, 1]], n)
            u1, u2 = (z[:, 0]).argsort().argsort(), None
            Ls = np.sort(L)[u1]                      # L 주변분포 = 관측값
            k = np.round(np.sort(M) * 30).astype(int)  # M 관측 분포 -> 이항 재표집
            from scipy.stats import norm
            p2 = norm.cdf(z[:, 1])
            Ms = np.array([rng.binomial(30, max(q, 1e-9)) / 30 for q in np.quantile(np.repeat(k / 30, 1), p2)])
            sim_pairs.append((Ls, Ms))
        sims.append(strat_tau(sim_pairs))
    sims = np.array(sims)
    power_p = float(np.mean(sims <= obs_tau))
    print(f"관측 후반 τ-b {obs_tau:+.3f} | H1 시뮬 τ-b 5% 분위 {np.percentile(sims, 5):+.3f}, "
          f"중앙값 {np.median(sims):+.3f}")
    print(f"P(τ̂ ≤ 관측 | 진짜 τ=0.57) = {power_p:.4f}  → {'양립 불가(진짜 소멸)' if power_p < 0.05 else '검정력 부족(정직 보고)'}")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
