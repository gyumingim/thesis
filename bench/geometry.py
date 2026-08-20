"""X자 교차로 도로·경로 기하 — MetaDrive X맵 실측 정합판 (라운드 2, 2026-08-20).

설치된 metadrive 0.4.3 map="X" 에서 실측한 값으로 재구축:
  MAX_LANE_NUM=3, MAX_LANE_WIDTH=4.5 → 관측 정규화 분모 total_width=18.0
  편도 3차선(폭 3.5), 스폰 직선 10m, 경로 총길이 122.5m,
  스폰 시 체크포인트 5m/45m 전방, 50m 내 차량 노출 평균 1.3대.

좌표계: 교차로 중심 = 원점. 우측통행. ego/NPC 는 가운데 차선(중심에서 5.25m) 주행.
도로 반폭 H = 3차선 x 3.5 = 10.5m (편도 로드웨이 폭 = 10.5, 양방향 전체 = 21).

경로 12개 = 진입 팔 4 x 기동 3 (right/straight/left). 모든 경로 총길이 122.5m 로 통일.
"""
import numpy as np

import spec

LANE_W = spec.LANE_WIDTH            # 3.5
H = 3 * LANE_W                      # 10.5 — 도로(편도) 반... 정확히는 로드웨이 폭이자 도로 반폭
EGO_OFF = 1.5 * LANE_W              # 5.25 — 주행 차선(가운데) 중심의 도로중심 기준 오프셋
ENTRY_LEN = 10.0                    # MetaDrive FirstPGBlock 실측 (스폰 차선 길이 10)
TOTAL_ROUTE = 122.5                 # MetaDrive navigation.total_length 실측
ROAD_ARM = 110.0                    # 물리 도로 팔 길이 (최장 진출로 커버, on_road 판정용)
WP_STEP = 2.0
MANEUVERS = ("right", "straight", "left")


def _rot(theta):
    c, s = np.cos(theta), np.sin(theta)
    return np.array([[c, -s], [s, c]])


