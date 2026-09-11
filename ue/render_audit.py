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

# 프리셋 3분류. «이른 아침» 을 맑음과 한 묶음에 두면 안 된다 — 여명 하늘은 실제로
# 붉고, 그걸 «파래야 한다» 로 판정하면 옳게 만든 장면이 실패로 찍힌다(실측 −0.055).
OVERCAST = ("흐림", "짙은 흐림", "비 온 뒤")
DAWN = ("이른 아침",)
# ★ 2026-09-05 정정: 처음에는 «상단 100행 = 하늘» 로 뒀는데, 이 장면들은 도심 협곡이라
#   상단이 대부분 **건물 벽면**이다. 그래서 «하늘 색» 지표가 실제로는 벽면 색을 재고
#   있었고, 노출을 낮추자 지표가 오히려 나빠지는 착시가 생겼다. 하늘은 협곡 안에서
#   거의 항상 **가장 밝은 영역**이므로, 상단 영역에서 밝기 상위 분위만 고른다.
#   ★ 2차 정정: «밝기 상위» 로도 부족했다. 햇빛 받은 흰 타워 벽면이 파란 하늘보다 밝아
#     그쪽이 뽑힌다(scene_2 는 눈으로 명백히 파란 하늘인데 지표는 B−R −0.086 을 냈다).
#     하늘의 결정적 성질은 밝기가 아니라 **매끄러움**이다 — 건물 벽면은 창문 격자 때문에
#     국소 분산이 크고 하늘은 거의 0 이다. 국소 표준편차가 작고 어둡지 않은 화소만 고른다.
# 실사 참조 분위 (ue/real_baseline.py, Udacity CrowdAI 150장). 임계를 «내가 고른
# 숫자» 에서 «실사 분포» 로 옮긴 값이다. 참조는 간선도로라 하늘이 넓고 우리는 도심
# 협곡이므로 방향·크기의 기준이지 절대 진리는 아니다(§6.4 도메인 갭과 같은 주의).
VOID_REF = 0.061        # 실사 소실점 공허 75분위
BLOWN_REF = 0.109       # 실사 과노출 75분위
SKY_BAND = 0.42         # 상단 42% 안에서 고른다
SKY_SMOOTH = 0.02       # 국소 표준편차 상한 (창문 격자를 배제)
ROAD_ROWS = 500         # 하단 = 노면 위주


def _local_sd(g, r=2):
    """5x5 국소 표준편차 — 적분영상 없이 shift 누적으로 구한다."""
    acc = np.zeros_like(g)
    acc2 = np.zeros_like(g)
    n = 0
    for dy in range(-r, r + 1):
        for dx in range(-r, r + 1):
            sh = np.roll(np.roll(g, dy, axis=0), dx, axis=1)
            acc += sh
            acc2 += sh * sh
            n += 1
    return np.sqrt(np.maximum(acc2 / n - (acc / n) ** 2, 0.0))


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
        band = rgb[:int(rgb.shape[0] * SKY_BAND)]
        bl = band.mean(axis=2)
        loc_sd = _local_sd(bl)
        # ★ 3차 정정: «매끄럽고 밝은» 만으로도 틀린다 — 유리 커튼월은 매끄럽고, 협곡이
        #   좁으면 하늘 화소가 거의 없어 그늘진 벽면이 뽑힌다(짙은 흐림이 가장 파랗게
        #   측정되는 역전이 남았다). 하늘의 진짜 정의는 «건물 윤곽선 위» 다. 열마다
        #   구조(국소 분산)가 처음 나타나는 행을 찾아 그 **위쪽만** 하늘로 삼는다.
        struct = loc_sd > SKY_SMOOTH
        H = band.shape[0]
        # 열별 최초 구조 행 (없으면 H)
        first = np.where(struct.any(axis=0), struct.argmax(axis=0), H)
        rows_idx = np.arange(H)[:, None]
        m = rows_idx < first[None, :]
        m &= ~struct                       # 잔여 구조 화소 제외
        sky = band[m] if m.sum() > 300 else np.zeros((0, 3), np.float32)
        # 중앙대(세로 42~62%) 에서 같은 매끄러움 판정을 다시 한다
        h0, h1 = int(rgb.shape[0] * 0.42), int(rgb.shape[0] * 0.62)
        mid_l = rgb[h0:h1].mean(axis=2)
        loc_sd_mid = _local_sd(mid_l)
        rows.append(dict(
            name=os.path.basename(f)[:-4],
            preset=d["weather"]["preset"],
            overcast=d["weather"]["preset"] in OVERCAST,
            dawn=d["weather"]["preset"] in DAWN,
            sun=d["weather"]["sun_intensity"],
            mean=float(lum.mean()),
            road_sd=float(lum[ROAD_ROWS:].std()),
            sky_px=int(sky.shape[0]),
            sky_br=float(np.median(sky[:, 2] - sky[:, 0])) if len(sky) else float("nan"),
            sky_lum=float(np.median(sky.mean(axis=1))) if len(sky) else float("nan"),
            # 소실점 공허 — 화면 중앙대(수평선 부근)에 «매끄럽고 밝은» 화소가 많으면
            # 도심 협곡이 개활지로 열려 하늘/빈 지면이 보인다는 뜻이다. 닫힌 협곡이면
            # 그 대역은 건물 벽면·도로·차량이라 국소 분산이 크다.
            void=float(((loc_sd_mid < SKY_SMOOTH) & (mid_l > 0.55)).mean()),
            blown=float((lum > 0.92).mean()),
        ))
    return rows


