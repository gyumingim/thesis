"""마스킹 구제가 **무엇을** 고치는가 — §5.2 (i)/(ii) 분해를 시나리오 짝으로 본다.

논문 §5.2 는 퇴화 차원 마스킹이 전이를 5%→55% 로 올린다고 보고하면서, 기제를 두 층위로
가설만 세우고 「본 자료로는 (ii)가 검증되지 않는다」 고 적었다:

  (i)  분포외 z-score 주입 → 정책 폭주. 마스킹으로 제거된다면 **도로 이탈**이 줄어야 한다.
  (ii) 정보 자체의 미학습. 마스킹된 정책은 셋째 차를 «없는 셈» 치므로, 그 차가 실제로
       위협일 때 실패한다 — 즉 **충돌은 남아야 한다**.

두 예측은 같은 성공률 변화 아래에서 **실패 구성**으로 갈린다. 총계만으로도 방향이 보이고
(이탈 58.3%→15.0%, 충돌 36.7%→30.0%), 여기서는 같은 30 시나리오를 짝지어 전이표까지 본다.
평가 시드가 같으므로 시나리오는 정확히 대응한다 — 짝지은 검정(McNemar)이 성립한다.

한계를 먼저 적는다: 정책 시드는 **둘뿐**이다. 시나리오 짝 검정은 «이 정책에서» 유효하고,
정책 축으로의 일반화는 n=2 에 걸려 있다. 두 시드가 같은 방향인지를 함께 본다.

실행: .venv/Scripts/python.exe tools/mask_mechanism.py
"""
import json
import math
import os
import sys

NAME = {1: "충돌", 2: "이탈", 3: "성공", 4: "타임아웃"}
ORDER = [3, 1, 2, 4]
D = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                 "bench_results", "mask_paired")
OLD = os.path.join(os.path.dirname(D), "support_fixed")


def load(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)[0]


def binom_two_sided(k, n):
    """p=0.5 이항의 양측 정확 p — McNemar 의 정확판(불일치 쌍이 적어 근사를 못 쓴다)."""
    if n == 0:
        return 1.0
    c = [math.comb(n, i) for i in range(n + 1)]
    tot = float(sum(c))
    obs = c[k]
    return min(1.0, sum(x for x in c if x <= obs + 1e-12) / tot)


