"""DPC 재산출 — 확정 정숙 조건에서 경량 신호가 전이 성능을 예측하는가.

§6.3 의 DPC 실측은 부호 오류판에서 얻었고, 정정판 재산출도 GPU 경합 20M 런에서만 했다.
§8 향후 연구 (4)가 남겨 둔 "정숙 조건 136M 체크포인트 재산출"이 이 스크립트다.
CSV 내보내기 없이 TensorBoard 이벤트 파일에서 직접 학습 곡선을 읽는다.

정의 (tools/dpc_metric.py 와 동일):
- L_c = 체크포인트 c 시점 ±150s 창의 경량 학습 episodic_return 평균 (경량 신호만 —
  전이 점수를 훔쳐보지 않는다)
- M_c = 같은 체크포인트의 MetaDrive 30ep 결정론 성공률
- τ = 시드 내 쌍만 집계하는 층화 Kendall τ-b (풀링하면 시드 간 수준 차가 상관으로 샌다)
- Δτ = 전반(5~30분) − 후반(35~60분)
- p = 시드 내 순환 이동 순열 1,000회 (자기상관 보존)

실행: python tools/dpc_recompute.py
"""
import glob
import json
import os
import re
import sys

import numpy as np
from scipy.stats import kendalltau

HALF = 150.0          # 체크포인트 시점 ±150s 창
N_PERM = 1000


def load_curve(run_dir):
    from tensorboard.backend.event_processing import event_accumulator
    ea = event_accumulator.EventAccumulator(run_dir, size_guidance={"scalars": 0})
    ea.Reload()
    if "charts/episodic_return" not in ea.Tags()["scalars"]:
        return None
    ev = ea.Scalars("charts/episodic_return")
    t0 = ev[0].wall_time
    return np.array([(e.wall_time - t0, e.value) for e in ev])


def pair_seed(run_dir, eval_json):
    curve = load_curve(run_dir)
    if curve is None:
        return None
    rows = sorted(json.load(open(eval_json)), key=lambda r: r["elapsed_s"])
    rows = [r for r in rows if r["ckpt"] != "final.pt"]
    L, M, T = [], [], []
    for r in rows:
        t = r["elapsed_s"]
        w = curve[(curve[:, 0] >= t - HALF) & (curve[:, 0] <= t + HALF)]
        if len(w) == 0:
            continue
        L.append(float(w[:, 1].mean()))
        M.append(100 * r["success_rate"])
        T.append(t)
    return np.array(L), np.array(M), np.array(T)


def stratified_tau(seeds):
    """시드 내 쌍만 세는 층화 Kendall τ-b — 시드별 τ 를 쌍 수로 가중 평균한다."""
    num, den = 0.0, 0.0
    for L, M in seeds:
        if len(L) < 3:
            continue
        t, _ = kendalltau(L, M)
        if np.isnan(t):
            continue
        w = len(L) * (len(L) - 1) / 2
        num += t * w
        den += w
    return num / den if den else float("nan")


def perm_p(seeds, observed):
    """시드 내 순환 이동으로 널 분포 — M 의 자기상관 구조를 보존한다."""
    rng = np.random.default_rng(0)
    null = []
    for _ in range(N_PERM):
        shifted = []
        for L, M in seeds:
            k = int(rng.integers(1, max(2, len(M))))
            shifted.append((L, np.roll(M, k)))
        null.append(stratified_tau(shifted))
    null = np.array([v for v in null if not np.isnan(v)])
    return float(np.mean(np.abs(null) >= abs(observed)))


def main():
    pairs = []
    for ev in sorted(glob.glob("bench_results/clean/eval_md__clean_s*.json")):
        s = re.search(r"_s(\d+)\.json$", ev).group(1)
        runs = glob.glob("runs/Intersection__clean_custom__%s__*" % s)
        if not runs:
            print("  런 디렉터리 없음: 시드", s)
            continue
        got = pair_seed(runs[0], ev)
        if got:
            pairs.append((s, ) + got)

    if not pairs:
        print("자료 없음")
        return 2

    print("확정 정숙 조건(136M) DPC 재산출 — 시드 %d개" % len(pairs))
    seeds_all, seeds_early, seeds_late = [], [], []
    for s, L, M, T in pairs:
        t, p = kendalltau(L, M)
        early = T <= 1800
        late = T > 1800
        seeds_all.append((L, M))
        if early.sum() >= 3:
            seeds_early.append((L[early], M[early]))
        if late.sum() >= 3:
            seeds_late.append((L[late], M[late]))
        print("  시드 %s: n=%d  τ=%+.2f (p=%.3f)  L범위 %.0f~%.0f  M범위 %.0f~%.0f"
              % (s, len(L), t, p, L.min(), L.max(), M.min(), M.max()))

    tau_all = stratified_tau(seeds_all)
    tau_e = stratified_tau(seeds_early)
    tau_l = stratified_tau(seeds_late)
    print()
    print("  층화 τ-b  전 구간 %+.3f (순열 p=%.3f)" % (tau_all, perm_p(seeds_all, tau_all)))
    print("           전반(≤30분) %+.3f | 후반(>30분) %+.3f | Δτ=%+.3f"
          % (tau_e, tau_l, tau_e - tau_l))
    print()
    print("  해석 기준: |τ| < 0.2 면 예측력 부재로 읽는다. Δτ 가 크고 전반 τ 가 유의하면")
    print("  '신뢰 창(trust horizon)'이 존재한다는 뜻이고, 둘 다 0 부근이면 경량 신호로는")
    print("  체크포인트를 고를 수 없다는 뜻이다(§6.3).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
