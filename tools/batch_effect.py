"""8월 시드와 9월 시드는 **교환 가능하지 않다** — 시드 보강의 1차 결과.

사전 등록(STATUS 2026-09-17)은 10시드를 **하나의 표본으로 묶어** 시드 단위 Welch 를 주
지표로 삼았다. 그 전제는 「추가된 5시드가 기존 5시드와 같은 조건에서 나왔다」는 것이고,
코드 동일성·장비 동일성·정숙 조건은 돌리기 전에 확인했다. 그러나 **처리량은 확인하지
않았다.** 벽시계 예산 실험에서 처리량은 결과를 직접 결정하는 양이다.

실측:
    경량   8월 141.95 ± 7.99 Msteps  →  9월 163.67 ± 0.74 Msteps   (**+15.3%**)
    네이티브 8월   3.95 ± 0.04 Msteps  →  9월   4.24 ± 0.04 Msteps   (**+7.3%**)

같은 1시간에 9월 런이 더 많이 학습했고, **경량이 두 배 더 이득**을 봤다. 9월 σ 가
경량에서 7.99 → 0.74 로 줄어든 것도 같은 방향의 증거다 — 8월 조건이 더 시끄러웠다.
(141.95M 은 논문이 「확정 정숙 조건」으로 인용하는 바로 그 값이다.)

따라서 묶어서 낸 p 는 **시드 효과와 조건 효과가 섞인 값**이다. 이 저장소가 이미 문서화한
교락(§7 조건 교락: 정숙 vs GPU 경합, 네이티브 62.0% → 53.3%)과 같은 종류다.

이 도구가 하는 것:
  (1) 배치별로 따로 낸 격차 — 같은 조건 안에서의 비교라 교락이 없다
  (2) 배치를 블록인자로 둔 팔 효과와 **상호작용**
  (3) 사전 등록대로 묶어서 낸 값 — 숨기지 않고 나란히 둔다
  (4) 시드 수준에서 처리량과 전이 성능의 관계 — 기제 점검

실행: .venv/Scripts/python.exe tools/batch_effect.py
"""
import glob
import io
import json
import os
import statistics as st
import sys

import numpy as np
from scipy import stats

ROOT = "bench_results/scenario_blocks"
BATCH = {
    "8월": {"경량": ["clean_s%d" % s for s in range(1, 6)],
            "네이티브": ["nd_s%d" % s for s in range(2, 7)]},
    "9월": {"경량": ["clean_s%d" % s for s in range(6, 11)],
            "네이티브": ["nd_s%d" % s for s in range(7, 12)]},
}
CAND = {"경량": ["bench_results/seeds6to10/eval_md__%s.json",
                 "bench_results/clean/eval_md__%s.json",
                 "bench_results/seeds45/eval_md__%s.json"],
        "네이티브": ["bench_results/seeds6to10/eval_md__%s.json",
                    "bench_results/native_desktop/eval_md__%s.json",
                    "bench_results/seeds45/eval_md__%s.json"]}


def block_mean(tag):
    """8블록 평균 성공률(%) — 주 지표와 같은 정의."""
    v = []
    for f in sorted(glob.glob(os.path.join(ROOT, "eval_md__%s__b*.json" % tag))):
        r = [x for x in json.load(io.open(f, encoding="utf-8")) if x["ckpt"] == "final.pt"]
        if r:
            v.append(100.0 * r[0]["success_rate"])
    return st.mean(v) if v else None


def msteps(arm, tag):
    for pat in CAND[arm]:
        f = pat % tag
        if os.path.exists(f):
            r = [x for x in json.load(io.open(f, encoding="utf-8"))
                 if x["ckpt"] == "final.pt"]
            if r:
                return r[0]["global_step"] / 1e6
    return None


def welch(a, b):
    t, p = stats.ttest_ind(a, b, equal_var=False)
    na, nb = len(a), len(b)
    va, vb = st.variance(a), st.variance(b)
    se = (va / na + vb / nb) ** 0.5
    df = (va / na + vb / nb) ** 2 / ((va / na) ** 2 / (na - 1) + (vb / nb) ** 2 / (nb - 1))
    crit = stats.t.ppf(0.975, df) * se
    d = st.mean(a) - st.mean(b)
    return d, t, df, p, (d - crit, d + crit)


