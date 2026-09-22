"""인지 오차의 **나머지 차원** — 횡방향과 요각. §8 (9) 선택지 (b) 의 선행 조건.

§6.4 는 지면평면 접지선 추정의 **종방향** 잔차만 쟀다(σ 1.10/2.82/5.10 m). §8 (9) 의
사전 감도 측정에서 종방향만 주입하는 설계가 탈락했고(섭동이 탐색 잡음 이하), 남은
유일한 길이 「§6.4 가 재지 않은 차원을 함께 주입」이다. 그러려면 그 차원들의 오차를
**같은 방식으로 재야** 한다 — 주입할 값이 없으면 실험도 없다.

같은 원자료를 쓴다: CARLA 500프레임(`C:/carla/out/frame_*.json`), 완벽 검출기 가정
(GT 3D 박스를 투영해 2D 박스를 만든다) — 검출 오차와 기하 오차를 분리하려는 §6.4 의
설계를 그대로 따른다. 필터도 같다(x<4 제외, 화면 밖 제외).

재는 것 둘:
  **① 횡방향** — 기하적으로 결정된다. 접지선으로 거리 d 를 얻고 박스 중앙 열 u_c 에서
     ŷ = d·(u_c − CX)/FX. 거리 오차가 그대로 횡방향으로 번지므로, 이 잔차는 §6.4 의
     종방향 잔차와 **독립이 아니다**. 상관을 함께 보고한다.
  **② 요각** — 겉보기 폭에서 역산한다. 겉보기 폭 w_app = d·(u1−u0)/FX 이고 클래스 평균
     치수로 w_app = 1.85|cos ψ| + 4.7|sin ψ| 를 ψ 에 대해 푼다(§6.4 의 «크기사전» 이
     쓰던 식의 역). ★ 이 추정은 **부호와 전후를 구분하지 못한다**(|cos|·|sin|). 따라서
     오차는 0~90° 로 접은 값으로만 의미가 있고, 그대로 주입에 쓸 수는 없다.

**속도는 재지 못한다** — 이 라벨에 속도 필드가 없고 프레임이 연속열이라는 보장도 없다.
속도 오차를 주입하려면 CARLA 재수집이 필요하다.

실행: .venv/Scripts/python.exe bench/percept_lateral.py "C:/carla/out/frame_*.json"
"""
import glob
import json
import sys

import numpy as np

sys.path.insert(0, __file__.rsplit("percept_lateral.py", 1)[0])
from percept_v0 import FX, CX, CY, box_corners, project   # noqa: E402

BANDS = ((4.0, 15.0), (15.0, 30.0), (30.0, 50.0))
W_M, L_M = 1.85, 4.7          # 클래스 평균 (§6.4 «크기사전» 과 동일 상수)


def yaw_from_width(w_app):
    """겉보기 폭 → |ψ| (0~90°). w = W|cosψ| + L|sinψ| 를 격자로 역산한다."""
    grid = np.linspace(0.0, np.pi / 2, 901)
    pred = W_M * np.cos(grid) + L_M * np.sin(grid)
    return np.rad2deg(grid[np.argmin(np.abs(pred[None, :] - w_app[:, None]), axis=1)])


