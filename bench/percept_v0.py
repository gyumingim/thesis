"""인지 v0: 무학습 기하 기준선 2종 평가 (지면평면 / 크기사전).

입력: CARLA 생성 프레임의 GT 라벨 (3D 상대위치 + 크기 + 요각).
2D 검출은 '완벽 검출기' 가정 — GT 3D 박스를 이미지에 투영해 2D 박스를 만든다.
(검출 오차와 기하 오차를 분리해 기하 방식 자체의 오차 상한을 측정하는 설계.)

카메라: FOV 90°, 1280x720, 높이 1.5m → fx = 640/tan(45°) = 640, cx=640, cy=360.
- 지면평면: 바닥이 평평하면 지면점의 투영 y 로부터 d = fx·h/(y_bottom−cy)
- 크기사전: 차폭 W≈1.85m 가정, d ≈ fx·W/w_px (요각에 따른 겉보기 폭 오차가 약점)
"""
import glob
import json
import sys
import numpy as np

FX = FY = 640.0
CX, CY = 640.0, 360.0
H_CAM = 1.5
W_PRIOR = 1.85


def box_corners(v):
    """차량 로컬 3D 박스 8모서리 → 카메라 좌표 (x전방, y우측, z상방)."""
    p = v["relative_position_m"]
    l, w, h = v["size_m"]["l"], v["size_m"]["w"], v["size_m"]["h"]
    yaw = np.deg2rad(v["relative_yaw_deg"])
    cs, sn = np.cos(yaw), np.sin(yaw)
    out = []
    for dx in (-l / 2, l / 2):
        for dy in (-w / 2, w / 2):
            for dz in (-h / 2, h / 2):
                out.append((p["x"] + dx * cs - dy * sn,
                            p["y"] + dx * sn + dy * cs,
                            p["z"] + dz))
    return np.array(out)


def project(pts):
    """카메라 좌표 → 픽셀 (u 우측+, v 아래+). z상방이므로 v = CY - FY*z/x."""
    x, y, z = pts[:, 0], pts[:, 1], pts[:, 2]
    u = CX + FX * y / x
    v = CY - FY * z / x
    return u, v


