"""경량 교차로 RL 환경 — Numba 본체.

MetaDrive(0.4.3, map="X", GT 관측)와 과제·행동·관측 51차원·보상·종료를 정합.
모든 정규화 공식의 출처는 설치된 metadrive 0.4.3 소스이며 spec.py / PAPER.md 3.4절에 기록.

의도적 근사 (논문 명시 대상):
- 차량 동역학: Bullet 강체 → 자전거 모델 (WHEELBASE/MAX_ACCEL 근사)
- 충돌: 박스 → 원 (반경 COLLISION_RADIUS)
- 도로 이탈: on_lane → 십자 도로영역 밖
- NPC: MetaDrive IDM+MOBIL → 순수추종 조향 + 간격 기반 가감속
- 맵: StdInterSection(편도 2~3차선, 반경 10) → 편도 1차선, 회전반경 1.75/5.25
"""
import numpy as np
from numba import njit, prange

import spec
from geometry_md import pack_routes, build_sections_md, build_rules

# 라운드6: MetaDrive X맵 실측 차선 네트워크 — 좌표계까지 MD 그대로.
_WPS, _NWP, _CUM, _TANG, _RLEN, _LOFF = pack_routes()
_SES, _SXY, _SINFO = build_sections_md()          # (36,4) 섹션 4개
_RECTS, _BOX, _CELL, _DGRID = build_rules()

DT_P = np.float32(spec.DT_PHYS)
REP = spec.DECISION_REPEAT
WB = np.float32(spec.WHEELBASE)
MS = np.float32(spec.MAX_STEER)
MA = np.float32(spec.ACCEL_MAX)          # 가속 2.93 (실측)
MB = np.float32(spec.BRAKE_MAX)          # 제동 14.1 (실측, 비대칭)
SV0 = np.float32(spec.STEER_SAT_V0)      # 조향 포화 모델
SSP = np.float32(spec.STEER_SAT_P)
VMAX = np.float32(spec.MAX_SPEED)
VMAX_KMH = np.float32(spec.MAX_SPEED_KMH)
CR = np.float32(spec.COLLISION_RADIUS)
DR = np.float32(spec.DETECT_RADIUS)
NAVI_D = np.float32(spec.NAVI_POINT_DIST)
TW = np.float32(spec.TOTAL_WIDTH)
LW = np.float32(spec.LANE_WIDTH)
NO = spec.NUM_OTHERS
HOR = spec.HORIZON
NPC_V = np.float32(8.0)      # NPC 목표 속도 m/s
LOOKAHEAD = np.float32(6.0)  # 순수추종 전방주시거리 m
RW = np.float32(10.5)             # 로드웨이 폭 (편도 3차선)
# 처방 (ii) 경계 보수화: 학습 시에만 합법 영역을 δ 만큼 수축시켜 §6.3 의 경계 착취를
# 차단한다. 평가(evaluate.py)는 이 변수를 켜지 않으므로 표준 경계 그대로다.
# numba njit 은 모듈 전역을 컴파일 상수로 굽기 때문에 임포트 시점 환경변수로 주입한다.
import os as _os
B_EXTRA = np.float32(float(_os.environ.get("BOUNDARY_EXTRA_M", "0.0")))

OFFLANE_TOL = np.float32(1.95)    # 내부 거리장 on_lane 근사 임계
MARGIN = np.float32(1.852 / 2)    # 차폭 절반 (MD WIDTH=1.852 실측)
HALF_LEN = np.float32(2.3)        # 전장 절반 — MD는 차체 폴리곤으로 선 접촉 판정 (사망거리 1.26~1.35m 실측)
LINE_W2 = np.float32(0.15)        # 차선 도색 반폭
N_EGO_ROUTES = 9                  # 남쪽 팔: 기동3 x 차선3


