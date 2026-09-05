"""렌더된 장면의 **외형 통계** 감사 — 기상 프리셋이 실제로 그림을 바꾸는지 검정한다.

`ue/label_audit.py` 가 라벨 기하를 본다면 이 도구는 픽셀을 본다. 계기는 2026-09-05 의
발견이다: 프리셋 이름은 여섯 가지인데 **그림은 사실상 한 가지**였다.

  * 태양 강도가 1.16~8.02 로 7배 차이인데 화면 평균 밝기는 0.28~0.46 에 머물렀다
    (r=+0.27, n=10). 자동노출이 조도 축을 상쇄한다.
  * 더 나쁜 것은 하늘 색이 **뒤집혀** 있었다는 점이다 — 흐림 계열의 하늘 B−R 중앙값이
    0.137 로 맑음 계열 0.043 보다 더 파랬다. 맑은 장면일수록 하늘이 백화돼 채널이 함께
    포화하면서 B−R 이 0 으로 눌리기 때문이다.

즉 «기상 다양성» 이 이름뿐이었고 그나마 있는 축은 실제와 반대였다. 데이터셋 다양성을
주장하려면 이 지표가 통과해야 한다.

판정:
  (1) 하늘 색 분리 — 맑음 계열의 하늘 B−R 중앙값이 흐림 계열보다 **커야** 한다.
  (2) 백화 통제 — 어떤 프리셋도 과노출 화소가 5% 를 넘지 않아야 한다.
  (3) 대비 축 — 맑음 계열의 노면 대비(그림자 경계)가 흐림 계열보다 커야 한다.

실행: python ue/render_audit.py C:/ue/verify10 [비교할_이전_디렉터리]
"""
import glob
import io
import json
import os
import statistics
import sys

import numpy as np
from PIL import Image

OVERCAST = ("흐림", "짙은 흐림", "비 온 뒤")
SKY_ROWS = 100          # 상단 띠 = 하늘 위주. 카메라 pitch 가 ±3° 이내라 안전하다.
ROAD_ROWS = 500         # 하단 = 노면 위주


def measure(root):
    rows = []
    fs = sorted(glob.glob(os.path.join(root, "scene_*.png")),
                key=lambda x: int(os.path.basename(x)[6:-4]))
    for f in fs:
        j = f[:-4] + ".json"
        if not os.path.exists(j):
            continue
        d = json.load(io.open(j, encoding="utf-8"))
        rgb = np.asarray(Image.open(f).convert("RGB"), dtype=np.float32) / 255.0
        lum = rgb.mean(axis=2)
        sky = rgb[:SKY_ROWS].reshape(-1, 3)
        rows.append(dict(
            name=os.path.basename(f)[:-4],
            preset=d["weather"]["preset"],
            overcast=d["weather"]["preset"] in OVERCAST,
            sun=d["weather"]["sun_intensity"],
            mean=float(lum.mean()),
            road_sd=float(lum[ROAD_ROWS:].std()),
            sky_br=float(np.median(sky[:, 2] - sky[:, 0])),
            blown=float((lum > 0.92).mean()),
        ))
    return rows


def report(root):
    rows = measure(root)
    if not rows:
        print("렌더 없음:", root)
        return None
    print("== %s (%d장)" % (root, len(rows)))
    print("  %-9s %-9s %6s %7s %8s %9s %8s" %
          ("장면", "프리셋", "태양", "평균", "노면 대비", "하늘 B−R", "과노출"))
    for r in rows:
        print("  %-9s %-9s %6.2f %7.3f %8.3f %9.3f %7.1f%%" %
              (r["name"], r["preset"], r["sun"], r["mean"], r["road_sd"],
               r["sky_br"], 100 * r["blown"]))

    oc = [r for r in rows if r["overcast"]]
    cl = [r for r in rows if not r["overcast"]]
    out = {}
    print()
    if oc and cl:
        out["하늘 B−R 맑음"] = statistics.median(r["sky_br"] for r in cl)
        out["하늘 B−R 흐림"] = statistics.median(r["sky_br"] for r in oc)
        gap = out["하늘 B−R 맑음"] - out["하늘 B−R 흐림"]
        ok = gap > 0
        print("  (1) 하늘 색  맑음 %d장 B−R %.3f  vs  흐림 %d장 %.3f  → 차이 %+.3f  %s"
              % (len(cl), out["하늘 B−R 맑음"], len(oc), out["하늘 B−R 흐림"], gap,
                 "통과" if ok else "**실패 — 흐린 하늘이 더 파랗다**"))
        out["하늘 색 분리"] = 1.0 if ok else 0.0

        out["노면 대비 맑음"] = statistics.median(r["road_sd"] for r in cl)
        out["노면 대비 흐림"] = statistics.median(r["road_sd"] for r in oc)
        d2 = out["노면 대비 맑음"] - out["노면 대비 흐림"]
        print("  (3) 노면 대비 맑음 %.3f  vs  흐림 %.3f  → 차이 %+.3f  %s"
              % (out["노면 대비 맑음"], out["노면 대비 흐림"], d2,
                 "통과" if d2 > 0 else "실패 — 흐린 날 그림자가 더 세다"))
        out["대비 분리"] = 1.0 if d2 > 0 else 0.0

    worst = max(rows, key=lambda r: r["blown"])
    out["최대 과노출"] = 100 * worst["blown"]
    print("  (2) 백화     최대 과노출 %.1f%% (%s, %s)  %s"
          % (out["최대 과노출"], worst["name"], worst["preset"],
             "통과" if worst["blown"] <= 0.05 else "실패 — 5% 초과"))

    sun = np.array([r["sun"] for r in rows])
    mean = np.array([r["mean"] for r in rows])
    r_bm = float(np.corrcoef(sun, mean)[0, 1]) if len(rows) > 2 else float("nan")
    out["태양-밝기 r"] = r_bm
    print("  참고    태양 강도 vs 화면 밝기 r=%+.3f — 자동노출이 있으므로 0 근처가 정상이다"
          % r_bm)
    print("          (실제 카메라도 자동노출을 한다. 흐림의 단서는 밝기가 아니라 하늘 색과")
    print("           그림자 경도다 — 그래서 판정을 (1)·(3) 으로 둔다.)")
    return out


def main():
    roots = sys.argv[1:] or ["C:/ue/verify10"]
    outs = [(r, report(r)) for r in roots]
    outs = [(r, o) for r, o in outs if o]
    if len(outs) > 1:
        print()
        print("== 대조")
        keys = list(outs[0][1])
        print("  %-16s %s" % ("지표", " ".join("%16s" % os.path.basename(r) for r, _ in outs)))
        for k in keys:
            print("  %-16s %s" % (k, " ".join("%16.3f" % o.get(k, float("nan"))
                                              for _, o in outs)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
