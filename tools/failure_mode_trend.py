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


def per_seed_tau(pattern, field, include_final=False):
    """시드별 Kendall τ.

    final.pt 는 기본으로 제외하되 include_final 로 포함할 수 있다. 제외 사유는 시간축
    문제가 **아니다** — 정숙 런의 final 은 t003300 에서 정확히 300s 뒤로 등간격 위에 있다.
    종점 체크포인트가 추세 통계에 미치는 지렛대가 커서 양쪽을 병기하려는 것이며,
    실제로 충돌률 추세는 final 포함 시 유의성을 잃는다(§6.2 에 그대로 보고).
    """
    out = []
    for f in sorted(glob.glob(pattern)):
        rows = sorted(json.load(open(f)), key=lambda r: r["elapsed_s"])
        if not include_final:
            rows = [r for r in rows if r["ckpt"] != "final.pt"]
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
        for inc in (False, True):
            ts = per_seed_tau(pattern, field, include_final=inc)
            if not ts:
                if not inc:
                    print("   %s: 자료 없음" % label)
                continue
            chi, pf = fisher([p for _, p in ts])
            same = len({np.sign(t) for t, _ in ts}) == 1
            print("   %-4s final %s τ=%s | 부호 일치 %s | Fisher p=%.4f"
                  % (label, "포함" if inc else "제외",
                     ", ".join("%+.2f" % t for t, _ in ts),
                     "예" if same else "아니오", pf))


def main():
    pats = sys.argv[1:] or ["bench_results/clean/eval_md__clean_s*.json",
                            "bench_results/fixed/eval_md__fix_s*.json"]
    for pat in pats:
        report(pat, pat)


if __name__ == "__main__":
    main()
