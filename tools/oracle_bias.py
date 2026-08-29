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
import sys

import numpy as np

N_EP = 30
N_MC = 20000


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
    return 0


if __name__ == "__main__":
    sys.exit(main())