@njit(inline="always")
def _rnd(rs, e):
    rs[e] = rs[e] * np.uint64(6364136223846793005) + np.uint64(1442695040888963407)
    return np.float32((rs[e] >> np.uint64(33)) & np.uint64(0x7FFFFFFF)) / np.float32(2147483648.0)


@njit(inline="always")
def _clip01(x):
    return 0.0 if x < 0.0 else (1.0 if x > 1.0 else x)


@njit(inline="always")
def _track(rid, wp, x, y, WPS, NWP, CUM, TANG):
    """폴리라인 위 최근접 지점: (새 wp, 호장 long, 좌+ lateral, 접선 tx, ty)."""
    k = NWP[rid]
    i = wp
    while i < k - 2:
        tx = TANG[rid, i, 0]
        ty = TANG[rid, i, 1]
        proj = (x - WPS[rid, i, 0]) * tx + (y - WPS[rid, i, 1]) * ty
        if proj > CUM[rid, i + 1] - CUM[rid, i]:
            i += 1
        else:
            break
    tx = TANG[rid, i, 0]
    ty = TANG[rid, i, 1]
    px = x - WPS[rid, i, 0]
    py = y - WPS[rid, i, 1]
    proj = px * tx + py * ty
    return i, CUM[rid, i] + proj, tx * py - ty * px, tx, ty


@njit(inline="always")
def _place_at_s(rid, s, WPS, NWP, CUM, TANG):
    """호장 s 의 위치·헤딩. 반환 (x, y, heading, wp_idx)."""
    k = NWP[rid]
    i = 0
    while i < k - 2 and CUM[rid, i + 1] < s:
        i += 1
    seg = CUM[rid, i + 1] - CUM[rid, i]
    f = 0.0 if seg <= 0 else (s - CUM[rid, i]) / seg
    x = WPS[rid, i, 0] * (1 - f) + WPS[rid, i + 1, 0] * f
    y = WPS[rid, i, 1] * (1 - f) + WPS[rid, i + 1, 1] * f
    return x, y, np.arctan2(TANG[rid, i, 1], TANG[rid, i, 0]), i


@njit(inline="always")
def _spawn_npc(rs, e, i, npc, npc_rid, npc_wp, RLEN, WPS, NWP, CUM, TANG, ex, ey):
    # ego 주변 8m 는 피해서 스폰 (즉사 방지). 5회 재시도 후에도 겹치면 마지막 후보 사용.
    x = np.float32(0.0)
    y = np.float32(0.0)
    h = np.float32(0.0)
    wp = np.int32(0)
    rid = np.int32(0)
    for _try in range(5):
        rid = np.int32(_rnd(rs, e) * 35.999)
        s = np.float32(2.0) + _rnd(rs, e) * (RLEN[rid] * np.float32(0.7))
        x, y, h, wp = _place_at_s(rid, s, WPS, NWP, CUM, TANG)
        dx = x - ex
        dy = y - ey
        if dx * dx + dy * dy > np.float32(64.0):
            break
    npc[e, i, 0] = x
    npc[e, i, 1] = y
    npc[e, i, 2] = h
    npc[e, i, 3] = np.float32(3.0) + _rnd(rs, e) * np.float32(5.0)
    npc_rid[e, i] = rid
    npc_wp[e, i] = wp


@njit(inline="always")
def _spawn_ego(rs, e, ego, ego_rid, ego_wp, ego_long_last, ego_prev_h, last_act, t,
               WPS, NWP, CUM, TANG):
    rid = np.int32(_rnd(rs, e) * 8.999)        # 남쪽 팔 고정, 기동 3 x 차선 3 무작위 (MD 스폰차선 랜덤 실측)
    # MetaDrive 스폰 실측: 10m 스폰 차선의 중간(5m 지점), 속도 0
    x, y, h, wp = _place_at_s(rid, np.float32(5.0), WPS, NWP, CUM, TANG)
    ego[e, 0] = x
    ego[e, 1] = y
    ego[e, 2] = h
    ego[e, 3] = 0.0                             # MetaDrive 스폰 속도 0
    ego_rid[e] = rid
    ego_wp[e] = wp
    ego_long_last[e] = np.float32(5.0)
    ego_prev_h[e] = h
    last_act[e, 0] = 0.0
    last_act[e, 1] = 0.0
    t[e] = 0