def main(pattern):
    rows = []
    for f in sorted(glob.glob(pattern)):
        d = json.load(open(f))
        for veh in d["vehicles"]:
            gt_x = veh["relative_position_m"]["x"]
            gt_y = veh["relative_position_m"]["y"]
            if gt_x < 4:                 # 코앞은 화면 밖으로 잘림
                continue
            c = box_corners(veh)
            if (c[:, 0] <= 0.5).any():
                continue
            u, v = project(c)
            u0, u1, v1 = u.min(), u.max(), v.max()
            if u1 < 0 or u0 > 1280 or v1 > 720 + 100:
                continue
            # ① 지면평면: 박스 하단(v1)이 지면 접점.
            # 카메라 실높이는 라벨에서 역산 — CARLA 스폰포인트가 노면 위에 떠 있어
            # 명목 1.5m 와 다르고, 타운에 경사도 있음 (v0 1차평가에서 +56% 편향의 주범).
            # 실계에선 캘리브레이션에 해당하므로 정당한 보정.
            h_cam = (veh["size_m"]["h"] / 2) - veh["relative_position_m"]["z"]
            d_gp = FX * h_cam / max(v1 - CY, 1e-6)
            # ② 크기사전: 요각 반영 겉보기 폭 사전 = w·|cos|+l·|sin| (클래스 평균 상수)
            yaw_r = np.deg2rad(veh["relative_yaw_deg"])
            w_eff = 1.85 * abs(np.cos(yaw_r)) + 4.7 * abs(np.sin(yaw_r))
            d_sz = FX * w_eff / max(u1 - u0, 1e-6)
            # 횡방향: 박스 중심 u → y = (u-cx)·d/fx
            y_gp = (0.5 * (u0 + u1) - CX) * d_gp / FX
            # ★ 2026-09-15 추가: 위 d_gp 는 **쓸 수 없는 추정치**다(§6.4 정정). h_cam 을
            #   라벨에서 차량마다 역산하므로 지면평면 수식과 대수적으로 소거돼
            #   d_gp ≡ x_min(최근접 바닥 모서리의 종방향 거리)이 된다 — 잔차가 0 이고,
            #   gt_x(박스 **중심**)와의 차이는 오차가 아니라 «중심 대 모서리» 정의 차이다.
            #   그 산포를 노이즈 σ 로 쓰면 결정론적 기하 오프셋을 노이즈로 주입하게 된다.
            #
            #   고칠 점 둘: (1) 실계는 카메라 높이를 **한 번 캘리브레이션**하고 고정한다 —
            #   차량마다 역산하지 않는다. (2) 지면평면이 추정하는 것은 중심이 아니라
            #   **접지선까지의 거리**이므로 비교 대상도 x_min 이어야 한다.
            #   둘을 고치면 잔차가 비로소 «평면 가정 + 캘리브레이션 오차» 가 된다.
            x_min = float(c[:, 0].min())
            rows.append((gt_x, gt_y, d_gp, d_sz, y_gp, h_cam, v1, x_min))
    r = np.array(rows)
    gt_x, gt_y, d_gp, d_sz, y_gp, h_cams, v1s, x_mins = r.T
    print(f"평가 대상 차량: {len(r)}건 (거리 {gt_x.min():.0f}~{gt_x.max():.0f}m)")
    for name, est in (("지면평면", d_gp), ("크기사전", d_sz)):
        err = est - gt_x
        rel = np.abs(err) / gt_x
        print(f"  {name}: 종방향 MAE {np.abs(err).mean():5.2f}m | 상대오차 중앙값 {np.median(rel)*100:4.1f}% "
              f"| p90 {np.percentile(rel,90)*100:5.1f}%")
    lat_err = np.abs(y_gp - gt_y)
    print(f"  횡방향(지면평면 거리 사용): MAE {lat_err.mean():.2f}m")
    # 거리 구간별 (구판 — 참고용으로만 남긴다)
    print("  [구판] 거리별 지면평면 σ:", end=" ")
    for lo, hi in ((4, 15), (15, 30), (30, 50)):
        m = (gt_x >= lo) & (gt_x < hi)
        if m.sum() > 2:
            print(f"{lo}-{hi}m: {np.std(d_gp[m]-gt_x[m]):.2f}m(n={m.sum()})", end="  ")
    print()
    print("  ↑ 이 σ 는 노이즈가 아니다 — 차량마다 h_cam 을 역산해 d_gp ≡ x_min 이 되므로")
    print("    gt_x 와의 차이는 «박스 중심 대 최근접 모서리» 라는 결정론적 정의 차이다.")

    # ── 정정판: 고정 캘리브레이션 + 올바른 비교 대상 ──────────────────────────
    h_fix = float(np.median(h_cams))          # 한 번 캘리브레이션한 값에 해당
    d_fix = FX * h_fix / np.maximum(v1s - CY, 1e-6)
    res = d_fix - x_mins                      # 접지선 추정의 진짜 잔차
    print()
    print(f"  [정정판] 고정 카메라높이 {h_fix:.3f} m (역산값의 중앙값 = 1회 캘리브레이션 상당)")
    print(f"           비교 대상 = x_min(접지선), 지면평면이 실제로 추정하는 양")
    print(f"           전체 잔차: 평균 {res.mean():+.3f} m · σ {res.std():.3f} m · "
          f"MAE {np.abs(res).mean():.3f} m (n={len(res)})")
    print("           거리별 σ:", end=" ")
    for lo, hi in ((4, 15), (15, 30), (30, 50)):
        m = (gt_x >= lo) & (gt_x < hi)
        if m.sum() > 2:
            print(f"{lo}-{hi}m: 평균{res[m].mean():+.2f} σ{res[m].std():.2f}m(n={m.sum()})",
                  end="  ")
    print()
    print("           ↑ **이 σ 가 노이즈 주입에 쓸 수 있는 값**이다. 평면 가정과 고정")
    print("             캘리브레이션에서 오는 잔차이며, 정의 차이가 섞여 있지 않다.")


if __name__ == "__main__":
    main(sys.argv[1])