def main():
    data = {bt: {arm: [block_mean(t) for t in tags] for arm, tags in d.items()}
            for bt, d in BATCH.items()}
    thr = {bt: {arm: [msteps(arm, t) for t in tags] for arm, tags in d.items()}
           for bt, d in BATCH.items()}
    for bt in data:
        for arm in data[bt]:
            if any(v is None for v in data[bt][arm]):
                print("결측: %s %s" % (bt, arm))
                return 2

    print("처리량 — 벽시계 1시간에 실제로 학습한 양 (Msteps, final.pt 기준)")
    for arm in ("경량", "네이티브"):
        a, b = thr["8월"][arm], thr["9월"][arm]
        print("  %-8s 8월 %8.2f ± %.2f   9월 %8.2f ± %.2f   **%+.1f%%**"
              % (arm, st.mean(a), st.stdev(a), st.mean(b), st.stdev(b),
                 100 * (st.mean(b) / st.mean(a) - 1)))
    print("  → 9월 런이 같은 1시간에 더 많이 학습했고, **경량이 두 배 더 이득**을 봤다.")
    print("    σ 도 경량에서 7.99 → 0.74 로 줄었다 — 8월 조건이 더 시끄러웠다는 증거다.")

    print("\n(1) 배치별 격차 — 같은 조건 안의 비교라 교락이 없다")
    gaps = {}
    for bt in ("8월", "9월"):
        L, N = data[bt]["경량"], data[bt]["네이티브"]
        d, t, df, p, ci = welch(L, N)
        gaps[bt] = d
        print("  %-4s 경량 %.1f ± %.1f  대  네이티브 %.1f ± %.1f  격차 %+.1f%%p"
              % (bt, st.mean(L), st.stdev(L), st.mean(N), st.stdev(N), d))
        print("       Welch t=%.2f df=%.1f p=%.3f  95%% CI [%+.1f, %+.1f]"
              % (t, df, p, ci[0], ci[1]))

    print("\n(2) 배치를 블록인자로 — 팔 효과와 상호작용")
    inter = gaps["9월"] - gaps["8월"]
    arm_eff = (gaps["8월"] + gaps["9월"]) / 2
    print("  팔 효과(두 배치 평균) %+.1f%%p" % arm_eff)
    print("  **상호작용 %+.1f%%p** — 9월 조건에서 격차가 %s"
          % (inter, "좁아진다" if inter > 0 else "벌어진다"))
    # 상호작용의 검정: 배치별 격차 둘의 차이를 셀 분산으로
    ses = []
    for bt in ("8월", "9월"):
        L, N = data[bt]["경량"], data[bt]["네이티브"]
        ses.append(st.variance(L) / len(L) + st.variance(N) / len(N))
    se_i = sum(ses) ** 0.5
    z = inter / se_i
    print("  상호작용 근사 검정 z=%.2f (p≈%.3f) — n=5 셀이라 검정력이 낮다"
          % (z, 2 * (1 - stats.norm.cdf(abs(z)))))

    print("\n(3) 사전 등록대로 **묶어서** 낸 값 (숨기지 않는다)")
    L = data["8월"]["경량"] + data["9월"]["경량"]
    N = data["8월"]["네이티브"] + data["9월"]["네이티브"]
    d, t, df, p, ci = welch(L, N)
    print("  경량 %.1f ± %.1f  대  네이티브 %.1f ± %.1f  (각 n=10)"
          % (st.mean(L), st.stdev(L), st.mean(N), st.stdev(N)))
    print("  격차 %+.1f%%p  Welch t=%.2f df=%.1f **p=%.3f**  95%% CI [%+.1f, %+.1f]"
          % (d, t, df, p, ci[0], ci[1]))
    print("  ★ 이 값은 **시드 효과와 조건 효과가 섞여 있다.** 두 배치의 처리량이 다르고")
    print("    그 차이가 팔마다 다르므로(상호작용), 묶은 p 를 헤드라인으로 쓰면 안 된다.")

    print("\n(4) 기제 점검 — 처리량이 높은 시드가 실제로 더 잘 전이하는가 (팔 안에서)")
    for arm in ("경량", "네이티브"):
        x = thr["8월"][arm] + thr["9월"][arm]
        y = data["8월"][arm] + data["9월"][arm]
        r, pr = stats.pearsonr(x, y)
        rs, ps = stats.spearmanr(x, y)
        print("  %-8s Pearson r=%+.2f (p=%.3f)  Spearman ρ=%+.2f (p=%.3f)  n=%d"
              % (arm, r, pr, rs, ps, len(x)))
    print("  상관이 양이면 「처리량이 결과를 민다」는 해석과 정합한다. 다만 배치가")
    print("  처리량과 완전히 겹치므로 이 상관은 **배치 효과와 분리되지 않는다**.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
