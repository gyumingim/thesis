"""시드 축 σ 를 **참 정책 분산과 평가 잡음으로 가른다** — 「팔당 25시드 필요」의 근거 점검.

§2.5 는 팔당 5시드의 검정력이 0.19 이고 관측 격차를 80% 로 검출하려면 **팔당 25시드
(총 50시간)** 가 필요하다고 적었다. 그 계산은 시드 간 표준편차를 통째로 «정책 분산» 으로
본다. 그런데 시드마다 성공률을 **30에피소드 한 블록**으로 쟀으므로 그 σ 에는 평가 잡음이
섞여 있다. 섞인 만큼 필요한 시드 수는 과대평가된다.

이제 가를 수 있다 — §7 표 6 의 자료가 시드마다 **블록 8개**를 준다(반복 측정).
시드 × 블록 이원 분해(반복 없음)로 세 성분을 나눈다:

    y[s][b] = μ + α_s(정책) + β_b(블록 난이도) + ε[s][b](잔차)

  - σ_정책 : 시드를 늘려야만 줄어든다. **검정력 계산에 들어가야 하는 것은 이것이다.**
  - σ_블록 : 두 팔이 같은 블록을 보므로 **격차에서는 상쇠**된다.
  - σ_잔차 : 시드×블록 상호작용 + 이항 표집. 블록을 늘리면 줄어든다.

잔차를 **이항 바닥**(p(1−p)/30)과 비교하면 상호작용이 실재하는지도 보인다 — 잔차가
바닥과 같으면 «정책마다 어려워하는 블록이 다르다» 는 증거가 없다는 뜻이다.

실행: .venv/Scripts/python.exe tools/variance_components.py
"""
import glob
import io
import json
import os
import sys

import numpy as np
from scipy import stats

ROOT = "bench_results/scenario_blocks"
# 시드 목록 — 2026-09-17 에 팔당 5 → 10 으로 보강했다(bench/run_seeds6to10.sh).
# ARM_SEEDS=5 로 옛 표본을 그대로 재현할 수 있게 남겨 둔다 — 논문이 n=5 행과 n=10 행을
# 나란히 싣기 때문이고, 「바뀐 것은 표본뿐」임을 언제든 다시 보일 수 있어야 한다.
# ★ 기본값은 **5(8월 배치)** 다. 2026-09-17 에 팔당 10시드를 채웠지만 9월 배치는
#   처리량이 다르고(경량 +15.3%, 네이티브 +7.3%) 그 차이가 팔마다 다르므로, 묶으면
#   조건 효과가 섞인다(§7 배치 효과, tools/batch_effect.py). 조건이 통제된 표본은
#   **8월 배치**이고 논문의 모든 수치가 그것이다. ARM_SEEDS=10 은 묶은 값을 보고
#   싶을 때만 쓰며, 그 값은 헤드라인으로 쓸 수 없다.
_NS = int(os.environ.get("ARM_SEEDS", "5"))
ARMS = {"경량": ["clean_s%d" % s for s in range(1, 1 + _NS)],
        "네이티브": ["nd_s%d" % s for s in range(2, 2 + _NS)]}
N_EP = 30


def table(tags, blocks):
    Y = np.full((len(tags), len(blocks)), np.nan)
    for i, t in enumerate(tags):
        for j, b in enumerate(blocks):
            f = os.path.join(ROOT, "eval_md__%s__b%d.json" % (t, b))
            if os.path.exists(f):
                rows = json.load(io.open(f, encoding="utf-8"))
                r = [x for x in rows if x["ckpt"] == "final.pt"]
                if r:
                    Y[i, j] = 100.0 * r[0]["success_rate"]
    return Y


def decompose(Y):
    """반복 없는 이원 분해 → (σ²_시드, σ²_블록, σ²_잔차)."""
    S, B = Y.shape
    g = Y.mean()
    rs, cs = Y.mean(1), Y.mean(0)
    ms_s = B * np.sum((rs - g) ** 2) / (S - 1)
    ms_b = S * np.sum((cs - g) ** 2) / (B - 1)
    resid = Y - rs[:, None] - cs[None, :] + g
    ms_e = np.sum(resid ** 2) / ((S - 1) * (B - 1))
    return max((ms_s - ms_e) / B, 0.0), max((ms_b - ms_e) / S, 0.0), ms_e


def seeds_for(delta, sds, B, power=0.8):
    """격차 delta 를 power 로 검출하는 데 필요한 팔당 시드 수 (블록 B개 평균 기준).

    ★ z 근사가 아니라 논문이 쓴 것과 **같은** 몬테카를로 Welch 검정력을 쓴다
      (tools/power_mde.power_welch). 다른 정의로 계산하면 「25시드」와 비교가 안 된다.
    """
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from power_mde import power_welch
    var = [sp ** 2 + se ** 2 / B for sp, se in sds]
    d = delta / (sum(var) / 2) ** 0.5             # pooled SD 기준 효과크기
    for n in range(3, 200):
        if power_welch(d, n, n_mc=40000, seed=3) >= power:
            return n, d
    return float("nan"), d


