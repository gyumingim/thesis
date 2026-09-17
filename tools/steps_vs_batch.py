"""배치 차이는 **처리량 때문인가** — 같은 «스텝 수» 에서 두 배치를 맞대어 본다.

§7 배치 효과: 9월 배치가 8월보다 같은 1시간에 더 많이 학습했고(경량 +15.3%, 네이티브
+7.3%) 격차도 좁았다(−19.8 → −9.1%p). 두 해석이 가능하다.

  (A) **처리량 해석** — 9월 런이 더 많이 학습해서 더 잘한다. 그렇다면 **스텝 수를 맞추면**
      두 배치가 같은 곡선 위에 있어야 한다.
  (B) **그 밖의 조건 변화** — 3주 사이에 처리량 말고 다른 것이 바뀌었다(드라이버·발열·
      배경 상태 등). 그렇다면 스텝을 맞춰도 9월이 여전히 높다.

가를 수 있다. 체크포인트마다 `global_step` 과 전이 성공률이 **이미 저장돼 있다**(12개
체크포인트 × b500000 30에피소드). 재학습도 재평가도 필요 없다.

방법: 두 배치가 **모두 도달한** 스텝 예산에서 각 런의 곡선을 선형보간해 성공률을 읽고,
배치 간 Welch 로 비교한다. 예산은 8월 런의 최솟값 이하로 잡아 외삽을 피한다.

한계: 여기 쓰는 전이 점수는 **b500000 한 블록 30에피소드**다(체크포인트 단위로 저장된
유일한 자료). §7 표 6 의 8블록 평균보다 잡음이 크다 — 그래서 유의성보다 **점추정의
방향과 크기**를 본다.

실행: .venv/Scripts/python.exe tools/steps_vs_batch.py
"""
import io
import json
import os
import statistics as st
import sys

import numpy as np
from scipy import stats

SRC = {
    ("경량", "8월"): ("bench_results/clean/eval_md__clean_s%d.json", range(1, 6)),
    ("경량", "9월"): ("bench_results/seeds6to10/eval_md__clean_s%d.json", range(6, 11)),
    ("네이티브", "8월"): ("bench_results/native_desktop/eval_md__nd_s%d.json", range(2, 7)),
    ("네이티브", "9월"): ("bench_results/seeds6to10/eval_md__nd_s%d.json", range(7, 12)),
}


def curve(path):
    """(스텝 오름차순 배열, 성공률%) — final.pt 는 마지막 체크포인트와 같은 시점이라 뺀다."""
    if not os.path.exists(path):
        return None
    rows = [r for r in json.load(io.open(path, encoding="utf-8")) if r["ckpt"] != "final.pt"]
    if not rows:
        return None
    rows.sort(key=lambda r: r["global_step"])
    x = np.array([r["global_step"] / 1e6 for r in rows], float)
    y = np.array([100.0 * r["success_rate"] for r in rows], float)
    return x, y


def at(x, y, budget):
    """스텝 예산에서의 성공률 — 선형보간. 범위 밖이면 None(외삽하지 않는다)."""
    if budget < x[0] or budget > x[-1]:
        return None
    return float(np.interp(budget, x, y))


def main():
    C = {}
    for key, (pat, seeds) in SRC.items():
        cs = [curve(pat % s) for s in seeds]
        cs = [c for c in cs if c is not None]
        if len(cs) < 3:
            print("자료 부족: %s %s (%d개)" % (key[0], key[1], len(cs)))
            return 2
        C[key] = cs

    for arm in ("경량", "네이티브"):
        a, b = C[(arm, "8월")], C[(arm, "9월")]
        top_a = min(c[0][-1] for c in a)      # 8월 런이 모두 도달한 최대 스텝
        top_b = min(c[0][-1] for c in b)
        lo = max(max(c[0][0] for c in a), max(c[0][0] for c in b))
        hi = min(top_a, top_b)
        print("\n=== %s ===" % arm)
        print("  겹치는 스텝 구간 %.1f ~ %.1f Msteps (8월 도달 %.1f, 9월 도달 %.1f)"
              % (lo, hi, top_a, top_b))
        if hi <= lo:
            print("  겹치는 구간이 없다 — 이 팔에서는 스텝 정렬 비교가 불가능하다.")
            continue
        print("  %10s %20s %20s %10s %8s"
              % ("스텝 예산", "8월 (n=%d)" % len(a), "9월 (n=%d)" % len(b), "차이", "Welch p"))
        for frac in (0.5, 0.7, 0.85, 1.0):
            # ★ 부동소수 때문에 lo+(hi-lo)*1.0 이 hi 를 아주 조금 넘어, 끝점이 정확히
            #   hi 인 런 하나가 at() 에서 None 이 되어 **조용히 빠졌다**(8월 n=5 → 4).
            #   그 상태로 +7.6%p 를 읽었는데 전수로는 +10.9%p 다. 경계는 클램프한다.
            bud = min(lo + (hi - lo) * frac, hi)
            va = [v for v in (at(*c, bud) for c in a) if v is not None]
            vb = [v for v in (at(*c, bud) for c in b) if v is not None]
            if len(va) < 3 or len(vb) < 3:
                continue
            p = stats.ttest_ind(vb, va, equal_var=False).pvalue
            print("  %9.1fM %11.1f ± %-6.1f %11.1f ± %-6.1f %+9.1f %8.3f  (n=%d/%d)"
                  % (bud, st.mean(va), st.stdev(va), st.mean(vb), st.stdev(vb),
                     st.mean(vb) - st.mean(va), p, len(va), len(vb)))
        # 각 배치가 실제로 도달한 끝점(스텝이 다르다) — 대조용
        ea = [c[1][-1] for c in a]
        eb = [c[1][-1] for c in b]
        print("  %-9s %11.1f ± %-6.1f %11.1f ± %-6.1f %+9.1f %8.3f   ← 스텝 **미정렬**"
              % ("각자 끝점", st.mean(ea), st.stdev(ea), st.mean(eb), st.stdev(eb),
                 st.mean(eb) - st.mean(ea),
                 stats.ttest_ind(eb, ea, equal_var=False).pvalue))

    print("\n판정 규칙")
    print("  스텝을 맞췄을 때 차이가 **사라지면** (A) 처리량 해석 — 9월이 더 잘한 이유는")
    print("  더 많이 학습했기 때문이다. 배치 효과는 곧 처리량 효과이고, §7 의 «시드를 늘릴")
    print("  때 배치를 통제하라» 는 «처리량을 맞추라» 로 구체화된다.")
    print("  스텝을 맞춰도 9월이 **여전히 높으면** (B) 다른 조건이 바뀐 것이고, 그것이")
    print("  무엇인지는 이 자료로 알 수 없다 — 그때는 배치 자체를 통제해야 한다.")
    print("  ※ 전이 점수는 b500000 한 블록 30에피소드라 잡음이 크다. 유의성보다 점추정의")
    print("    방향과 크기를 본다.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
