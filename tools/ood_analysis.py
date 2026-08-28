"""분포외(OOD) 크기와 실패의 관계 분석 — CARLA 폐루프 결과용 (2026-08-28).

가설: 지지집합 위반은 이분법이 아니라 연속 척도이며, 축이 겹치면 누적된다.
사용: python tools/ood_analysis.py C:/carla/evolve5
"""
import glob
import json
import os
import sys
import collections
import statistics as st


def load(root):
    rows = []
    for f in glob.glob(os.path.join(root, "v4_*.json")):
        tag = os.path.basename(f)[3:-5].split("_")
        if len(tag) < 5:
            continue
        try:
            data = json.load(open(f, encoding="utf-8"))
        except Exception:
            continue
        for r in data:
            if "ood_max" not in r:            # 계측 이전 배치
                continue
            rows.append(dict(r, gov=tag[3], msk=tag[4]))
    return rows


def main(root):
    rows = load(root)
    print(f"OOD 계측 포함 에피소드 {len(rows)}")
    if not rows:
        return
    ok = [r for r in rows if r["outcome"] == "성공"]
    ng = [r for r in rows if r["outcome"] != "성공"]
    for nm, g in (("성공", ok), ("실패", ng)):
        if g:
            print(f"  {nm} n={len(g)}: 평균최대|z| {st.median(r['ood_max'] for r in g):.2f} | "
                  f"피크 {st.median(r['ood_peak'] for r in g):.2f} | "
                  f"|z|>3 차원수 {st.median(r['ood_dims'] for r in g):.2f}")
    print("\n조건별 OOD 크기:")
    cond = collections.defaultdict(list)
    for r in rows:
        cond[(r["gov"], r["msk"])].append(r)
    for k in sorted(cond):
        g = cond[k]
        s = sum(1 for r in g if r["outcome"] == "성공")
        print(f"  거버너 {k[0][1:]:3s} {k[1]:6s} (n={len(g):3d}): 성공 {s/len(g):.0%} | "
              f"|z|>3 차원수 {st.median(r['ood_dims'] for r in g):.2f} | "
              f"평균최대|z| {st.median(r['ood_max'] for r in g):.2f}")
    print("\nOOD 차원수 구간별 성공률:")
    for lo, hi in ((0, 1), (1, 2), (2, 3), (3, 5), (5, 99)):
        g = [r for r in rows if lo <= r["ood_dims"] < hi]
        if g:
            s = sum(1 for r in g if r["outcome"] == "성공")
            print(f"  {lo}~{hi}개: {s}/{len(g)} = {s/len(g):.0%}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "C:/carla/evolve5")