def _south_route(maneuver):
    """남쪽 팔 진입 기준 경로 (가운데 차선). 진행방향 +y, 차선중심 x=+5.25."""
    pts = []
    y0 = -(H + ENTRY_LEN)
    y = np.arange(y0, -H, WP_STEP)
    pts.append(np.stack([np.full_like(y, EGO_OFF), y], -1))

    if maneuver == "straight":
        mid_len = 2 * H
        y2 = np.arange(-H, H, WP_STEP)
        pts.append(np.stack([np.full_like(y2, EGO_OFF), y2], -1))
        exit_dir, exit_start = np.array([0.0, 1.0]), np.array([EGO_OFF, H])
    elif maneuver == "right":
        # (5.25,-10.5) → (10.5,-5.25), 중심 (10.5,-10.5), 반경 10.5-5.25=5.25
        r = H - EGO_OFF
        mid_len = r * np.pi / 2
        th = np.linspace(np.pi, np.pi / 2, 10)
        pts.append(np.stack([H + r * np.cos(th), -H + r * np.sin(th)], -1))
        exit_dir, exit_start = np.array([1.0, 0.0]), np.array([H, -EGO_OFF])
    elif maneuver == "left":
        # (5.25,-10.5) → (-10.5, 5.25), 중심 (-10.5,-10.5), 반경 10.5+5.25=15.75
        r = H + EGO_OFF
        mid_len = r * np.pi / 2
        th = np.linspace(0.0, np.pi / 2, 18)
        pts.append(np.stack([-H + r * np.cos(th), -H + r * np.sin(th)], -1))
        exit_dir, exit_start = np.array([-1.0, 0.0]), np.array([-H, EGO_OFF])
    else:
        raise ValueError(maneuver)

    exit_len = TOTAL_ROUTE - ENTRY_LEN - mid_len
    n_exit = int(exit_len // WP_STEP)
    t = np.arange(1, n_exit + 1)[:, None] * WP_STEP
    pts.append(exit_start[None, :] + exit_dir[None, :] * 0)          # 정확한 이음점
    pts.append(exit_start[None, :] + exit_dir[None, :] * t)
    pts.append(exit_start[None, :] + exit_dir[None, :] * exit_len)   # 정확한 종점

    out = np.concatenate(pts, 0)
    keep = np.ones(len(out), bool)
    keep[1:] = np.linalg.norm(np.diff(out, axis=0), axis=1) > 1e-4
    return out[keep]


def build_routes():
    """(n_routes, max_wp, 2), 개수, 누적호장, 접선, 총길이. index = arm*3 + maneuver."""
    raw = []
    for arm in range(4):
        R = _rot(arm * np.pi / 2)
        for m in MANEUVERS:
            raw.append(_south_route(m) @ R.T)
    n = len(raw)
    max_wp = max(len(r) for r in raw)
    wps = np.zeros((n, max_wp, 2), np.float32)
    n_wp = np.zeros(n, np.int32)
    cum = np.zeros((n, max_wp), np.float32)
    tang = np.zeros((n, max_wp, 2), np.float32)
    for i, r in enumerate(raw):
        k = len(r)
        wps[i, :k] = r
        n_wp[i] = k
        seg = np.diff(r, axis=0)
        L = np.linalg.norm(seg, axis=1)
        cum[i, 1:k] = np.cumsum(L)
        t = seg / L[:, None]
        tang[i, : k - 1] = t
        tang[i, k - 1] = t[-1]
        wps[i, k:] = r[-1]
        cum[i, k:] = cum[i, k - 1]
        tang[i, k:] = t[-1]
    length = cum[np.arange(n), n_wp - 1]
    return wps, n_wp, cum, tang, length.astype(np.float32)


def _interp_at_s(r, cum_r, k, s):
    i = int(np.searchsorted(cum_r[:k], s, side="right") - 1)
    i = max(0, min(i, k - 2))
    seg = cum_r[i + 1] - cum_r[i]
    f = 0.0 if seg <= 0 else (s - cum_r[i]) / seg
    return r[i] * (1 - f) + r[i + 1] * f


def build_sections():
    """체크포인트(섹션) 정보. bend 정규화 분모 = CURVE_RADIUS_MAX + lane_num*lane_width
    = 60 + 3*3.5 = 70.5 (node_network_navigation.py:326, 편도 3차선 기준)."""
    wps, n_wp, cum, tang, length = build_routes()
    n = len(wps)
    sec_end_s = np.zeros((n, 3), np.float32)
    sec_end_xy = np.zeros((n, 3, 2), np.float32)
    sec_info = np.zeros((n, 3, 3), np.float32)
    denom = spec.CURVE_RADIUS_MAX + 3 * LANE_W
    a90 = (90.0 / spec.CURVE_ANGLE_MAX + 1) / 2
    STRAIGHT = (0.0, 0.5, 0.5)
    for i in range(n):
        m = i % 3
        if m == 0:
            r = H - EGO_OFF
            mid_len, info_mid = r * np.pi / 2, (r / denom, 1.0, a90)
        elif m == 1:
            mid_len, info_mid = 2 * H, STRAIGHT
        else:
            r = H + EGO_OFF
            mid_len, info_mid = r * np.pi / 2, (r / denom, 0.0, a90)
        s1 = ENTRY_LEN
        s2 = s1 + mid_len
        s3 = float(length[i])
        sec_end_s[i] = (s1, s2, s3)
        sec_info[i, 0] = STRAIGHT
        sec_info[i, 1] = info_mid
        sec_info[i, 2] = STRAIGHT
        for j, sv in enumerate((s1, s2, s3)):
            sec_end_xy[i, j] = _interp_at_s(wps[i], cum[i], int(n_wp[i]), sv)
    return sec_end_s, sec_end_xy, sec_info


def on_road(x, y):
    return ((np.abs(x) <= H) & (np.abs(y) <= H + ROAD_ARM)) | \
           ((np.abs(y) <= H) & (np.abs(x) <= H + ROAD_ARM))
