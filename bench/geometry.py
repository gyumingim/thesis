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
H = 3 * LANE_W                      # 10.5 — 로드웨이 폭(편도 3차선)이자 팔 구간 도로 반폭
CORNER_R = 10.0                     # MetaDrive StdInterSection radius=10 (pg_space 실측)
IBOX = H + CORNER_R                 # 20.5 — 교차로 영역 반크기. 교차 구간 길이 41m
                                    #        (MD 실측: 블록1 끝 x=10 → ck2 x=50, 40m 교차와 일치)
LANE_OFFSETS = (0.5 * LANE_W, 1.5 * LANE_W, 2.5 * LANE_W)   # 1.75/5.25/8.75 — 황색중앙선 기준
                                    # (MD 실측: 우측차선 스폰 시 dist L/R=8.75/1.75 → 차선센터 8.75)
EGO_OFF = LANE_OFFSETS[1]           # 하위호환(가운데 차선)
ENTRY_LEN = 10.0                    # MetaDrive FirstPGBlock 실측 (스폰 차선 길이 10)
TOTAL_ROUTE = 122.5                 # MetaDrive navigation.total_length 실측
ROAD_ARM = 110.0                    # 물리 도로 팔 길이 (최장 진출로 커버, on_road 판정용)
WP_STEP = 2.0
MANEUVERS = ("right", "straight", "left")


def _rot(theta):
    c, s = np.cos(theta), np.sin(theta)
    return np.array([[c, -s], [s, c]])


def _south_route(maneuver, lane_off):
    """남쪽 팔 진입 기준 경로. 진행방향 +y, 차선중심 x=+lane_off (차선별 커넥터)."""
    pts = []
    y0 = -(IBOX + ENTRY_LEN)
    y = np.arange(y0, -IBOX, WP_STEP)
    pts.append(np.stack([np.full_like(y, lane_off), y], -1))

    if maneuver == "straight":
        mid_len = 2 * IBOX
        y2 = np.arange(-IBOX, IBOX, WP_STEP)
        pts.append(np.stack([np.full_like(y2, lane_off), y2], -1))
        exit_dir, exit_start = np.array([0.0, 1.0]), np.array([lane_off, IBOX])
    elif maneuver == "right":
        r = IBOX - lane_off
        mid_len = r * np.pi / 2
        th = np.linspace(np.pi, np.pi / 2, max(8, int(r)))
        pts.append(np.stack([IBOX + r * np.cos(th), -IBOX + r * np.sin(th)], -1))
        exit_dir, exit_start = np.array([1.0, 0.0]), np.array([IBOX, -lane_off])
    elif maneuver == "left":
        r = IBOX + lane_off
        mid_len = r * np.pi / 2
        th = np.linspace(0.0, np.pi / 2, max(12, int(r)))
        pts.append(np.stack([-IBOX + r * np.cos(th), -IBOX + r * np.sin(th)], -1))
        exit_dir, exit_start = np.array([-1.0, 0.0]), np.array([-IBOX, lane_off])
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
    lane_offs = []
    for arm in range(4):
        R = _rot(arm * np.pi / 2)
        for m in MANEUVERS:
            for lo in LANE_OFFSETS:
                raw.append(_south_route(m, lo) @ R.T)
                lane_offs.append(lo)
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
    return wps, n_wp, cum, tang, length.astype(np.float32), np.array(lane_offs, np.float32)


def _interp_at_s(r, cum_r, k, s):
    i = int(np.searchsorted(cum_r[:k], s, side="right") - 1)
    i = max(0, min(i, k - 2))
    seg = cum_r[i + 1] - cum_r[i]
    f = 0.0 if seg <= 0 else (s - cum_r[i]) / seg
    return r[i] * (1 - f) + r[i + 1] * f


def build_sections():
    """체크포인트(섹션) 정보. bend 정규화 분모 = CURVE_RADIUS_MAX + lane_num*lane_width
    = 60 + 3*3.5 = 70.5 (node_network_navigation.py:326, 편도 3차선 기준)."""
    wps, n_wp, cum, tang, length, lane_offs = build_routes()
    n = len(wps)
    sec_end_s = np.zeros((n, 3), np.float32)
    sec_end_xy = np.zeros((n, 3, 2), np.float32)
    sec_info = np.zeros((n, 3, 3), np.float32)
    denom = spec.CURVE_RADIUS_MAX + 3 * LANE_W
    a90 = (90.0 / spec.CURVE_ANGLE_MAX + 1) / 2
    STRAIGHT = (0.0, 0.5, 0.5)
    for i in range(n):
        m = (i // 3) % 3
        lo = lane_offs[i]
        if m == 0:
            r = IBOX - lo
            mid_len, info_mid = r * np.pi / 2, (r / denom, 1.0, a90)
        elif m == 1:
            mid_len, info_mid = 2 * IBOX, STRAIGHT
        else:
            r = IBOX + lo
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
    return ((np.abs(x) <= H) & (np.abs(y) <= IBOX + ROAD_ARM)) | \
           ((np.abs(y) <= H) & (np.abs(x) <= IBOX + ROAD_ARM)) | \
           ((np.abs(x) <= IBOX) & (np.abs(y) <= IBOX))
