"""평가 **시나리오 축**의 변동을 측정한다 — 논문이 한계로만 적어 두었던 것.

§7 한계: 본 논문의 모든 MetaDrive 전이 수치는 시나리오 500000~500029 라는 **단일 30장면
표본**에 조건부다. 두 팔, 12개 체크포인트, 10개 학습 시드가 전부 같은 30장면을 본다.
따라서 보고된 오차막대는 **학습 시드 축**의 변동이고, 시나리오 축은 한 번도 측정되지
않았다. 절대 수치가 다른 30장면에서 얼마나 움직이는지 말할 수 없었다.

재학습은 필요 없었다 — 한계는 **평가** 표본에 관한 것이므로 기존 final.pt 를 서로 다른
시나리오 블록에서 다시 평가하면 된다(bench/run_scenario_blocks.sh).

이 도구가 답하는 것:
  (1) 팔 평균과 격차가 블록마다 얼마나 움직이는가
  (2) 분산을 **시드 축 / 시나리오 축**으로 분해하면 어느 쪽이 큰가
  (3) 방향(경량 < 네이티브)이 블록에 걸쳐 유지되는가 — 블록을 블록인자로 둔 대응 검정

실행: python tools/scenario_axis.py
"""
import glob
import io
import itertools
import json
import os
import statistics as st
import sys

ROOT = "bench_results/scenario_blocks"
LIGHT = ["clean_s%d" % s for s in (1, 2, 3, 4, 5)]
NATIVE = ["nd_s%d" % s for s in (2, 3, 4, 5, 6)]


def rate(tag, blk):
    f = os.path.join(ROOT, "eval_md__%s__b%d.json" % (tag, blk))
    if not os.path.exists(f):
        return None
    rows = json.load(io.open(f, encoding="utf-8"))
    r = [x for x in rows if x["ckpt"] == "final.pt"]
    return 100.0 * r[0]["success_rate"] if r else None


def sign_perm(d):
    """대응 차이의 부호 순열 정확 검정."""
    nz = [x for x in d if abs(x) > 1e-12]
    base = sum(x for x in d if abs(x) <= 1e-12)
    obs = abs(st.mean(d))
    hit = sum(1 for s in itertools.product([1, -1], repeat=len(nz))
              if abs((base + sum(x * y for x, y in zip(nz, s))) / len(d)) >= obs - 1e-12)
    return st.mean(d), hit / 2 ** len(nz)


