"""DPC/Δτ — 경량 신호의 전이 예측력과 그 시간 구조 (§2.4 정식화의 실측, 2026-08-27).

지표 (로드맵 사이클2 정의):
- τ_full: 시드 내 (L_c, M_c) 12쌍의 Kendall τ-b, 시드별 → 층화 결합(시드 내 쌍만 집계).
- Δτ: 전반부(5-30분)/후반부(35-60분)의 층화 τ 차이. (원설계 '포화 전/후'는 경량 시뮬이
  첫 ckpt 이전에 포화해 이 데이터에서 퇴화 — 실측 t_sat=5분 전 시드.)
- p값: 시드 내 순환 이동(circular shift) 널 분포 (자기상관 보존, 1000회).
L = 경량 학습 episodic_return 의 ckpt 시점 ±150s 평균 (경량 신호만 — 전이 훔쳐보기 없음).
M = MetaDrive 30ep 성공률 (eval_md__final_custom_s*.json).
사용: python tools/dpc_metric.py <tb_csv_dir> <eval_json_dir>
"""
import csv
import glob
import json
import os
import sys

import numpy as np
from scipy.stats import kendalltau


def load_seed(tb_csv, eval_json):
    rows = []
    with open(tb_csv) as f:
        r = csv.reader(f); next(r)
        rows = [(float(a), float(c)) for a, b, c in r]
    t0 = rows[0][0]
    ev = sorted(json.load(open(eval_json)), key=lambda x: x["elapsed_s"])
    ev = [e for e in ev if e["ckpt"] != "final.pt"]
    L, M, T = [], [], []
    for e in ev:
        tc = e["elapsed_s"]
        vals = [v for w, v in rows if abs((w - t0) - tc) <= 150]
        if not vals:
            continue
        L.append(float(np.mean(vals))); M.append(e["success_rate"]); T.append(tc)
    return np.array(T), np.array(L), np.array(M)


def strat_tau(pairs):
    """시드 내 쌍만 세는 층화 Kendall τ-b (concordant-discordant 합산)."""
    num = den1 = den2 = 0.0
    for L, M in pairs:
        n = len(L)
        for i in range(n):
            for j in range(i + 1, n):
                a, b = np.sign(L[i] - L[j]), np.sign(M[i] - M[j])
                if a != 0 and b != 0:
                    num += a * b
                if a != 0: den1 += 1
                if b != 0: den2 += 1
    return num / np.sqrt(den1 * den2) if den1 and den2 else float("nan")


def main(tb_dir, ev_dir):
    seeds = []
    for s in (1, 2, 3, 4, 5):
        tb = os.path.join(tb_dir, f"tb_{s}.csv")
        ej = glob.glob(os.path.join(ev_dir, f"eval_md__final_custom_s{s}.json"))
        if os.path.exists(tb) and ej:
            seeds.append((s,) + load_seed(tb, ej[0]))
    print(f"시드 {len(seeds)}개")
    pre, post, full = [], [], []
    for s, T, L, M in seeds:
        tau, _ = kendalltau(L, M)
        m_pre, m_post = T <= 1800, T > 1800
        full.append((L, M)); pre.append((L[m_pre], M[m_pre])); post.append((L[m_post], M[m_post]))
        print(f"s{s}: τ_full={tau:+.2f}  후반 L추세 {'상승' if L[m_post][-1] > L[m_post][0] else '하강'}  "
              f"M 후반 {M[m_post][0]:.0%}→{M[m_post][-1]:.0%}")
    tf, tp, to = strat_tau(full), strat_tau(pre), strat_tau(post)
    print(f"\n층화 τ: 전체 {tf:+.3f} | 포화 전 {tp:+.3f} | 포화 후 {to:+.3f} | Δτ(전-후) {tp - to:+.3f}")
    # 순환 이동 순열 p (포화 후 τ가 이만큼 음일 확률)
    rng = np.random.default_rng(0)
    def perm_p(pairs, obs, side):
        null = []
        for _ in range(1000):
            perm = []
            for L, M in pairs:
                k = rng.integers(1, len(L)) if len(L) > 1 else 0
                perm.append((np.roll(L, k), M))
            null.append(strat_tau(perm))
        null = np.array(null)
        return float(np.mean(null <= obs) if side == "le" else np.mean(null >= obs))
    print(f"순열 p: 전반 τ ≥ 실측 {perm_p(pre, tp, 'ge'):.3f} | 후반 τ ≤ 실측 {perm_p(post, to, 'le'):.3f}")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