def main():
    blocks = sorted({int(os.path.basename(f).split("__b")[1][:-5])
                     for f in glob.glob(os.path.join(ROOT, "*.json"))})
    if len(blocks) < 3:
        print("블록이 부족하다 — bench/run_scenario_blocks.sh 를 먼저 돌려라.")
        return 2
    print("시드 × 블록 = 5 × %d (final.pt, 30에피소드, 결정론)" % len(blocks))

    res = {}
    print("")
    print("분산 성분 (단위 %p)")
    print("  %-8s %10s %10s %10s %12s" % ("팔", "σ_정책", "σ_블록", "σ_잔차", "이항 바닥"))
    for arm, tags in ARMS.items():
        Y = table(tags, blocks)
        if np.isnan(Y).any():
            print("  %s: 결측 있음" % arm)
            return 2
        vp, vb, ve = decompose(Y)
        pr = Y / 100.0
        floor = float(np.mean(pr * (1 - pr)) / N_EP) * 100.0 ** 2
        res[arm] = (vp ** 0.5, ve ** 0.5, floor ** 0.5, Y)
        print("  %-8s %10.1f %10.1f %10.1f %12.1f"
              % (arm, vp ** 0.5, vb ** 0.5, ve ** 0.5, floor ** 0.5))
    print("  이항 바닥 = 30에피소드 표집만으로 생기는 σ. 잔차가 이 값과 비슷하면")
    print("  시드×블록 상호작용(정책마다 어려운 블록이 다름)의 증거가 없다는 뜻이다.")

    print("")
    print("단일 블록 σ 와의 비교 — 논문의 검정력 계산이 쓴 값")
    for arm in ARMS:
        Y = res[arm][3]
        s1 = float(np.mean([np.std(Y[:, j], ddof=1) for j in range(Y.shape[1])]))
        print("  %-8s 단일 블록 시드 σ %.1f%%p  →  그중 참 정책 σ %.1f%%p (%.0f%%)"
              % (arm, s1, res[arm][0], 100 * res[arm][0] / s1 if s1 else 0))

    sds = [(res[a][0], res[a][1]) for a in ARMS]
    sd1 = [(float(np.mean([np.std(res[a][3][:, q], ddof=1)
                           for q in range(res[a][3].shape[1])])), 0.0) for a in ARMS]
    print("")
    print("필요한 팔당 시드 수 (양측 α=0.05, 검정력 0.8, 논문과 같은 몬테카를로 Welch)")
    print("  %-32s %8s %10s" % ("설계 / 표적 격차", "시드/팔", "효과크기 d"))
    n0, d0 = seeds_for(12.7, sd1, 1)
    print("  %-32s %8s %10.2f" % ("블록 1개 · 12.7%p (논문 설정)", n0, d0))
    n1, d1 = seeds_for(19.7, sd1, 1)
    print("  %-32s %8s %10.2f" % ("블록 1개 · 19.7%p", n1, d1))
    for B in (1, 4, 8, 16):
        nb, db = seeds_for(19.7, sds, B)
        lab = ("블록 1개 (성분 합성·검산)" if B == 1 else "블록 %d개 평균 · 19.7%%p" % B)
        print("  %-32s %8s %10.2f" % (lab, nb, db))
    nf, df_ = seeds_for(19.7, [(sp, 0.0) for sp, _ in sds], 1)
    print("  %-32s %8s %10.2f" % ("평가 잡음 0 (이론 하한)", nf, df_))
    print("")
    print("  두 가지가 갈린다. (1) 논문의 「팔당 25시드」는 **b500000 한 블록의 격차**")
    print("  12.7%p 를 표적으로 하고 평가 잡음이 섞인 σ 를 쓴 값이다. (2) 블록 평균으로")
    print("  얻은 격차 19.7%p 를 표적으로 하고 σ 를 성분 분해하면 요구가 크게 준다.")
    print("  블록을 늘리는 것이 싼 이유는 **재학습이 필요 없기 때문**이다 — 보관")
    print("  체크포인트를 다시 평가하면 되고, 시드는 학습을 다시 해야 한다.")
    print("  다만 참 정책 σ 는 블록으로 줄지 않으므로 **시드 수의 하한**은 남는다.")
    print("")
    print("  ★ 경고: 이 계산은 **관측 효과크기**를 참값으로 놓는다. 19.7%p 의 95% 구간은")
    print("    [−41.8, +2.3] 이므로 필요한 시드 수도 그만큼 불확실하다. 논문이 「관측 p 에서")
    print("    미래 검정력을 역추론하지 말라」고 적은 것과 같은 함정이 여기에도 있다 —")
    print("    이 수치는 **계획용 눈금**이지 보장이 아니다.")
    print("  ★ 검산: 「블록 1개 · 12.7%p」가 논문의 「팔당 25시드」를 재현하는지부터 보라.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
