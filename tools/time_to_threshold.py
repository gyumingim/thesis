"""벽시계 도달 시간 비교 — 같은 성능에 누가 먼저 도달하는가.

최종 성능만 비교하면 처리량 우위가 통째로 사라진다. 처리량이 사는 곳은 **같은 수준에
도달하는 데 걸린 시간**이다. 이 스크립트는 두 학습 곡선(체크포인트별 전이 성공률)에서
목표 수준 τ 를 처음 넘긴 시각을 시드마다 구하고, 그 비를 낸다.

주의 두 가지.
 (1) 체크포인트는 300초 격자라 도달 시각의 해상도가 ±150초다. 선형 보간은 하지 않는다 —
     30ep 평가의 표본오차(±9%p 수준)가 격자 오차보다 크기 때문이다.
 (2) 한 번 넘고 다시 내려오는 곡선이 흔하므로 "최초 도달"과 "마지막 도달"을 함께 낸다.
     둘이 크게 다르면 그 수준은 안정적으로 유지되는 것이 아니다.

실행:
  python tools/time_to_threshold.py --a "bench_results/clean/eval_md__clean_s*.json" \
      --b "bench_results/native_desktop/eval_md__nd_s*.json" --level 58.9
"""
import argparse
import glob
import json

import numpy as np


def curves(pattern):
    out = []
    for f in sorted(glob.glob(pattern)):
        rows = sorted(json.load(open(f)), key=lambda r: r["elapsed_s"])
        pts = [(r["elapsed_s"], 100 * r["success_rate"]) for r in rows if r["ckpt"] != "final.pt"]
        if pts:
            out.append((f, pts))
    return out


def reach(pts, level):
    hit = [t for t, v in pts if v >= level]
    return (min(hit), max(hit)) if hit else (None, None)


def side(name, pattern, level):
    cs = curves(pattern)
    if not cs:
        print("  %s: 자료 없음 (%s)" % (name, pattern))
        return []
    firsts = []
    print("  %s" % name)
    for f, pts in cs:
        a, b = reach(pts, level)
        firsts.append(a)
        print("    %-38s 최초 %s  마지막 %s  최고 %.1f%%" %
              (f.split("eval_md__")[-1],
               "%5.0fs" % a if a else "미도달",
               "%5.0fs" % b if b else "  —  ",
               max(v for _, v in pts)))
    return firsts


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--a", required=True, help="빠른 쪽 glob (경량 시뮬)")
    ap.add_argument("--b", required=True, help="느린 쪽 glob (네이티브)")
    ap.add_argument("--level", type=float, required=True, help="목표 성공률 %")
    args = ap.parse_args()

    print("목표 수준 %.1f%% 도달 시각" % args.level)
    fa = side("A (경량)", args.a, args.level)
    fb = side("B (네이티브)", args.b, args.level)
    ok_a = [t for t in fa if t]
    ok_b = [t for t in fb if t]
    print()
    print("  A 도달 %d/%d 시드, 중앙값 %s" %
          (len(ok_a), len(fa), "%.0fs" % np.median(ok_a) if ok_a else "—"))
    print("  B 도달 %d/%d 시드, 중앙값 %s" %
          (len(ok_b), len(fb), "%.0fs" % np.median(ok_b) if ok_b else "—"))
    if ok_a and ok_b:
        print("  벽시계 단축 배수 (B/A 중앙값): %.1f×" % (np.median(ok_b) / np.median(ok_a)))
    elif ok_a and not ok_b:
        print("  네이티브는 예산 안에 이 수준에 도달하지 못했다 — 배수를 하한으로만 말할 수 있다.")


if __name__ == "__main__":
    main()
