"""실패 모드의 시간 추세 — 학습이 진행되며 실패가 충돌에서 이탈로 옮겨가는가.

성공률만 보면 잡히지 않는 것을 본다. 성공률은 노이즈에 묻혀 추세가 안 보여도,
**실패의 구성**은 방향을 가질 수 있다. 체크포인트별 이탈률·충돌률과 학습 시간의
Kendall τ 를 시드마다 따로 구하고(풀링하면 시드 간 수준 차가 상관으로 새어든다),
시드별 p 값을 Fisher 로 결합한다.

실행: python tools/failure_mode_trend.py [glob ...]
"""
import glob
import json
import sys

import numpy as np
from scipy import stats

FIELDS = (("out_of_road_rate", "이탈"), ("crash_rate", "충돌"), ("success_rate", "성공"))


def per_seed_tau(pattern, field):
    out = []
    for f in sorted(glob.glob(pattern)):
        rows = sorted(json.load(open(f)), key=lambda r: r["elapsed_s"])
        rows = [r for r in rows if r["ckpt"] != "final.pt"]   # final 은 시간축이 어긋난다
        if len(rows) < 4:
            continue
        out.append(stats.kendalltau([r["elapsed_s"] for r in rows],
                                    [r[field] for r in rows]))
    return out


def fisher(ps):
    chi = -2 * sum(np.log(max(p, 1e-12)) for p in ps)
    return chi, stats.chi2.sf(chi, 2 * len(ps))


def report(name, pattern):
    print("== %s" % name)
    for field, label in FIELDS:
        ts = per_seed_tau(pattern, field)
        if not ts:
            print("   %s: 자료 없음" % label)
            continue
        chi, pf = fisher([p for _, p in ts])
        same = len({np.sign(t) for t, _ in ts}) == 1
        print("   %-4s τ=%s | 부호 일치 %s | Fisher χ²=%.2f df=%d p=%.4f"
              % (label, ", ".join("%+.2f" % t for t, _ in ts),
                 "예" if same else "아니오", chi, 2 * len(ts), pf))


def main():
    pats = sys.argv[1:] or ["bench_results/clean/eval_md__clean_s*.json",
                            "bench_results/fixed/eval_md__fix_s*.json"]
    for pat in pats:
        report(pat, pat)


if __name__ == "__main__":
    main()