@njit(parallel=True, cache=True)
def _step(WPS, NWP, CUM, TANG, RLEN, LOFF, SES, SXY, SINFO, RECTS, BOX, CELL, DGRID,
          ego, ego_rid, ego_wp, ego_long_last, ego_prev_h, last_act, t, rs,
          npc, npc_rid, npc_wp, pending,
          action, obs, reward, term, trunc, flags):
    E = ego.shape[0]
    V = npc.shape[1]
    for e in prange(E):
        # ---------- 0. NEXT_STEP 리셋: 직전 스텝에 종료된 env 는 이번 스텝에서
        # 행동을 무시하고 리스폰 + 첫 관측만 반환한다 (gymnasium NEXT_STEP 의미론) ----------
        fresh = pending[e] == 1
        if fresh:
            _spawn_ego(rs, e, ego, ego_rid, ego_wp, ego_long_last, ego_prev_h, last_act, t,
                       WPS, NWP, CUM, TANG)
            for i in range(V):
                _spawn_npc(rs, e, i, npc, npc_rid, npc_wp, RLEN, WPS, NWP, CUM, TANG,
                           ego[e, 0], ego[e, 1])
            pending[e] = 0

        # ---------- 1. NPC 제어 ----------
        st_npc = np.empty(V, np.float32)
        ac_npc = np.empty(V, np.float32)
        for i in range(0 if fresh else V):
            rid = npc_rid[e, i]
            x = npc[e, i, 0]
            y = npc[e, i, 1]
            h = npc[e, i, 2]
            v = npc[e, i, 3]
            wp, lng, lat, tx, ty = _track(rid, npc_wp[e, i], x, y, WPS, NWP, CUM, TANG)
            npc_wp[e, i] = wp
            # 전방주시점
            s_t = lng + LOOKAHEAD
            if s_t > RLEN[rid]:
                s_t = RLEN[rid]
            gx, gy, _gh, _gi = _place_at_s(rid, s_t, WPS, NWP, CUM, TANG)
            dx = gx - x
            dy = gy - y
            ch = np.cos(h)
            sh = np.sin(h)
            fwd = ch * dx + sh * dy
            left = -sh * dx + ch * dy
            Ld = np.sqrt(dx * dx + dy * dy) + np.float32(1e-6)
            alpha = np.arctan2(left, fwd)
            sr = np.arctan(np.float32(2.0) * WB * np.sin(alpha) / Ld) / MS
            st_npc[i] = -1.0 if sr < -1.0 else (1.0 if sr > 1.0 else sr)
            # 전방 차량 간격 (ego 포함)
            gap = np.float32(1e9)
            for j in range(V + 1):
                if j == i:
                    continue
                ox = ego[e, 0] if j == V else npc[e, j, 0]
                oy = ego[e, 1] if j == V else npc[e, j, 1]
                rdx = ox - x
                rdy = oy - y
                f2 = ch * rdx + sh * rdy
                l2 = -sh * rdx + ch * rdy
                if 0.0 < f2 < 40.0 and (l2 if l2 > 0 else -l2) < 2.5 and f2 < gap:
                    gap = f2
            if gap < 1e8:
                a = (gap - (np.float32(2.0) + np.float32(1.5) * v)) * np.float32(0.5)
            else:
                a = (NPC_V - v) * np.float32(0.8)
            ac_npc[i] = -MB if a < -MB else (MA if a > MA else a)   # 제동은 14.1까지 허용

        # ---------- 2. 적분 (물리 서브스텝) ----------
        a0 = action[e, 0]
        a0 = -1.0 if a0 < -1.0 else (1.0 if a0 > 1.0 else a0)
        a1 = action[e, 1]
        a1 = -1.0 if a1 < -1.0 else (1.0 if a1 > 1.0 else a1)
        if fresh:
            a0 = np.float32(0.0)
            a1 = np.float32(0.0)
        for _ in range(0 if fresh else REP):
            acc = a1 * MA if a1 > 0.0 else a1 * MB       # 실측: 가속 2.93 / 제동 14.1
            v = ego[e, 3] + acc * DT_P
            v = 0.0 if v < 0.0 else (VMAX if v > VMAX else v)
            # 조향 포화(타이어 슬립 근사): δ_eff = δ / (1 + (|s|·v/V0)^P) — MD 4점 실측 피팅
            sat = np.float32(1.0) + ((a0 if a0 > 0 else -a0) * v / SV0) ** SSP
            hh = ego[e, 2] + v / WB * np.tan(a0 * MS / sat) * DT_P
            ego[e, 0] += v * np.cos(hh) * DT_P
            ego[e, 1] += v * np.sin(hh) * DT_P
            ego[e, 2] = hh
            ego[e, 3] = v
            for i in range(V):
                vi = npc[e, i, 3] + ac_npc[i] * DT_P
                vi = 0.0 if vi < 0.0 else (VMAX if vi > VMAX else vi)
                sti = st_npc[i]
                sati = np.float32(1.0) + ((sti if sti > 0 else -sti) * vi / SV0) ** SSP
                hi = npc[e, i, 2] + vi / WB * np.tan(sti * MS / sati) * DT_P
                npc[e, i, 0] += vi * np.cos(hi) * DT_P
                npc[e, i, 1] += vi * np.sin(hi) * DT_P
                npc[e, i, 2] = hi
                npc[e, i, 3] = vi

        # ---------- 3. NPC 경로 종료 → 재투입 ----------
        for i in range(0 if fresh else V):
            rid = npc_rid[e, i]
            wp, lng, lat, tx, ty = _track(rid, npc_wp[e, i], npc[e, i, 0], npc[e, i, 1],
                                          WPS, NWP, CUM, TANG)
            npc_wp[e, i] = wp
            if lng > RLEN[rid] - np.float32(1.5):
                _spawn_npc(rs, e, i, npc, npc_rid, npc_wp, RLEN, WPS, NWP, CUM, TANG,
                           ego[e, 0], ego[e, 1])

        # ---------- 4. ego 경로 추적 ----------
        rid = ego_rid[e]
        ex = ego[e, 0]
        ey = ego[e, 1]
        eh = ego[e, 2]
        ev = ego[e, 3]
        wp, lng, lat, ltx, lty = _track(rid, ego_wp[e], ex, ey, WPS, NWP, CUM, TANG)
        ego_wp[e] = wp

        # ---------- 5. 관측 51차원 ----------
        # ego 9 (state_obs.py:86~152 공식)
        # 라운드4: 차선별 오프셋 반영. MD 실측 — 우측차선 스폰 시 L/R = 8.75/1.75.
        # 좌측 가장자리(황색 중앙선) = 차선센터에서 lane_off, 우측(백색 실선) = 10.5-lane_off.
        lo = LOFF[rid]
        obs[e, 0] = _clip01((lo - lat) / TW)
        obs[e, 1] = _clip01((RW - lo + lat) / TW)
        # MetaDrive 부호 규약 (2026-08-20 프로브로 실측 확정):
        #   lateral 은 오른쪽=+ (local_coordinates: 왼쪽 0.5m 이동 시 lat=-0.5)
        #   heading_diff 는 좌회전 시 감소 (정렬 0.500 → 좌 10° 0.413)
        # → 우법선 기준으로 계산해야 전이 시 의미가 일치한다.
        nx = lty                                     # 차선 우법선
        ny = -ltx
        obs[e, 2] = _clip01((np.cos(eh) * nx + np.sin(eh) * ny + np.float32(1.0)) / np.float32(2.0))
        obs[e, 3] = _clip01((ev * np.float32(3.6) + np.float32(1.0)) / (VMAX_KMH + np.float32(1.0)))
        obs[e, 4] = _clip01((a0 + np.float32(1.0)) / np.float32(2.0))
        obs[e, 5] = _clip01((a0 + np.float32(1.0)) / np.float32(2.0))
        obs[e, 6] = _clip01((a1 + np.float32(1.0)) / np.float32(2.0))
        dh = eh - ego_prev_h[e]
        obs[e, 7] = _clip01((dh if dh > 0 else -dh) / np.float32(0.1))
        obs[e, 8] = _clip01((-lat * np.float32(2.0) / LW + np.float32(1.0)) / np.float32(2.0))  # 우측=+
        ego_prev_h[e] = eh

        # navi 10 (node_network_navigation.py:288~345 공식)
        sec = 0
        for j in range(3):
            if lng > SES[rid, j]:
                sec = j + 1
        fx = np.cos(eh)
        fy = np.sin(eh)
        rx = fy
        ry = -fx                                     # 우측 벡터
        for c in range(2):
            sc = sec if c == 0 else (sec + 1 if sec < 3 else 3)
            dxc = SXY[rid, sc, 0] - ex
            dyc = SXY[rid, sc, 1] - ey
            dn = np.sqrt(dxc * dxc + dyc * dyc)
            if dn > NAVI_D:
                dxc *= NAVI_D / dn
                dyc *= NAVI_D / dn
            b = 9 + c * 5
            obs[e, b + 0] = _clip01(((dxc * fx + dyc * fy) / NAVI_D + np.float32(1.0)) / np.float32(2.0))
            obs[e, b + 1] = _clip01(((dxc * rx + dyc * ry) / NAVI_D + np.float32(1.0)) / np.float32(2.0))
            obs[e, b + 2] = SINFO[rid, sc, 0]
            obs[e, b + 3] = SINFO[rid, sc, 1]
            obs[e, b + 4] = SINFO[rid, sc, 2]

        # GT 8대 x 4 (lidar.py:100~118 공식: 위치 /50, 상대속도(km/h) /80, (x+1)/2 클립)
        d_all = np.empty(V, np.float32)
        for i in range(V):
            ddx = npc[e, i, 0] - ex
            ddy = npc[e, i, 1] - ey
            d_all[i] = np.sqrt(ddx * ddx + ddy * ddy)
        used = np.zeros(V, np.uint8)
        k = NO if NO < V else V
        min_d = np.float32(1e9)
        for s2 in range(k):
            best = -1
            bd = np.float32(1e18)
            for i in range(V):
                if used[i] == 0 and d_all[i] < bd:
                    bd = d_all[i]
                    best = i
            used[best] = 1
            if s2 == 0:
                min_d = bd
            b = 19 + s2 * 4
            if bd < DR:
                ddx = npc[e, best, 0] - ex
                ddy = npc[e, best, 1] - ey
                dvx = (npc[e, best, 3] * np.cos(npc[e, best, 2]) - ev * fx) * np.float32(3.6)
                dvy = (npc[e, best, 3] * np.sin(npc[e, best, 2]) - ev * fy) * np.float32(3.6)
                obs[e, b + 0] = _clip01(((ddx * fx + ddy * fy) / DR + np.float32(1.0)) / np.float32(2.0))
                obs[e, b + 1] = _clip01(((ddx * rx + ddy * ry) / DR + np.float32(1.0)) / np.float32(2.0))
                obs[e, b + 2] = _clip01(((dvx * fx + dvy * fy) / VMAX_KMH + np.float32(1.0)) / np.float32(2.0))
                obs[e, b + 3] = _clip01(((dvx * rx + dvy * ry) / VMAX_KMH + np.float32(1.0)) / np.float32(2.0))
            else:
                obs[e, b + 0] = 0.0
                obs[e, b + 1] = 0.0
                obs[e, b + 2] = 0.0
                obs[e, b + 3] = 0.0
        for s2 in range(k, NO):
            b = 19 + s2 * 4
            obs[e, b + 0] = 0.0
            obs[e, b + 1] = 0.0
            obs[e, b + 2] = 0.0
            obs[e, b + 3] = 0.0

        # ---------- 6. 보상·종료 (metadrive_env.py:245~296 공식) ----------
        if fresh:
            reward[e] = 0.0
            term[e] = False
            trunc[e] = False
            flags[e] = 0
        else:
            # 라운드6: 실측 규칙 — 생존 = (로드웨이 rect 안 & 실선 비접촉) OR (교차로 거리장 합법).
            # 두 판정을 OR 로 묶어 박스↔rect 이음새 오탐을 제거 (전문가 22회 가짜사망으로 발견).
            rect_alive = False
            for rrr in range(RECTS.shape[0]):
                a0 = RECTS[rrr, 0]
                a1 = RECTS[rrr, 1]
                rlo = RECTS[rrr, 2]
                rhi = RECTS[rrr, 3]
                ax_ = RECTS[rrr, 4]
                acoord = ex if ax_ < 0.5 else ey
                latc = ey if ax_ < 0.5 else ex
                if a0 - 0.01 <= acoord <= a1 + 0.01 and rlo <= latc <= rhi:
                    dev = np.sin(eh) if ax_ < 0.5 else np.cos(eh)
                    dev = dev if dev > 0 else -dev
                    m_eff = MARGIN + HALF_LEN * dev + LINE_W2 + B_EXTRA
                    rect_alive = not (latc < rlo + m_eff or latc > rhi - m_eff)
                    break
            grid_alive = False
            if BOX[0] < ex < BOX[1] and BOX[2] < ey < BOX[3]:
                gi = np.int64((ex - BOX[0]) / CELL)
                gj = np.int64((ey - BOX[2]) / CELL)
                gi = 0 if gi < 0 else (DGRID.shape[0] - 1 if gi >= DGRID.shape[0] else gi)
                gj = 0 if gj < 0 else (DGRID.shape[1] - 1 if gj >= DGRID.shape[1] else gj)
                grid_alive = DGRID[gi, gj] <= OFFLANE_TOL - B_EXTRA
            line_kill = not (rect_alive or grid_alive)
            crashed = min_d < CR
            arrived = lng >= RLEN[rid] - np.float32(2.0)
            out_road = line_kill and (not arrived)
            t[e] += 1
            timeout = t[e] >= HOR

            r = np.float32(1.0) * (lng - ego_long_last[e]) \
                + np.float32(0.1) * (ev * np.float32(3.6) / VMAX_KMH)
            if arrived:
                r = np.float32(10.0)
            elif out_road:
                r = np.float32(-5.0)
            elif crashed:
                r = np.float32(-5.0)
            reward[e] = r
            ego_long_last[e] = lng

            is_term = crashed or out_road or arrived
            term[e] = is_term
            trunc[e] = timeout and not is_term
            flags[e] = 1 if crashed else (2 if out_road else (3 if arrived else (4 if timeout else 0)))

            # ---------- 7. NEXT_STEP: 종료 표시만 하고 리스폰은 다음 스텝 첫머리에 ----------
            if is_term or timeout:
                pending[e] = 1

            last_act[e, 0] = a0
            last_act[e, 1] = a1


