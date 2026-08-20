"""X자 교차로 도로·경로 기하 (빌드 타임, NumPy).

MetaDrive map="X"(StdInterSection)의 경량 대응물. 우회전/직진/좌회전 경로를
폴리라인(웨이포인트 열)으로 미리 계산해 두고, 런타임(Numba)은 배열만 읽는다.

좌표계: 교차로 중심 = 원점. 팔은 +x(E), +y(N), -x(W), -y(S) 방향.
우측통행: 진행방향 기준 오른쪽 차선을 쓴다. 차선폭 3.5m, 편도 1차선.
도로 반폭 H = 3.5m (양방향 2차선 = 총폭 7m).

경로 12개 = 진입 팔 4 × 기동 3 (right/straight/left).
"""
import numpy as np

import spec

H = spec.LANE_WIDTH                 # 도로 반폭 = 3.5 (편도 1차선)
LANE_OFF = spec.LANE_WIDTH / 2      # 차선 중심의 횡방향 오프셋 = 1.75
ARM = spec.ARM_LENGTH               # 60
WP_STEP = 2.0                       # 웨이포인트 간격 m
MANEUVERS = ("right", "straight", "left")


def _rot(theta):
    c, s = np.cos(theta), np.sin(theta)
    return np.array([[c, -s], [s, c]])


def _south_route(maneuver):
    """남쪽 팔에서 진입하는 기준 경로. 다른 팔은 회전으로 얻는다.

    진입 차선 중심: x=+1.75, y ∈ [-(H+ARM), -H], 진행방향 +y.
    """
    pts = []
    # 진입 직선
    y = np.arange(-(H + ARM), -H, WP_STEP)
    pts.append(np.stack([np.full_like(y, LANE_OFF), y], -1))

    if maneuver == "straight":
        y2 = np.arange(-H, H + ARM, WP_STEP)
        pts.append(np.stack([np.full_like(y2, LANE_OFF), y2], -1))
        pts.append(np.array([[LANE_OFF, H + ARM]]))                 # 정확한 종점
    elif maneuver == "right":
        # (1.75, -H) → (H, -1.75), 중심 (H, -H), 반경 H-LANE_OFF=1.75, 시계방향
        r = H - LANE_OFF
        th = np.linspace(np.pi, np.pi / 2, 8)
        arc = np.stack([H + r * np.cos(th), -H + r * np.sin(th)], -1)
        pts.append(arc)
        x2 = np.arange(H, H + ARM, WP_STEP)
        pts.append(np.stack([x2, np.full_like(x2, -LANE_OFF)], -1))
        pts.append(np.array([[H + ARM, -LANE_OFF]]))
    elif maneuver == "left":
        # (1.75, -H) → (-H, 1.75), 중심 (-H, -H), 반경 H+LANE_OFF=5.25, 반시계
        r = H + LANE_OFF
        th = np.linspace(0.0, np.pi / 2, 14)
        arc = np.stack([-H + r * np.cos(th), -H + r * np.sin(th)], -1)
        pts.append(arc)
        x2 = np.arange(-H, -(H + ARM), -WP_STEP)
        pts.append(np.stack([x2, np.full_like(x2, LANE_OFF)], -1))
        pts.append(np.array([[-(H + ARM), LANE_OFF]]))
    else:
        raise ValueError(maneuver)
    out = np.concatenate(pts, 0)
    # 이음매의 중복/근접점 제거 (0 길이 세그먼트는 접선 계산을 깨뜨린다)
    keep = np.ones(len(out), bool)
    keep[1:] = np.linalg.norm(np.diff(out, axis=0), axis=1) > 1e-4
    return out[keep]


def build_routes():
    """(n_routes, max_wp, 2) 웨이포인트, (n_routes,) 실제 개수·총길이, 누적길이·접선.

    route index = arm*3 + maneuver  (arm: 0=S,1=E,2=N,3=W / maneuver: 0=R,1=S,2=L)
    """
    raw = []
    for arm in range(4):
        R = _rot(arm * np.pi / 2)   # S 기준 경로를 90도씩 회전
        for m in MANEUVERS:
            raw.append(_south_route(m) @ R.T)
    n = len(raw)
    max_wp = max(len(r) for r in raw)
    wps = np.zeros((n, max_wp, 2), np.float32)
    n_wp = np.zeros(n, np.int32)
    cum = np.zeros((n, max_wp), np.float32)     # 시작점부터의 호장
    tang = np.zeros((n, max_wp, 2), np.float32)  # 단위 접선
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
        # 패딩 구간은 마지막 값 유지 (Numba 분기 제거용)
        wps[i, k:] = r[-1]
        cum[i, k:] = cum[i, k - 1]
        tang[i, k:] = t[-1]
    length = cum[np.arange(n), n_wp - 1]
    return wps, n_wp, cum, tang, length.astype(np.float32)


def _interp_at_s(r, cum_r, k, s):
    """호장 s 에서의 폴리라인 좌표 (빌드 타임 전용)."""
    i = int(np.searchsorted(cum_r[:k], s, side="right") - 1)
    i = max(0, min(i, k - 2))
    seg = cum_r[i + 1] - cum_r[i]
    f = 0.0 if seg <= 0 else (s - cum_r[i]) / seg
    return r[i] * (1 - f) + r[i + 1] * f


def build_sections():
    """경로별 체크포인트(섹션) 정보 — MetaDrive 내비 관측용.

    섹션 = [진입 직선, 교차로 내부(호 또는 직선), 진출 직선].
    체크포인트 = 각 섹션의 끝점 (MetaDrive: ref_lane.position(ref_lane.length, 0) = 차선 끝).
    sec_info = (bend01, dir01, angle01):
      직선   → (0, 0.5, 0.5)
      우회전 → (1.75/63.5, 1.0, (90/135+1)/2)   좌회전 → (5.25/63.5, 0.0, 동일)
      정규화 근거: node_network_navigation.py:326~344, CURVE radius max=60, angle max=135,
                  분모 = 60 + lane_num*lane_width = 63.5
    """
    wps, n_wp, cum, tang, length = build_routes()
    n = len(wps)
    sec_end_s = np.zeros((n, 3), np.float32)
    sec_end_xy = np.zeros((n, 3, 2), np.float32)
    sec_info = np.zeros((n, 3, 3), np.float32)
    denom = spec.CURVE_RADIUS_MAX + 1 * spec.LANE_WIDTH
    a90 = (90.0 / spec.CURVE_ANGLE_MAX + 1) / 2
    STRAIGHT = (0.0, 0.5, 0.5)
    for i in range(n):
        m = i % 3      # 0=right, 1=straight, 2=left
        if m == 0:
            mid_len, info_mid = (H - LANE_OFF) * np.pi / 2, ((H - LANE_OFF) / denom, 1.0, a90)
        elif m == 1:
            mid_len, info_mid = 2 * H, STRAIGHT
        else:
            mid_len, info_mid = (H + LANE_OFF) * np.pi / 2, ((H + LANE_OFF) / denom, 0.0, a90)
        s1 = ARM                      # 진입 직선 길이 = 60 (팔끝→도로경계)
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
    """도로 위 여부 (십자 영역). out_of_road = not on_road. 검증용 NumPy 버전."""
    return ((np.abs(x) <= H) & (np.abs(y) <= H + ARM)) | \
           ((np.abs(y) <= H) & (np.abs(x) <= H + ARM))
