"""헤드라인 비교 확정 — 동일 장비·정숙 조건에서 경량 전이 대 MetaDrive 네이티브.

논문의 주 판정은 오래도록 **장비 교차 비교**에 걸려 있었다: 경량 48.9% 는 데스크톱
(RTX 5080) 정숙 조건, 네이티브 68%±9% 는 노트북(RTX 4060) 5시드였다. 이 스크립트는
같은 데스크톱·같은 정숙 조건·같은 프로토콜로 학습한 네이티브 3시드와 대조해 그 교락을
없앤 결과를 낸다.

세 가지를 한꺼번에 낸다.
 1. 최종 성능 대조 (Welch, 효과크기, 구간)
 2. 벽시계 도달 시간 — 네이티브가 경량의 피크 수준에 도달하는 데 걸린 시간
 3. 실현 처리량 배수 (같은 장비·같은 조건의 스텝 수 비)

실행: python tools/headline_compare.py
"""
import glob
import json

import numpy as np
from scipy import stats

LIGHT = "bench_results/clean/eval_md__clean_s*.json"
NATIVE_DESKTOP = "bench_results/native_desktop/eval_md__nd_s*.json"
NATIVE_LAPTOP = [63.0, 57.0, 70.0, 80.0, 70.0]     # 원자료는 노트북에 있다(§6.2 표 1)


def load(pattern):
    out = []
    for f in sorted(glob.glob(pattern)):
        rows = sorted(json.load(open(f)), key=lambda r: r["elapsed_s"])
        fin = [r for r in rows if r["ckpt"] == "final.pt"]
        # 시각은 시드마다 몇 초씩 어긋나므로 300초 격자로 묶는다(정확 일치로 묶으면
        # 한 시드 값만 잡혀 '평균 곡선'이 아니라 단일 시드 곡선이 된다 — 실제로 밟은 함정).
        ck = [(round(r["elapsed_s"] / 300) * 300, 100 * r["success_rate"])
              for r in rows if r["ckpt"] != "final.pt"]
        if fin:
            out.append(dict(name=f.split("__")[-1][:-5],
                            final=100 * fin[0]["success_rate"],
                            steps=fin[0]["global_step"],
                            elapsed=fin[0]["elapsed_s"], curve=ck))
    return out


def welch(a, b):
    t, p = stats.ttest_ind(a, b, equal_var=False)
    na, nb = len(a), len(b)
    se = np.sqrt(np.var(a, ddof=1) / na + np.var(b, ddof=1) / nb)
    df = se ** 4 / ((np.var(a, ddof=1) / na) ** 2 / (na - 1) +
                    (np.var(b, ddof=1) / nb) ** 2 / (nb - 1))
    tcrit = stats.t.ppf(0.975, df)
    d = np.mean(a) - np.mean(b)
    return t, p, df, (d - tcrit * se, d + tcrit * se)


def reach(curve, level):
    hit = [t for t, v in curve if v >= level]
    return min(hit) if hit else None


def main():
    light, nat = load(LIGHT), load(NATIVE_DESKTOP)
    if not nat:
        print("데스크톱 네이티브 평가 결과가 아직 없다:", NATIVE_DESKTOP)
        return
    lf = [r["final"] for r in light]
    nf = [r["final"] for r in nat]

    print("== 최종 성능 (1시간 예산, 30ep 결정론)")
    print("  경량 전이 (데스크톱 정숙, n=%d): %.1f%% ± %.1f  %s"
          % (len(lf), np.mean(lf), np.std(lf, ddof=1), [round(v, 1) for v in lf]))
    print("  네이티브 (데스크톱 정숙, n=%d): %.1f%% ± %.1f  %s"
          % (len(nf), np.mean(nf), np.std(nf, ddof=1), [round(v, 1) for v in nf]))
    print("  네이티브 (노트북, n=5, 참고):   %.1f%% ± %.1f"
          % (np.mean(NATIVE_LAPTOP), np.std(NATIVE_LAPTOP, ddof=1)))
    if len(lf) > 1 and len(nf) > 1:
        t, p, df, ci = welch(lf, nf)
        print("  동일 장비 Welch: t=%.2f df=%.1f p=%.3f | 차이 %.1f%%p, 95%% CI [%.1f, %.1f]"
              % (t, df, p, np.mean(lf) - np.mean(nf), ci[0], ci[1]))
        t2, p2, df2, ci2 = welch(lf, NATIVE_LAPTOP)
        print("  장비 교차 Welch(참고): t=%.2f df=%.1f p=%.3f | 차이 %.1f%%p"
              % (t2, df2, p2, np.mean(lf) - np.mean(NATIVE_LAPTOP)))

    print()
    print("== 벽시계 도달 시간 (경량의 피크 수준에 네이티브는 언제 도달하나)")
    grid = sorted({t for r in light for t, _ in r["curve"]})
    peak_t, peak_v = max(((t, float(np.mean([v for r in light for tt, v in r["curve"] if tt == t])))
                          for t in grid), key=lambda x: x[1])
    print("  경량 피크: %.1f%% @ %.0fs" % (peak_v, peak_t))
    for label, runs in (("네이티브(데스크톱 정숙)", nat),):
        hits = [reach(r["curve"], peak_v) for r in runs]
        got = [h for h in hits if h]
        print("  %s 도달: %d/%d 시드, %s" % (label, len(got), len(runs),
              ("중앙값 %.0fs (경량 대비 %.1f배)" % (np.median(got), np.median(got) / peak_t))
              if got else "예산 안에 미도달"))
        print("     시드별:", ["%.0fs" % h if h else "미도달" for h in hits])

    print()
    print("== 실현 처리량 (같은 장비·같은 조건)")
    ls = np.mean([r["steps"] for r in light])
    ns = np.mean([r["steps"] for r in nat])
    print("  경량 %.2fM steps / 네이티브 %.2fM steps = **%.1f배**" % (ls / 1e6, ns / 1e6, ls / ns))
    print("  (경량 %.0f SPS, 네이티브 %.0f SPS)"
          % (ls / np.mean([r["elapsed"] for r in light]),
             ns / np.mean([r["elapsed"] for r in nat])))


if __name__ == "__main__":
    main()