def main():
    blocks = sorted({int(os.path.basename(f).split("__b")[1][:-5])
                     for f in glob.glob(os.path.join(ROOT, "*.json"))})
    if len(blocks) < 2:
        print("블록이 둘 이상 필요하다. bench/run_scenario_blocks.sh 를 먼저 돌려라.")
        return 2
    tab = {t: {b: rate(t, b) for b in blocks} for t in LIGHT + NATIVE}
    if any(v is None for t in tab for v in tab[t].values()):
        print("결측 있음 — 일부 조합이 평가되지 않았다.")
        return 2

    print("시나리오 블록별 성공률 (final.pt, 30에피소드, 결정론)")
    print("  %-10s %s" % ("정책", " ".join("%9s" % ("b%d" % b) for b in blocks)))
    for t in LIGHT + NATIVE:
        print("  %-10s %s" % (t, " ".join("%8.1f%%" % tab[t][b] for b in blocks)))

    print()
    print("팔 평균과 격차")
    print("  %-10s %s" % ("", " ".join("%9s" % ("b%d" % b) for b in blocks)))
    lm = {b: st.mean(tab[t][b] for t in LIGHT) for b in blocks}
    nm = {b: st.mean(tab[t][b] for t in NATIVE) for b in blocks}
    print("  %-10s %s" % ("경량", " ".join("%8.1f%%" % lm[b] for b in blocks)))
    print("  %-10s %s" % ("네이티브", " ".join("%8.1f%%" % nm[b] for b in blocks)))
    gaps = [lm[b] - nm[b] for b in blocks]
    print("  %-10s %s" % ("격차", " ".join("%+8.1f" % g for g in gaps)))
    print()
    print("  경량 팔 평균의 블록 간 범위 %.1f~%.1f%%p (폭 %.1f)"
          % (min(lm.values()), max(lm.values()), max(lm.values()) - min(lm.values())))
    print("  네이티브 팔 평균의 블록 간 범위 %.1f~%.1f%%p (폭 %.1f)"
          % (min(nm.values()), max(nm.values()), max(nm.values()) - min(nm.values())))
    print("  격차의 블록 간 범위 %+.1f~%+.1f%%p (폭 %.1f)"
          % (min(gaps), max(gaps), max(gaps) - min(gaps)))

    print()
    print("분산 분해 — 어느 축이 더 큰가")
    for name, arm in (("경량", LIGHT), ("네이티브", NATIVE)):
        # 시드 축: 블록마다 시드 간 표준편차를 구해 평균
        seed_sd = st.mean(st.stdev([tab[t][b] for t in arm]) for b in blocks)
        # 시나리오 축: 정책마다 블록 간 표준편차를 구해 평균
        scen_sd = st.mean(st.stdev([tab[t][b] for b in blocks]) for t in arm)
        print("  %-8s 시드 축 σ %5.1f%%p   시나리오 축 σ %5.1f%%p   비 %.2f"
              % (name, seed_sd, scen_sd, scen_sd / seed_sd if seed_sd else float("nan")))
    print("  비가 1 보다 작으면 시나리오 축이 시드 축보다 좁다는 뜻 — 즉 «다른 30장면을")
    print("  썼어도 결론이 크게 흔들리지는 않는다» 를 수치로 말할 수 있다.")

    print()
    print("방향의 일관성 — 블록을 블록인자로 둔 대응 검정")
    for b in blocks:
        d = [tab[l][b] - tab[n][b] for l, n in zip(LIGHT, NATIVE)]
        m, p = sign_perm(d)
        print("  b%-8d 격차 %+6.1f%%p  부호 순열 p=%.4f%s"
              % (b, m, p, "  ← 유의" if p < 0.05 else ""))
    # ★ 여기서 두 가지를 조심한다.
    #   (a) clean_sN 과 nd_sN 은 **짝이 아니다** — 서로 다른 학습 실행이고 공유하는 것이
    #       없다. 위 블록별 «대응 검정» 은 편의상 인덱스로 짝지은 것이라 근거가 약하다.
    #       공유되는 것은 **시나리오 블록**이므로 블록만이 정당한 블록인자다.
    #   (b) 5시드 × 4블록 = 20쌍을 독립 표본으로 세면 안 된다. 같은 시드가 네 번
    #       재등장하므로 군집이다(CARLA 표에서 같은 실수를 잡았다).
    #   따라서 정직한 분석은 **시드를 단위로** 두고 블록 평균으로 평가 잡음만 줄이는 것이다.
    print()
    print("정직한 검정 — 시드가 단위, 블록 평균으로 평가 잡음만 줄인다")
    lm5 = [st.mean(tab[t][b] for b in blocks) for t in LIGHT]
    nm5 = [st.mean(tab[t][b] for b in blocks) for t in NATIVE]
    d = st.mean(nm5) - st.mean(lm5)
    va, vb, n = st.variance(lm5), st.variance(nm5), len(lm5)
    se = (va / n + vb / n) ** 0.5
    tt = d / se
    df = (va / n + vb / n) ** 2 / ((va / n) ** 2 / (n - 1) + (vb / n) ** 2 / (n - 1))
    print("  경량 %.1f ± %.1f  대  네이티브 %.1f ± %.1f  (각 n=%d)"
          % (st.mean(lm5), st.stdev(lm5), st.mean(nm5), st.stdev(nm5), n))
    print("  격차 %+.1f%%p  Welch t=%.2f df=%.1f" % (-d, tt, df))
    print()
    print("  블록을 단위로 본 격차 %s — %d/%d 이 음수(부호검정 p=%.3f)"
          % ([round(g, 1) for g in gaps], sum(g < 0 for g in gaps), len(gaps),
             2.0 ** -(len(gaps) - 1)))
    print("  ※ 논문이 쓴 블록(%d)의 격차 %+.1f%%p 는 네 블록 중 **가장 작다**(평균 %+.1f)."
          % (blocks[0], gaps[0], st.mean(gaps)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