def main(pattern):
    files = sorted(glob.glob(pattern))
    if not files:
        print("프레임이 없다: %s" % pattern)
        return 2
    d_gt, lat_gt, lat_est, yaw_gt, yaw_est, d_err = [], [], [], [], [], []
    h_cams = []
    rows = []
    clipped = [0]
    for f in files:
        d = json.load(open(f, encoding="utf-8"))
        for veh in d["vehicles"]:
            p = veh["relative_position_m"]
            if p["x"] < 4:
                continue
            c = box_corners(veh)
            if (c[:, 0] <= 0.5).any():
                continue
            u, v = project(c)
            u0, u1, v1 = u.min(), u.max(), v.max()
            if u1 < 0 or u0 > 1280 or v1 > 720 + 100:
                continue
            # ★ 화면 가장자리에 **잘린** 박스는 겉보기 폭과 중앙 열이 둘 다 왜곡된다.
            #   §6.4 의 종방향(접지선 v1)은 세로만 쓰므로 영향이 적지만, 횡방향과
            #   요각은 가로를 쓰므로 치명적이다. 첫 판에서 근거리 요각 편향이 +38.9°
            #   로 나온 것이 이 때문이었다. 가로로 완전히 들어온 것만 쓴다.
            if u0 < 0 or u1 > 1280:
                clipped[0] += 1
                continue
            h_cams.append((veh["size_m"]["h"] / 2) - p["z"])
            rows.append((p, u0, u1, v1, veh))
    # §6.4 정정판과 같은 **고정 캘리브레이션**: 카메라 높이는 1회 중앙값으로 고정한다.
    # 차량마다 라벨에서 역산하면 거리 오차가 대수적으로 상쇄돼 잔차가 0 이 된다.
    h_fix = float(np.median(h_cams))
    for p, u0, u1, v1, veh in rows:
        d_hat = FX * h_fix / max(v1 - CY, 1e-6)
        u_c = 0.5 * (u0 + u1)
        d_gt.append(p["x"])
        d_err.append(d_hat - p["x"])
        lat_gt.append(p["y"])
        lat_est.append(d_hat * (u_c - CX) / FX)
        yaw_gt.append(veh["relative_yaw_deg"])
        yaw_est.append(float(yaw_from_width(np.array([d_hat * (u1 - u0) / FX]))[0]))
    d_gt = np.array(d_gt); d_err = np.array(d_err)
    lat_gt = np.array(lat_gt); lat_est = np.array(lat_est)
    yaw_gt = np.array(yaw_gt); yaw_est = np.array(yaw_est)
    lat_res = lat_est - lat_gt
    # 요각은 |ψ| 로만 비교 가능하다(추정이 부호·전후를 못 가린다)
    yaw_fold = np.abs(((np.abs(yaw_gt) + 90) % 180) - 90)
    yaw_res = yaw_est - yaw_fold

    print("카메라 높이 고정 캘리브레이션 h=%.3f m · 표본 %d건 (프레임 %d)"
          % (h_fix, len(d_gt), len(files)))
    print("  가장자리에 잘려 제외 %d건 — 가로 폭을 쓰는 추정에는 쓸 수 없다."
          % clipped[0])
    print("")
    print("① 횡방향 잔차 (추정 − GT, m)")
    print("  %-12s %8s %10s %10s %14s" % ("거리 구간", "n", "평균", "σ", "|종방향|과 상관"))
    for lo, hi in BANDS:
        m = (d_gt >= lo) & (d_gt < hi)
        if m.sum() < 20:
            continue
        r = np.corrcoef(np.abs(d_err[m]), np.abs(lat_res[m]))[0, 1]
        print("  %-12s %8d %9.2f %10.2f %14.2f"
              % ("%g~%g m" % (lo, hi), m.sum(), lat_res[m].mean(), lat_res[m].std(), r))
    print("  → 횡방향 오차는 거리 오차에서 파생된다(ŷ = d̂·(u−CX)/FX). 상관이 높으면")
    print("    두 차원을 **독립으로 주입하면 안 된다** — 같은 거리 오차를 두 번 세는 셈이다.")
    print("")
    print("② 요각 잔차 (겉보기 폭 역산, |ψ| 기준, 도)")
    print("  %-12s %8s %10s %10s" % ("거리 구간", "n", "평균", "σ"))
    for lo, hi in BANDS:
        m = (d_gt >= lo) & (d_gt < hi)
        if m.sum() < 20:
            continue
        print("  %-12s %8d %9.1f %10.1f"
              % ("%g~%g m" % (lo, hi), m.sum(), yaw_res[m].mean(), yaw_res[m].std()))
    print("  ★ 이 추정기는 부호와 전후를 구분하지 못한다(|cos|·|sin|). 위 수치는 «겉보기")
    print("    폭만으로 요각을 얼마나 아는가» 의 상한이며, **그대로 주입할 수는 없다.**")
    print("")
    print("③ 속도 — 잴 수 없다. 이 라벨에 속도 필드가 없고 프레임이 연속열이라는 보장도")
    print("   없다. 주입하려면 CARLA 재수집이 필요하다(§8 (9)).")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else "C:/carla/out/frame_*.json"))
