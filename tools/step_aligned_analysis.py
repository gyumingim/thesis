"""스텝을 맞춘 **8블록** 배치 비교 — 「9월이 더 잘한 것은 더 많이 학습해서인가」.

앞선 단일 블록 정렬 검정은 비유의였는데, 그것이 «차이가 없다» 인지 «못 가렸다» 인지
구분되지 않았다. 8블록 평균으로 보면 배치 차이 자체는 경량 +16.1%p(p=0.025)로 유의하다.
그래서 **스텝을 맞춘 그 한 점만** 8블록으로 평가했다(bench/run_step_aligned.py, 140회).

읽는 법:
  - 정렬 후에도 9월이 높으면 → 처리량이 아닌 **다른 조건 변화**가 있다.
  - 정렬 후 차이가 사라지면 → 배치 효과 = 처리량 효과.
  - **격차**(경량−네이티브)가 정렬 후에도 배치마다 다르면, §7 의 상호작용은 처리량으로
    설명되지 않는다.

실행: .venv/Scripts/python.exe tools/step_aligned_analysis.py
"""
import io
import json
import os
import statistics as st
import sys

from scipy import stats

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ALIGNED = os.path.join(ROOT, "bench_results", "step_aligned")
BLOCKS = (510000, 520000, 530000, 540000, 550000, 560000, 570000)
PERCKPT = {
    ("clean", "8월"): "bench_results/clean/eval_md__clean_s%d.json",
    ("clean", "9월"): "bench_results/seeds6to10/eval_md__clean_s%d.json",
    ("nd", "8월"): "bench_results/native_desktop/eval_md__nd_s%d.json",
    ("nd", "9월"): "bench_results/seeds6to10/eval_md__nd_s%d.json",
}
NAME = {"clean": "경량", "nd": "네이티브"}


def b500(tag, batch, seed, ckpt):
    f = os.path.join(ROOT, PERCKPT[(tag, batch)] % seed)
    for r in json.load(io.open(f, encoding="utf-8")):
        if r["ckpt"] == ckpt:
            return 100.0 * r["success_rate"]
    return None


def eight(tag, seed, batch, ckpt):
    v = [b500(tag, batch, seed, ckpt)]
    for b in BLOCKS:
        f = os.path.join(ALIGNED, "eval_md__%s_s%d__b%d.json" % (tag, seed, b))
        if not os.path.exists(f):
            return None
        rows = json.load(io.open(f, encoding="utf-8"))
        v.append(100.0 * rows[0]["success_rate"])
    return None if any(x is None for x in v) else st.mean(v)


def final8(tag, seed):
    """정렬하지 않은 final.pt 의 8블록 평균 — 대조용."""
    import glob
    v = []
    for f in sorted(glob.glob(os.path.join(ROOT, "bench_results", "scenario_blocks",
                                           "eval_md__%s_s%d__b*.json" % (tag, seed)))):
        r = [x for x in json.load(io.open(f, encoding="utf-8")) if x["ckpt"] == "final.pt"]
        if r:
            v.append(100.0 * r[0]["success_rate"])
    return st.mean(v) if len(v) == 8 else None


def measure():
    """(정렬 후 A, 정렬 전 F, 정렬 스텝) — 감시가 print 를 파싱하지 않도록 계산을 분리한다."""
    plan = json.load(io.open(os.path.join(ALIGNED, "plan.json"), encoding="utf-8"))
    A, F, steps = {}, {}, {}
    for p in plan:
        k = (p["tag"], p["batch"])
        A.setdefault(k, []).append(eight(p["tag"], p["seed"], p["batch"], p["ckpt"]))
        F.setdefault(k, []).append(final8(p["tag"], p["seed"]))
        steps.setdefault(k, []).append(p["step"] / 1e6)
    return A, F, steps


def main():
    plan = json.load(io.open(os.path.join(ALIGNED, "plan.json"), encoding="utf-8"))
    A = {}
    F = {}
    steps = {}
    for p in plan:
        k = (p["tag"], p["batch"])
        val = eight(p["tag"], p["seed"], p["batch"], p["ckpt"])
        if val is None:
            print("결측: %s s%d" % (p["tag"], p["seed"]))
            return 2
        A.setdefault(k, []).append(val)
        F.setdefault(k, []).append(final8(p["tag"], p["seed"]))
        steps.setdefault(k, []).append(p["step"] / 1e6)

    print("스텝 정렬 8블록 — 배치 차이가 정렬 후에도 남는가 (팔 안에서 9월 − 8월)")
    print("  %-8s %-10s %14s %14s %10s %9s"
          % ("팔", "정렬", "8월", "9월", "차이", "Welch p"))
    for tag in ("clean", "nd"):
        for lab, D in (("정렬 전(final)", F), ("**정렬 후**", A)):
            a, b = D[(tag, "8월")], D[(tag, "9월")]
            p = stats.ttest_ind(b, a, equal_var=False).pvalue
            print("  %-8s %-10s %7.1f ± %-5.1f %7.1f ± %-5.1f %+9.1f %9.4f"
                  % (NAME[tag], lab, st.mean(a), st.stdev(a), st.mean(b), st.stdev(b),
                     st.mean(b) - st.mean(a), p))
        sa, sb = steps[(tag, "8월")], steps[(tag, "9월")]
        print("           (정렬 스텝 8월 %.1f ± %.1fM, 9월 %.1f ± %.1fM)"
              % (st.mean(sa), st.stdev(sa), st.mean(sb), st.stdev(sb)))

    print("\n격차(경량 − 네이티브)가 배치마다 다른가 — §7 상호작용의 정렬판")
    print("  %-12s %12s %12s %12s" % ("정렬", "8월 격차", "9월 격차", "상호작용"))
    for lab, D in (("정렬 전(final)", F), ("**정렬 후**", A)):
        g = {}
        for bt in ("8월", "9월"):
            g[bt] = st.mean(D[("clean", bt)]) - st.mean(D[("nd", bt)])
        print("  %-12s %+11.1f %+12.1f %+12.1f" % (lab, g["8월"], g["9월"],
                                                   g["9월"] - g["8월"]))

    print("\n판정")
    for tag in ("clean", "nd"):
        a, b = A[(tag, "8월")], A[(tag, "9월")]
        p = stats.ttest_ind(b, a, equal_var=False).pvalue
        d = st.mean(b) - st.mean(a)
        raw = st.mean(F[(tag, "9월")]) - st.mean(F[(tag, "8월")])
        share = 100 * (1 - d / raw) if raw else float("nan")
        print("  %-8s 정렬 후 %+.1f%%p (p=%.4f) — 정렬 전 %+.1f%%p 의 %.0f%% 가 "
              "스텝 차이로 설명된다" % (NAME[tag], d, p, raw, share))
    return 0


if __name__ == "__main__":
    sys.exit(main())
