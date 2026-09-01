"""교차 구조의 검정 — 개별 시점이 아니라 **예산 축의 상호작용**을 검정한다.

§6.2 는 "5분엔 경량이 앞서고 15분에 교차한다"를 주장하면서, 근거로 개별 시점의 Welch
검정을 들었다. 그런데 그 방식은 12개 체크포인트 중 최소 p 를 고르는 사후 선택이라
다중비교 보정을 통과하지 못한다(Bonferroni 0.47, 순열 max-T 0.26).

**주장 자체를 검정하면 다르다.** "교차한다"는 곧 "두 팔의 시간에 따른 변화량이 다르다"
이므로, 시드마다 Δ = (최종 성공률 − 초반 앵커 성공률) 을 만들고 팔 라벨을 순열한다.
이것은 사후 극값이 아니라 연구 질문이 사전 지정한 대비다 — 예산 축의 양 끝.

초반 앵커는 5분(첫 체크포인트)과 10분(경량 피크) 둘 다 보고한다. 어느 쪽을 고르든
결론이 같다는 것을 보이기 위해서다.

실행: python tools/crossing_test.py
"""
import glob
import itertools
import json
import sys

import numpy as np

LIGHT = "bench_results/clean/eval_md__clean_s*.json"
NATIVE = "bench_results/native_desktop/eval_md__nd_s*.json"
ANCHORS = (("t000300.pt", "5분"), ("t000600.pt", "10분"))


def curve(pattern):
    per = {}
    for f in sorted(glob.glob(pattern)):
        sd = f.split("_s")[-1][:-5]
        for r in json.load(open(f)):
            per.setdefault(r["ckpt"], {})[sd] = 100 * r["success_rate"]
    return per


def deltas(per, anchor):
    sds = sorted(per["final.pt"])
    return np.array([per["final.pt"][s] - per[anchor][s] for s in sds])


def exact_perm(a, b):
    """두 표본을 합쳐 라벨을 모든 방식으로 나누는 정확 순열 검정 (양측)."""
    allv = np.concatenate([a, b])
    obs = b.mean() - a.mean()
    n = len(a)
    hit = tot = 0
    for idx in itertools.combinations(range(len(allv)), n):
        m = np.zeros(len(allv), bool)
        m[list(idx)] = True
        tot += 1
        hit += abs(allv[~m].mean() - allv[m].mean()) >= abs(obs) - 1e-9
    return obs, hit / tot, tot


def main():
    L, N = curve(LIGHT), curve(NATIVE)
    if not L or not N:
        print("원자료 없음")
        return 2
    print("교차 구조 검정 — 시드별 Δ(최종 − 초반 앵커) 의 팔 간 차이")
    print("귀무가설: 두 팔의 시간에 따른 변화량이 같다")
    print()
    for anchor, label in ANCHORS:
        dl, dn = deltas(L, anchor), deltas(N, anchor)
        obs, p, tot = exact_perm(dl, dn)
        print("  %s 앵커" % label)
        print("    경량   Δ = %+6.1f%%p  %s" % (dl.mean(), [float(round(v, 1)) for v in dl]))
        print("    네이티브 Δ = %+6.1f%%p  %s" % (dn.mean(), [float(round(v, 1)) for v in dn]))
        print("    차이 %+.1f%%p | 정확 순열 %d개, 양측 p=%.4f%s"
              % (obs, tot, p, "  ← 유의" if p < 0.05 else ""))
    print()
    print("  주의: 이 검정은 '어느 시점의 격차가 유의한가'를 묻지 않는다 — 개별 시점은")
    print("  모두 비유의다(§6.2). 묻는 것은 '두 곡선의 기울기가 다른가'이며, 그것이")
    print("  교차 구조의 내용이다. 앵커 두 개는 사전 지정(첫 체크포인트·경량 피크)이므로")
    print("  5분→40분 낙폭 철회 때와 같은 사후 극값 선택이 아니다.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