class IntersectionEnv:
    """배치 교차로 환경. step(action) -> (obs, reward, terminated, truncated, flags)."""

    def __init__(self, n_envs, n_vehicles=16, seed=0):
        self.E, self.V = n_envs, n_vehicles
        self.rs = (np.uint64(seed) * np.uint64(2654435761) +
                   np.arange(1, n_envs + 1, dtype=np.uint64) * np.uint64(0x9E3779B97F4A7C15))
        self.ego = np.zeros((self.E, 4), np.float32)
        self.ego_rid = np.zeros(self.E, np.int32)
        self.ego_wp = np.zeros(self.E, np.int32)
        self.ego_long_last = np.zeros(self.E, np.float32)
        self.ego_prev_h = np.zeros(self.E, np.float32)
        self.last_act = np.zeros((self.E, 2), np.float32)
        self.t = np.zeros(self.E, np.int32)
        self.npc = np.zeros((self.E, self.V, 4), np.float32)
        self.npc_rid = np.zeros((self.E, self.V), np.int32)
        self.npc_wp = np.zeros((self.E, self.V), np.int32)
        self.obs = np.zeros((self.E, spec.OBS_DIM), np.float32)
        self.reward = np.zeros(self.E, np.float32)
        self.term = np.zeros(self.E, np.bool_)
        self.trunc = np.zeros(self.E, np.bool_)
        self.flags = np.zeros(self.E, np.int8)
        self.pending = np.zeros(self.E, np.int8)
        self.reset()

    def reset(self):
        # NEXT_STEP: 전 env 를 pending 으로 만들고 0-행동 스텝을 돌리면
        # 커널의 fresh 경로가 리스폰 + 첫 관측 조립을 수행한다 (보상 0, done False).
        self.pending[:] = 1
        a = np.zeros((self.E, 2), np.float32)
        obs, *_ = self.step(a)
        return obs.copy()

    def step(self, action):
        _step(_WPS, _NWP, _CUM, _TANG, _RLEN, _LOFF, _SES, _SXY, _SINFO,
              _RECTS, _BOX, _CELL, _DGRID,
              self.ego, self.ego_rid, self.ego_wp, self.ego_long_last, self.ego_prev_h,
              self.last_act, self.t, self.rs,
              self.npc, self.npc_rid, self.npc_wp, self.pending,
              np.ascontiguousarray(action, dtype=np.float32),
              self.obs, self.reward, self.term, self.trunc, self.flags)
        return self.obs, self.reward, self.term, self.trunc, self.flags

    # ---- 테스트용 특권 조작 ----
    def expert_action(self):
        """순수추종 + 목표속도 8m/s 의 스크립트 운전 (검증용, NumPy)."""
        act = np.zeros((self.E, 2), np.float32)
        for e in range(self.E):
            rid = self.ego_rid[e]
            x, y, h, v = self.ego[e]
            k = int(_NWP[rid])
            i = int(self.ego_wp[e])
            tx, ty = _TANG[rid, i]
            lng = _CUM[rid, i] + (x - _WPS[rid, i, 0]) * tx + (y - _WPS[rid, i, 1]) * ty
            s_t = min(lng + 6.0, float(_RLEN[rid]))
            j = i
            while j < k - 2 and _CUM[rid, j + 1] < s_t:
                j += 1
            seg = _CUM[rid, j + 1] - _CUM[rid, j]
            f = 0.0 if seg <= 0 else (s_t - _CUM[rid, j]) / seg
            gx = _WPS[rid, j, 0] * (1 - f) + _WPS[rid, j + 1, 0] * f
            gy = _WPS[rid, j, 1] * (1 - f) + _WPS[rid, j + 1, 1] * f
            dx, dy = gx - x, gy - y
            fwd = np.cos(h) * dx + np.sin(h) * dy
            left = -np.sin(h) * dx + np.cos(h) * dy
            Ld = np.hypot(dx, dy) + 1e-6
            alpha = np.arctan2(left, fwd)
            act[e, 0] = np.clip(np.arctan(2 * spec.WHEELBASE * np.sin(alpha) / Ld) / spec.MAX_STEER, -1, 1)
            act[e, 1] = np.clip((8.0 - v) * 0.5, -1, 1)
        return act