def main():
    seeds = []
    for s in (1, 2):
        p = os.path.join(D, "eval_md__sup2plain_s%d.json" % s)
        m = os.path.join(D, "eval_md__sup2mask_s%d.json" % s)
        if not (os.path.exists(p) and os.path.exists(m)):
            print("원자료 없음 — bash bench/run_mask_paired.sh 를 먼저 돌려라 (%s)" % p)
            return 1
        seeds.append((s, load(p), load(m)))

    # ── 0. 재현 확인: 총계가 논문 원자료(support_fixed)와 같은가.
    print("재현 확인 — 새 평가가 논문 원자료의 총계를 재현하는가")
    bad = 0
    for s, p, m in seeds:
        for tag, new, oldf in (("무마스킹", p, "eval_md__sup2_s%d.json" % s),
                               ("마스킹", m, "eval_md__sup2mask_s%d.json" % s)):
            o = load(os.path.join(OLD, oldf))
            same = abs(o["success_rate"] - new["success_rate"]) < 1e-9
            bad += 0 if same else 1
            print("  s%d %-6s 구판 %.3f  신판 %.3f  %s"
                  % (s, tag, o["success_rate"], new["success_rate"],
                     "일치" if same else "**불일치**"))
    if bad:
        print("  ★ 결정론 평가가 재현되지 않았다. 아래 분석을 신뢰하지 마라.")

    # ── 1. 실패 구성
    print("\n실패 구성 — 마스킹은 무엇을 없애는가 (30에피소드/시드)")
    print("  %-6s %-8s %8s %8s %8s" % ("시드", "조건", "성공", "충돌", "이탈"))
    agg = {}
    for s, p, m in seeds:
        for tag, r in (("무마스킹", p), ("마스킹", m)):
            print("  s%-5d %-8s %7.1f%% %7.1f%% %7.1f%%"
                  % (s, tag, 100 * r["success_rate"], 100 * r["crash_rate"],
                     100 * r["out_of_road_rate"]))
            a = agg.setdefault(tag, [0.0, 0.0, 0.0])
            a[0] += r["success_rate"] / len(seeds)
            a[1] += r["crash_rate"] / len(seeds)
            a[2] += r["out_of_road_rate"] / len(seeds)
    print("  %-6s %-8s %7.1f%% %7.1f%% %7.1f%%"
          % ("평균", "무마스킹", *[100 * x for x in agg["무마스킹"]]))
    print("  %-6s %-8s %7.1f%% %7.1f%% %7.1f%%"
          % ("", "마스킹", *[100 * x for x in agg["마스킹"]]))
    dS = 100 * (agg["마스킹"][0] - agg["무마스킹"][0])
    dC = 100 * (agg["마스킹"][1] - agg["무마스킹"][1])
    dO = 100 * (agg["마스킹"][2] - agg["무마스킹"][2])
    print("  %-6s %-8s %+7.1f%s %+7.1f%s %+7.1f%s"
          % ("", "차이", dS, "%p", dC, "%p", dO, "%p"))
    print("  → 회복 %+.1f%%p 중 이탈 감소가 %.1f%%p, 충돌 감소가 %.1f%%p 를 설명한다."
          % (dS, -dO, -dC))

    # ── 2. 시나리오 짝 전이표
    print("\n시나리오 짝 전이표 — 같은 시나리오에서 무마스킹 → 마스킹 (두 시드 합산 60쌍)")
    T = {}
    per_seed_disc = []
    for s, p, m in seeds:
        pe = {e["scenario"]: e for e in p["per_episode"]}
        me = {e["scenario"]: e for e in m["per_episode"]}
        common = sorted(set(pe) & set(me))
        assert len(common) == len(pe) == len(me), "시나리오 집합이 어긋난다"
        b = c = 0
        for sc in common:
            T[(pe[sc]["flag"], me[sc]["flag"])] = T.get((pe[sc]["flag"], me[sc]["flag"]), 0) + 1
            if pe[sc]["success"] and not me[sc]["success"]:
                b += 1
            if me[sc]["success"] and not pe[sc]["success"]:
                c += 1
        per_seed_disc.append((s, b, c))
    print("      %s" % "".join("%8s" % ("→" + NAME[j]) for j in ORDER))
    for i in ORDER:
        row = [T.get((i, j), 0) for j in ORDER]
        if sum(row) == 0:
            continue
        print("  %-4s%s   (합 %d)" % (NAME[i], "".join("%8d" % v for v in row), sum(row)))

    # ── 3. 짝지은 검정
    print("\n짝지은 정확검정 (McNemar, 이항 양측)")
    tb = sum(b for _, b, _ in per_seed_disc)
    tc = sum(c for _, _, c in per_seed_disc)
    for s, b, c in per_seed_disc:
        print("  s%d  마스킹으로 성공→실패 %d, 실패→성공 %d, p=%.4f"
              % (s, b, c, binom_two_sided(min(b, c), b + c)))
    print("  합산 성공→실패 %d, 실패→성공 %d, p=%.5f (시드 내 짝만 집계)"
          % (tb, tc, binom_two_sided(min(tb, tc), tb + tc)))
    print("  ★ 이 검정은 «이 두 정책에서» 유효하다. 정책 축의 일반화는 n=2 에 걸려 있다.")

    # ── 4. 구제의 출처: 어떤 실패가 성공으로 바뀌었나
    print("\n구제의 출처 — 무마스킹 실패 종류별 성공 전환률")
    for i in (2, 1):
        tot = sum(v for (a, _), v in T.items() if a == i)
        won = T.get((i, 3), 0)
        if tot:
            print("  무마스킹 %-4s %2d건 중 %2d건이 성공으로 (%.0f%%)"
                  % (NAME[i], tot, won, 100.0 * won / tot))
    conv = T.get((2, 1), 0)
    print("  이탈 → 충돌로만 바뀐 것 %d건 (셋째 차를 «없는 셈» 친 결과라면 여기에 나타난다)"
          % conv)
    print("\n판정: (i) 폭주 제거는 이탈 감소로 %s. (ii) 미학습 잔존은 충돌이 %s."
          % ("나타난다" if dO < -5 else "나타나지 않는다",
             "남는 것으로 지지된다" if dC > -10 else "함께 줄어 지지되지 않는다"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