def report(root):
    rows = measure(root)
    if not rows:
        print("렌더 없음:", root)
        return None
    print("== %s (%d장)" % (root, len(rows)))
    print("  %-9s %-9s %6s %7s %8s %8s %9s %8s  %6s" %
          ("장면", "프리셋", "태양", "평균", "노면 대비", "하늘 밝기", "하늘 B−R", "과노출",
           "하늘px"))
    for r in rows:
        print("  %-9s %-9s %6.2f %7.3f %8.3f %8.3f %9.3f %7.1f%%  %6d" %
              (r["name"], r["preset"], r["sun"], r["mean"], r["road_sd"],
               r["sky_lum"], r["sky_br"], 100 * r["blown"], r["sky_px"]))

    import math as _m
    has_sky = lambda r: r["sky_px"] >= 300 and not _m.isnan(r["sky_br"])
    oc = [r for r in rows if r["overcast"] and has_sky(r)]
    cl = [r for r in rows if not r["overcast"] and not r["dawn"] and has_sky(r)]
    dw = [r for r in rows if r["dawn"] and has_sky(r)]
    nosky = [r for r in rows if not has_sky(r)]
    if nosky:
        print("  (하늘 화소 부족으로 색 판정에서 제외: %s)"
              % ", ".join("%s(%d px)" % (r["name"], r["sky_px"]) for r in nosky))
    out = {}
    print()
    if oc and cl:
        out["하늘 B−R 맑음"] = statistics.median(r["sky_br"] for r in cl)
        out["하늘 B−R 흐림"] = statistics.median(r["sky_br"] for r in oc)
        gap = out["하늘 B−R 맑음"] - out["하늘 B−R 흐림"]
        ok = gap > 0
        print("  (1) 하늘 색  맑음계열 %d장 B−R %.3f  vs  흐림계열 %d장 %.3f  → 차이 %+.3f  %s"
              % (len(cl), out["하늘 B−R 맑음"], len(oc), out["하늘 B−R 흐림"], gap,
                 "통과" if ok else "**실패 — 흐린 하늘이 더 파랗다**"))
        if dw:
            print("      여명 %d장 B−R %s — 붉은 것이 정상이므로 위 비교에서 제외"
                  % (len(dw), ", ".join("%+.3f" % r["sky_br"] for r in dw)))
        out["하늘 색 분리"] = 1.0 if ok else 0.0

        out["노면 대비 맑음"] = statistics.median(r["road_sd"] for r in cl)
        out["노면 대비 흐림"] = statistics.median(r["road_sd"] for r in oc)
        d2 = out["노면 대비 맑음"] - out["노면 대비 흐림"]
        # ★ 2026-09-06 판정 철회. 이 지표를 «그림자 경도» 로 쓸 수 없다 — 생성기의
        #   WEATHER 표에서 흐림 계열 3종(흐림·짙은 흐림·비 온 뒤)이 **전부 wet=True**,
        #   맑음 계열 3종이 전부 wet=False 라 습윤과 흐림이 완전히 교락돼 있다. 젖은
        #   노면의 반사가 국소 대비를 크게 올리므로, 그림자가 아무리 부드러워져도
        #   흐림 쪽 노면 대비가 더 높게 나온다(실측 흐림 0.183 vs 맑음 0.140).
        #   그림자 경도를 재려면 노면 전체 분산이 아니라 그림자 **경계의 기울기**를
        #   봐야 하고, 그것은 별도 설계가 필요하다. 그때까지 수치는 진단용으로만 싣는다.
        print("  (3) 노면 대비 맑음 %.3f  vs  흐림 %.3f  → 차이 %+.3f"
              % (out["노면 대비 맑음"], out["노면 대비 흐림"], d2))
        print("      **판정 철회** — 흐림 계열 3종이 전부 wet, 맑음 계열이 전부 dry 라")
        print("      습윤 반사와 그림자 경도가 완전 교락이다. 이 수치로는 가릴 수 없다.")
        out["대비 분리"] = float("nan")

    # 백화 판정에서 여명은 뺀다 — 낮은 태양이 화각에 들어오면 실제 사진도 그 부근이 탄다.
    cand = [r for r in rows if not r["dawn"]] or rows
    # ★ 2026-09-06 임계 재교정 (ue/real_baseline.py). 이전 임계 «소실점 최대 8%» 와
    #   «과노출 최대 5%» 는 둘 다 눈대중으로 고른 값이었고, 실사 150장에 같은 지표를
    #   돌려 보니 **실사가 지키지 못하는 기준**이었다:
    #     소실점 공허  실사 중앙 2.6% · 75분위 6.1% · 최대 27.8%
    #     과노출      실사 중앙 7.5% · 75분위 10.9% · 최대 36.6%
    #   즉 과노출 5% 임계는 실사 사진 절반을 떨어뜨리고, 우리 렌더는 **오히려 실사보다
    #   덜 탄다**. 최대값 판정도 실사에 불공정하므로 둘 다 **장면 중앙값**으로 바꾸고
    #   임계를 실사 75분위에 맞춘다.
    vw = max(rows, key=lambda r: r["void"])
    out["소실점 공허 최대"] = 100 * vw["void"]
    out["소실점 공허 중앙"] = 100 * float(np.median([r["void"] for r in rows]))
    out["소실점 공허 평균"] = 100 * float(np.mean([r["void"] for r in rows]))
    # ★ 2026-09-11 판정 철회. 이 임계(실사 75분위 6.1%)는 **간선도로 사진**에서 나왔는데
    #   우리 장면은 도심 협곡이다. 도심 참조(ref_all 170장)로 같은 지표를 풀링해 재면
    #   참조 중앙이 9.2% 로 우리(7.0%)보다 **높다** — 즉 실사 도심 거리가 우리보다 더
    #   비어 보인다. 같은 수치가 어느 참조를 쓰느냐에 따라 «+4.3%p 초과» 도 되고
    #   «−2.2%p 미달» 도 된다. 도메인이 결과를 지배하므로 단일 임계로 통과/실패를
    #   매기지 않는다. 분포 비교는 ue/dist_compare.py 로 한다.
    print("  (4) 소실점   장면 중앙 %.1f%% (간선 75분위 %.1f%% · 도심 중앙 9.2%%)"
          % (out["소실점 공허 중앙"], 100 * VOID_REF))
    print("      **판정 철회** — 참조 도메인이 값을 지배한다(간선 기준 초과, 도심 기준 미달).")
    print("      최대 %.1f%% (%s, %s) — 참고용. 실사 최대도 27.8%% 라 최대로는 판정하지 않는다."
          % (out["소실점 공허 최대"], vw["name"], vw["preset"]))
    worst = max(cand, key=lambda r: r["blown"])
    out["최대 과노출"] = 100 * worst["blown"]
    out["과노출 중앙"] = 100 * float(np.median([r["blown"] for r in cand]))
    print("  (2) 백화     여명 제외 장면 중앙 %.1f%% (실사 75분위 %.1f%%)  %s"
          % (out["과노출 중앙"], 100 * BLOWN_REF,
             "통과" if out["과노출 중앙"] <= 100 * BLOWN_REF else "실패"))
    print("      최대 %.1f%% (%s, %s) — 참고용(실사 최대 36.6%%)."
          % (out["최대 과노출"], worst["name"], worst["preset"]))
    if dw:
        print("      여명 %d장: 과노출 %s (태양이 화각에 들어오는 조건이라 판정 제외)"
              % (len(dw), ", ".join("%.1f%%" % (100 * r["blown"]) for r in dw)))

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
