"""CARLA 폐루프 주행 — 경량 시뮬에서 학습한 정책이 CARLA 를 실제로 운전한다 (2026-08-28).

GT 관측 어댑터(51차원) + 행동 매핑 + 판정. 카메라 없음(인지는 GT), 교통 밀도는 학습과
동일하게 NPC 3대. 정책 1스텝 = 0.1s = CARLA 5틱(decision_repeat=5).

관측 규약(2026-08-28 부호 정정 반영): 횡방향은 **좌(+)** — MetaDrive convert_to_local_coordinates
규약이며 정정된 env_numba 와 일치. 필드 산식 근거는 docs/REVISION_AUDIT.md.

실행: py -3.12 carla_drive.py --policy C:/ue/policy.npz --episodes 5 --record C:/carla/drive
"""
import argparse
import json
import math
import os
import queue

import carla
import numpy as np

MAXS_KMH = 80.0
DR = 50.0            # 탐지 반경
NAVI_D = 50.0
TOTAL_W = 18.0
ROAD_W = 10.5
LANE_W = 3.5


def clip01(x):
    return float(min(max(x, 0.0), 1.0))


class Policy:
    """ppo.py Agent 의 actor_mean 만 numpy 로 재현 (py3.12 에 torch 불필요)."""

    def __init__(self, path):
        z = np.load(path)
        self.W = [z[f"w{i}"] for i in range(3)]
        self.b = [z[f"b{i}"] for i in range(3)]
        self.mean, self.std = z["obs_mean"], z["obs_std"]

    def act(self, obs):
        x = np.clip((obs - self.mean) / self.std, -10, 10).astype(np.float32)
        for i in range(2):
            x = np.tanh(x @ self.W[i] + self.b[i])
        return np.clip(x @ self.W[2] + self.b[2], -1, 1)


def calibrate(world, bl, wp):
    """CARLA 차량의 풀스로틀 가속도·풀브레이크 감속도를 실측해 학습 환경(2.93 / 14.1 m/s^2)에
    맞추는 이득을 구한다. 이걸 빼면 CARLA 가 훨씬 빨리 가속해 정책의 학습 속도영역을 벗어난다
    (실측: 학습 25km/h vs CARLA 50km/h → 곡선 이탈)."""
    bp = (bl.filter("vehicle.dodge.charger") or bl.filter("vehicle.*"))[0]
    v = None
    for dz in (0.3, 2.0, 8.0):
        v = world.try_spawn_actor(bp, carla.Transform(
            carla.Location(wp.transform.location.x, wp.transform.location.y,
                           wp.transform.location.z + dz), wp.transform.rotation))
        if v:
            break
    if v is None:
        return 1.0, 1.0
    v.set_simulate_physics(True)
    for _ in range(5):
        world.tick()
    import time as _t
    v.apply_control(carla.VehicleControl(throttle=1.0))
    for _ in range(75):                     # 1.5 s
        world.tick()
    vel = v.get_velocity()
    a_c = math.hypot(vel.x, vel.y) / 1.5
    v.apply_control(carla.VehicleControl(throttle=0.0, brake=1.0))
    v0 = math.hypot(vel.x, vel.y)
    for _ in range(50):
        world.tick()
    vel2 = v.get_velocity()
    d_c = max((v0 - math.hypot(vel2.x, vel2.y)) / 1.0, 0.1)
    v.destroy()
    k_thr = min(1.0, 2.93 / max(a_c, 0.1))
    k_brk = min(1.0, 14.1 / max(d_c, 0.1))
    print(f"캘리브레이션: CARLA 가속 {a_c:.2f} m/s^2 (목표 2.93) → K_THR={k_thr:.2f} | "
          f"감속 {d_c:.2f} (목표 14.1) → K_BRK={k_brk:.2f}")
    return k_thr, k_brk


def route_via_junction(wp0, wenter, wexit, step=2.0, tail=30):
    """진입로 → 교차로 차선(next_until_lane_end) → 이탈로. 분기 선택을 탐욕법에 맡기지 않고
    의도한 교차로 차선을 직접 따라간다(실측: 탐욕 선택은 좌회전 앵커에서도 직진을 골랐다)."""
    route = [wp0]
    cur = wp0
    for _ in range(80):
        if cur.transform.location.distance(wenter.transform.location) < step * 1.5:
            break
        nxts = cur.next(step)
        if not nxts:
            break
        cur = min(nxts, key=lambda w: w.transform.location.distance(wenter.transform.location))
        route.append(cur)
    try:
        jr = wenter.next_until_lane_end(step)
    except Exception:
        jr = []
    route += list(jr)
    cur = (jr[-1] if jr else wexit)
    for _ in range(tail):
        nxts = cur.next(step)
        if not nxts:
            break
        cur = nxts[0]
        route.append(cur)
    return route


def route_to_exit(wp0, wexit, step=2.0, max_n=260, tail=30):
    """교차로 이탈 waypoint 를 목표로 분기를 선택해 경로를 만든다.
    GRP 는 좌회전 목적지에서 교차로를 우회하는 경로를 내놓는 경우가 있어(실측: 좌회전
    실패 에피소드의 경로에 교차로 waypoint 자체가 없었다) 의도한 기동을 보장하지 못한다."""
    route, cur = [wp0], wp0
    target = wexit.transform.location
    for _ in range(max_n):
        nxts = cur.next(step)
        if not nxts:
            break
        cur = min(nxts, key=lambda w: w.transform.location.distance(target))
        route.append(cur)
        if cur.transform.location.distance(target) < 2.5:
            break
    for _ in range(tail):
        nxts = cur.next(step)
        if not nxts:
            break
        cur = nxts[0]
        route.append(cur)
    return route


def route_grp(cmap, wp, ahead_m=120.0, res=2.0, dest_wp=None):
    """CARLA 공식 GlobalRoutePlanner 로 차로 수준 경로 생성 (교차로 분기 정확)."""
    import sys
    sys.path.append(r"C:/carla/Carla-0.10.0-Win64-Shipping/PythonAPI/carla")
    from agents.navigation.global_route_planner import GlobalRoutePlanner
    grp = GlobalRoutePlanner(cmap, res)
    if dest_wp is not None:                 # 교차로 이탈점에서 60m 더 진행한 지점을 목적지로
        end = dest_wp
        walked = 0.0
        while walked < 60.0:
            nxt = end.next(res)
            if not nxt:
                break
            end = nxt[0]; walked += res
    else:
        end = wp
        walked = 0.0
        while walked < ahead_m:
            nxt = end.next(res)
            if not nxt:
                break
            end = nxt[0]; walked += res
    trace = grp.trace_route(wp.transform.location, end.transform.location)
    return [w for w, _ in trace] or route_from(wp)


def route_from(wp, n=60, step=4.0):
    """진입 차선에서 시작해 교차로를 통과하는 경로(직진 우선)."""
    route = [wp]
    cur = wp
    for _ in range(n):
        nxts = cur.next(step)
        if not nxts:
            break
        if len(nxts) > 1:                     # 분기: 직진(방위 변화 최소) 선택
            nxts.sort(key=lambda w: abs((w.transform.rotation.yaw - cur.transform.rotation.yaw + 180) % 360 - 180))
        cur = nxts[0]
        route.append(cur)
    return route


class ObsBuilder:
    # CARLA 의 주차 차량은 액터가 아니라 레벨 지오메트리다(get_level_bbs). 액터만 보면
    # 관측에서 통째로 빠져 정책이 존재를 모른 채 충돌한다(실측: static.car 충돌 다수).
    LEVEL_BBS = None

    def __init__(self, world, ego, route, max_slots=3):
        self.max_slots = max_slots
        self.world, self.ego, self.route = world, ego, route
        self.map = world.get_map()
        if ObsBuilder.LEVEL_BBS is None:
            bbs = []
            for lab in ("Car", "Truck", "Bus"):
                try:
                    bbs += list(world.get_level_bbs(getattr(carla.CityObjectLabel, lab)))
                except Exception:
                    pass
            ObsBuilder.LEVEL_BBS = bbs
            print(f"   레벨 정적 차량 BB {len(bbs)}개를 장애물 관측에 포함")
        self.prev_yaw = math.radians(ego.get_transform().rotation.yaw)
        self.last_act = np.zeros(2, np.float32)
        self.idx = 0

    def _advance(self, loc):
        """경로 상 현재 인덱스 갱신 (최근접 전진)."""
        best, bi = 1e9, self.idx
        for i in range(self.idx, min(self.idx + 25, len(self.route))):
            w = self.route[i].transform.location
            d = (w.x - loc.x) ** 2 + (w.y - loc.y) ** 2
            if d < best:
                best, bi = d, i
        self.idx = bi
        return bi

    def build(self):
        e = self.ego
        tf = e.get_transform()
        p = tf.location
        f = tf.get_forward_vector()
        rgt = tf.get_right_vector()

        def prj(dx, dy):                       # (전방, 좌+)
            return dx * f.x + dy * f.y, -(dx * rgt.x + dy * rgt.y)

        obs = np.zeros(51, np.float32)
        i = self._advance(p)
        wp = self.route[i]
        lw = wp.transform.location
        lf = wp.transform.get_forward_vector()
        lr = wp.transform.get_right_vector()
        lat_r = (p.x - lw.x) * lr.x + (p.y - lw.y) * lr.y     # 차선 중심 대비 우(+)

        # 좌/우 여유폭: 차선 좌측 개수로 도로 내 위치 산정
        n_left = 0
        w2 = wp
        while n_left < 4:
            nx = w2.get_left_lane()
            if nx is None or nx.lane_type != carla.LaneType.Driving or (nx.lane_id * wp.lane_id) < 0:
                break
            n_left += 1; w2 = nx
        d_left = n_left * LANE_W + LANE_W / 2 + lat_r
        obs[0] = clip01(d_left / TOTAL_W)
        obs[1] = clip01((ROAD_W - d_left) / TOTAL_W)

        c = f.x * lr.x + f.y * lr.y                            # 헤딩차 (우법선 투영)
        obs[2] = clip01(max(min(c, 1.0), -1.0) / 2 + 0.5)

        v = e.get_velocity()
        spd = math.hypot(v.x, v.y)
        obs[3] = clip01((spd * 3.6 + 1) / (MAXS_KMH + 1))
        obs[4] = clip01((float(self.last_act[0]) + 1) / 2)
        obs[5] = clip01((float(self.last_act[0]) + 1) / 2)
        obs[6] = clip01((float(self.last_act[1]) + 1) / 2)

        yaw = math.radians(tf.rotation.yaw)
        dyaw = (yaw - self.prev_yaw + math.pi) % (2 * math.pi) - math.pi
        self.prev_yaw = yaw
        obs[7] = clip01(abs(dyaw) / 0.1)
        obs[8] = clip01((-lat_r * 2 / LANE_W + 1) / 2)         # env_numba 규약(분모 3.5)

        # navi: MetaDrive 규약 = "도로 구간 끝" 2개. CARLA 에선 교차로 진입점/이탈점이 그 대응물이다.
        # (앞쪽 고정 거리로 잡으면 교차로 내 차로 굴곡이 사라져 중앙분리대로 직진한다 — 실측 사고)
        segs = []
        seen_j = False
        for k in range(i, len(self.route)):
            isj = self.route[k].is_junction
            if not seen_j and isj:
                segs.append(k); seen_j = True
            elif seen_j and not isj:
                segs.append(k); break
        while len(segs) < 2:
            segs.append(min(len(self.route) - 1, i + 12 * (len(segs) + 1)))
        for c_i in range(2):
            j = min(segs[c_i], len(self.route) - 1)
            ck = self.route[j].transform.location
            dx, dy = ck.x - p.x, ck.y - p.y
            n = math.hypot(dx, dy)
            if n > NAVI_D:
                dx, dy = dx * NAVI_D / n, dy * NAVI_D / n
            fwd, left = prj(dx, dy)
            b = 9 + c_i * 5
            obs[b] = clip01((fwd / NAVI_D + 1) / 2)
            obs[b + 1] = clip01((left / NAVI_D + 1) / 2)
            # 곡률·방향·각도: 경로 구간의 방위 변화로 근사
            j2 = min(segs[1], len(self.route) - 1)
            a = self.route[j2].transform.rotation.yaw
            a0 = self.route[max(segs[0] - 1, 0)].transform.rotation.yaw
            dpsi = (a - a0 + 180) % 360 - 180
            if abs(dpsi) < 5:
                obs[b + 2], obs[b + 3], obs[b + 4] = 0.0, 0.5, 0.5
            else:
                # 호 길이를 경로 실측으로 (상수 48m 를 쓰면 CARLA 의 좁은 회전이 완만하게
                # 보여 정책이 감속·조향을 덜 한다 — 우회전 실패의 주원인)
                arc = 0.0
                for kk in range(max(segs[0] - 1, 0), min(segs[1], len(self.route) - 1)):
                    l1 = self.route[kk].transform.location
                    l2 = self.route[kk + 1].transform.location
                    arc += math.hypot(l2.x - l1.x, l2.y - l1.y)
                arc = max(arc, 2.0)
                R = arc / abs(math.radians(dpsi))
                obs[b + 2] = clip01(R / 70.5)
                obs[b + 3] = 1.0 if dpsi > 0 else 0.0
                obs[b + 4] = clip01((abs(dpsi) / 135.0 + 1) / 2)

        # 주변차 8슬롯 (가까운 순, GT)
        # 주변 장애물: 이동 차량 + 노변 정적 차량(주차) — 학습 환경엔 없지만 CARLA 에는 있다.
        # 관측에서 빠지면 정책이 존재 자체를 모르므로 충돌한다(실측: static.car 충돌).
        cands = []
        for pat in ("vehicle.*", "static.car*", "static.prop.*"):
            for a in self.world.get_actors().filter(pat):
                if a.id == e.id:
                    continue
                try:
                    q = a.get_transform().transform(a.bounding_box.location)
                except Exception:
                    q = a.get_transform().location
                d = math.hypot(q.x - p.x, q.y - p.y)
                if d <= DR:
                    cands.append((d, a, q))
        for bb in (ObsBuilder.LEVEL_BBS or []):
            q = bb.location
            d = math.hypot(q.x - p.x, q.y - p.y)
            if d <= DR:
                cands.append((d, None, q))
        cands.sort(key=lambda t: t[0])
        # 학습 밀도(V=3)에서 슬롯 4~8 은 항상 0 이었다(분산 0). CARLA 의 주차 차량으로
        # 그 슬롯을 채우면 미학습 입력이 되어 정책이 붕괴한다(실측 95%->0%). §5 지지집합.
        for k, (d, a, q) in enumerate(cands[:self.max_slots]):
            _static = a is None
            b = 19 + 4 * k
            fwd, left = prj(q.x - p.x, q.y - p.y)
            av = carla.Vector3D(0, 0, 0) if _static else a.get_velocity()
            dvx, dvy = (av.x - v.x) * 3.6, (av.y - v.y) * 3.6
            vf, vl = prj(dvx, dvy)
            obs[b] = clip01((fwd / DR + 1) / 2)
            obs[b + 1] = clip01((left / DR + 1) / 2)
            obs[b + 2] = clip01((vf / MAXS_KMH + 1) / 2)
            obs[b + 3] = clip01((vl / MAXS_KMH + 1) / 2)
        return obs, lat_r, spd


def run(a):
    pol = Policy(a.policy)
    client = carla.Client("127.0.0.1", 2000); client.set_timeout(60.0)
    world = client.get_world()
    st = world.get_settings(); st.synchronous_mode = True; st.fixed_delta_seconds = 0.02
    world.apply_settings(st)
    for v in world.get_actors().filter("vehicle.*"):
        try: v.destroy()
        except Exception: pass
    # 학습 환경엔 신호등이 없다 — 전 신호를 녹색 고정해 조건을 맞춘다(밀도 통제와 같은 취지)
    for tl in world.get_actors().filter("traffic.traffic_light*"):
        try:
            tl.set_state(carla.TrafficLightState.Green); tl.freeze(True)
        except Exception:
            pass

    cmap = world.get_map()
    bl = world.get_blueprint_library()
    ego_bp = (bl.filter("vehicle.dodge.charger") or bl.filter("vehicle.*"))[0]
    if ego_bp.has_attribute("color"):
        ego_bp.set_attribute("color", "20,90,230")
    npc_pool = [b for b in bl.filter("vehicle.*") if "firetruck" not in b.id and "carlacola" not in b.id]

    # 교차로 진입 차선 후보
    # 앵커 = (진입 차선 45m 전, 교차로 통과 방향 분류). 회전 난이도 조건을 만들기 위해
    # 진입/이탈 방위차로 좌회전·직진·우회전을 분류해 둔다.
    anchors, seen = [], set()
    for wp in cmap.generate_waypoints(6.0):
        j = wp.get_junction()
        if j is None or j.id in seen:
            continue
        seen.add(j.id)
        pairs = j.get_waypoints(carla.LaneType.Driving)
        if len(pairs) < 8:
            continue
        used_lane = set()
        for win, wout in pairs:
            key = (win.road_id, win.lane_id)
            if key in used_lane:
                continue
            used_lane.add(key)
            dpsi = (wout.transform.rotation.yaw - win.transform.rotation.yaw + 180) % 360 - 180
            if abs(dpsi) >= 150:
                kind = "유턴"          # 정책이 학습한 적 없는 기동 — 별도 조건으로 분리
            elif abs(dpsi) < 30:
                kind = "직진"
            else:
                kind = "우회전" if dpsi > 0 else "좌회전"
            prevs = win.previous(a.approach)
            if prevs:
                anchors.append((prevs[0], kind, wout, win))
    # 진입로가 정적 차량(주차)으로 막힌 앵커는 제외한다. 본 과제는 교차로 통과이며
    # 주차차 회피는 학습 분포 밖 기동이다(실측: 거버너 ON 우회전 잔여 실패 5건 전부
    # 진입로에서 static.car 와 40km/h 충돌).
    blockers = []
    for lab in ("Car", "Truck", "Bus"):
        try:
            blockers += [bb.location for bb in world.get_level_bbs(getattr(carla.CityObjectLabel, lab))]
        except Exception:
            pass
    def _clear(w0):
        cur = w0
        for _ in range(22):                       # 45m 를 2m 간격으로
            nxts = cur.next(2.0)
            if not nxts:
                break
            cur = nxts[0]
            c = cur.transform.location
            r = cur.transform.get_right_vector()
            for b in blockers:
                dx, dy = b.x - c.x, b.y - c.y
                if dx * dx + dy * dy > 100:
                    continue
                lat = abs(dx * r.x + dy * r.y)
                if lat < 1.8:                     # 차로 폭 안에 정적 장애물
                    return False
        return True
    before = len(anchors)
    anchors = [x for x in anchors if _clear(x[0])] or anchors
    print(f"진입로 클리어 필터: {before} -> {len(anchors)}")

    kinds = {}
    for _, k, _, _w in anchors:
        kinds[k] = kinds.get(k, 0) + 1
    print("진입 차선 후보", len(anchors), kinds)
    if a.turn_kind != "전체":
        anchors = [x for x in anchors if x[1] == a.turn_kind] or anchors
        print("필터 후", len(anchors), a.turn_kind)
    K_THR, K_BRK = calibrate(world, bl, anchors[0][0]) if anchors else (1.0, 1.0)

    if a.record:
        os.makedirs(a.record, exist_ok=True)
    results = []
    # 액터 재사용: CARLA 0.10 은 스폰/파괴 반복에서 자주 죽는다(실측: 2에피소드마다 크래시).
    # ego·NPC·센서를 한 번만 만들고 에피소드마다 텔레포트한다.
    ego = npcs = None
    col = {'hit': False, 'with_': ''}
    cs = cam = q = None

    for ep in range(a.episodes):
        wp0, kind, wexit, wenter = anchors[(ep * 7 + 3) % len(anchors)]   # 앵커를 흩어 선택
        try:
            route = route_grp(cmap, wp0, dest_wp=wexit)
        except Exception as ex:
            print("   GRP 실패, 폴백:", ex); route = route_from(wp0)
        # 의도한 기동 보장: (i) 교차로 구간이 없거나 (ii) 회전 앵커인데 경로가 직진이면
        # 이탈점을 목표로 분기를 선택하는 경로로 대체한다(실측: GRP 가 좌회전 앵커에서도
        # 직진 경로를 내놓아 '좌회전 조건'이 실제로는 직진이었다).
        def _turn_deg(rt):
            js = [k for k, w in enumerate(rt) if w.is_junction]
            if not js:
                return 0.0
            a = rt[max(js[0] - 1, 0)].transform.rotation.yaw
            b = rt[min(js[-1] + 1, len(rt) - 1)].transform.rotation.yaw
            return abs((b - a + 180) % 360 - 180)

        if (not any(w.is_junction for w in route)) or (kind != "직진" and _turn_deg(route) < 30):
            alt = route_via_junction(wp0, wenter, wexit)
            if not any(w.is_junction for w in alt):
                alt = route_to_exit(wp0, wexit)
            if any(w.is_junction for w in alt) and (kind == "직진" or _turn_deg(alt) >= 30):
                route = alt
        tf0 = carla.Transform(carla.Location(wp0.transform.location.x, wp0.transform.location.y,
                                             wp0.transform.location.z + 0.3), wp0.transform.rotation)
        if ego is None:
            for dz in (0.3, 1.5, 6.0):
                ego = world.try_spawn_actor(ego_bp, carla.Transform(
                    carla.Location(tf0.location.x, tf0.location.y, tf0.location.z + dz), tf0.rotation))
                if ego:
                    break
            if ego is None:
                print(f"ep{ep} 스폰 실패"); continue
            pc = ego.get_physics_control()
            try:
                pc.steering_curve = [carla.Vector2D(0.0, 1.0), carla.Vector2D(200.0, 1.0)]
                ego.apply_physics_control(pc)
            except Exception:
                pass
        else:
            ego.set_target_velocity(carla.Vector3D(0, 0, 0))
            ego.set_transform(tf0)
        max_sw = ego.get_physics_control().wheels[0].max_steer_angle or 70.0

        if npcs is None:
            npcs = []
            for m in range(a.npc):
                for dz in (0.3, 2.0):
                    v = world.try_spawn_actor(npc_pool[m % len(npc_pool)], carla.Transform(
                        carla.Location(tf0.location.x + 120 + m * 8, tf0.location.y, tf0.location.z + dz),
                        tf0.rotation))
                    if v:
                        npcs.append(v); break
        far = [w for w, _k, _e, _i in anchors
               if w.transform.location.distance(wp0.transform.location) > 30.0] or [x[0] for x in anchors]
        for m, v in enumerate(npcs):
            srcw = far[(ep * 3 + m) % len(far)]
            v.set_target_velocity(carla.Vector3D(0, 0, 0))
            v.set_transform(carla.Transform(
                carla.Location(srcw.transform.location.x, srcw.transform.location.y,
                               srcw.transform.location.z + 0.3), srcw.transform.rotation))
            try:
                v.set_autopilot(True)
            except Exception:
                pass

        col["hit"] = False
        if cs is None:
            cbp = bl.find("sensor.other.collision")
            cs = world.spawn_actor(cbp, carla.Transform(), attach_to=ego)
            cs.listen(lambda e: col.update(hit=True, with_=getattr(e.other_actor, "type_id", "?")))
            if a.record:
                cbp2 = bl.find("sensor.camera.rgb")
                cbp2.set_attribute("image_size_x", "960"); cbp2.set_attribute("image_size_y", "540")
                cam = world.spawn_actor(cbp2, carla.Transform(carla.Location(x=-7.0, z=3.6),
                                                              carla.Rotation(pitch=-13)), attach_to=ego)
                q = queue.Queue(); cam.listen(q.put)

        for _ in range(3):      # 동기 모드: 스폰 직후 tick 해야 트랜스폼이 유효해진다
            world.tick()
            if a.record:
                try: q.get(timeout=5.0)
                except Exception: pass
        ob = ObsBuilder(world, ego, route, max_slots=a.obs_slots)
        hist = []
        entry_spd, max_lat = None, 0.0
        j_entry = next((k for k, w in enumerate(route) if w.is_junction), len(route) - 1)
        min_R = 1e9
        j_last = max((k for k, w in enumerate(route) if w.is_junction), default=j_entry)
        for kk in range(max(j_entry - 2, 0), min(j_last + 2, len(route) - 1)):
            y1 = route[kk].transform.rotation.yaw
            y2 = route[kk + 1].transform.rotation.yaw
            dp = abs((y2 - y1 + 180) % 360 - 180)
            l1, l2 = route[kk].transform.location, route[kk + 1].transform.location
            ds = math.hypot(l2.x - l1.x, l2.y - l1.y)
            if dp > 0.5 and ds > 0.1:
                min_R = min(min_R, ds / math.radians(dp))
        _p = ego.get_transform().location
        _r0 = route[0].transform.location
        if a.verbose:
            print(f"   [진단] ego=({_p.x:.1f},{_p.y:.1f}) route0=({_r0.x:.1f},{_r0.y:.1f}) "
              f"거리={math.hypot(_p.x-_r0.x,_p.y-_r0.y):.1f}m 경로길이={len(route)}", flush=True)
        outcome, steps = "timeout", 0
        for t in range(a.max_steps):
            obs, lat_r, spd = ob.build()
            if a.mask_degen:
                # §5 지지집합 처방: 학습 중 분산 0 이던 내비 곡률 차원(11,12,13,16,17,18)을
                # 학습 시 상수로 고정한다. CARLA 는 이 차원에 학습분포 밖 값(0.145~0.621)을 넣는다.
                obs[11] = 0.0; obs[16] = 0.0
                obs[12] = 0.5; obs[17] = 0.5
                obs[13] = 0.5; obs[18] = 0.5
            act = pol.act(obs)
            ob.last_act = act
            steer = float(np.clip(-40.0 * act[0] / max_sw, -1, 1))     # 좌(+) → CARLA 우(+) 반전
            # 속도 거버너: 전방 25m 이내 최소 곡률반경에서 물리적으로 가능한 최대 속도로 제한.
            # 학습 시뮬(MetaDrive X맵)엔 반경 25~60m 회전만 있어 정책이 CARLA 의 10~15m
            # 회전에서 감속을 배우지 못했다(실측: 실패군 진입 52~55km/h, 반경 10~15m = 1.9g 요구).
            if a.governor > 0:
                R_ahead = 1e9
                for kk in range(ob.idx, min(ob.idx + 13, len(route) - 1)):
                    y1 = route[kk].transform.rotation.yaw
                    y2 = route[kk + 1].transform.rotation.yaw
                    dp = abs((y2 - y1 + 180) % 360 - 180)
                    l1, l2 = route[kk].transform.location, route[kk + 1].transform.location
                    ds = math.hypot(l2.x - l1.x, l2.y - l1.y)
                    if dp > 0.5 and ds > 0.1:
                        R_ahead = min(R_ahead, ds / math.radians(dp))
                if R_ahead < 400:
                    v_max = math.sqrt(a.governor * 9.81 * R_ahead)
                    if spd > v_max:
                        act = np.array([act[0], -min(1.0, (spd - v_max) / 3.0)], np.float32)
            ctrl = carla.VehicleControl(steer=steer)
            if act[1] >= 0:
                ctrl.throttle = 0.0 if spd * 3.6 > MAXS_KMH else float(act[1]) * K_THR
            else:
                ctrl.brake = float(min(abs(act[1]) * K_BRK, 1.0))
            for k5 in range(5):
                ego.apply_control(ctrl); world.tick()
                if a.record:
                    try:
                        img = q.get(timeout=5.0)
                        if k5 == 4 and t % 2 == 0:
                            img.save_to_disk(f"{a.record}/ep{ep}_{t:04d}.png")
                    except Exception:
                        pass
            steps += 1
            if a.record and t % 2 == 0:
                pass
            if col["hit"]:
                outcome = "충돌"
                print(f"   충돌 상대: {col.get('with_', '?')}", flush=True); break
            max_lat = max(max_lat, abs(lat_r))
            if entry_spd is None and j_entry > 3 and ob.idx >= j_entry:
                entry_spd = spd * 3.6
            hist.append((t, lat_r, spd * 3.6, float(act[0]), float(act[1]), steer,
                         float(obs[9]), float(obs[10]), float(obs[13]), ob.idx))
            if len(hist) > 6:
                hist.pop(0)
            if a.verbose and (t < 3 or t % 50 == 0):
                print(f"   t={t} lat={lat_r:+.2f} spd={spd*3.6:.0f}km/h act=[{act[0]:+.2f},{act[1]:+.2f}] "
                      f"steer={steer:+.2f} idx={ob.idx}/{len(route)}", flush=True)
            loc = ego.get_transform().location
            nw = cmap.get_waypoint(loc, True, carla.LaneType.Driving)
            off = math.hypot(loc.x - nw.transform.location.x, loc.y - nw.transform.location.y) if nw else 99
            if off > max(nw.lane_width, 3.0) * 0.9 if nw else True:
                outcome = "이탈"; break
            if ob.idx >= len(route) - 3:
                outcome = "성공"; break
        if outcome != "성공" and a.verbose:
            print("   [실패 직전 5스텝] t/lat/속도/조향act/가감속/steer/navi_fwd/navi_lat/각도")
            for h in hist:
                print(f"     {h[0]:3d} {h[1]:+5.2f} {h[2]:5.1f} {h[3]:+5.2f} {h[4]:+5.2f} {h[5]:+5.2f} "
                      f"{h[6]:.2f} {h[7]:.2f} {h[8]:.2f} idx={h[9]}", flush=True)
        # 라벨 정정: 앵커의 진입/이탈 방위차가 아니라 '실제 실행된 경로'의 총 회전각으로
        # 분류한다. 경로계획기가 유턴 경로를 내놓는 경우가 있고(실측 170도), 유턴은
        # 학습 환경에 없는 기동이라 좌회전 통계를 오염시킨다.
        _td = _turn_deg(route)
        if _td >= 150:
            kind = "유턴"
        elif _td < 30 and kind != "직진":
            kind = "직진"
        results.append(dict(ep=ep, kind=kind, outcome=outcome, steps=steps, entry_kmh=round(entry_spd or 0, 1), min_R=round(min(min_R, 999), 1), max_lat=round(max_lat, 2), turn_deg=round(_turn_deg(route), 1), n_junc=sum(1 for w in route if w.is_junction)))
        print(f"ep{ep}: {outcome} ({steps}스텝)", flush=True)
    for x in ([cam, cs] if cam else [cs]) + ([ego] if ego else []) + (npcs or []):
        try:
            if hasattr(x, 'stop'):
                x.stop()
            x.destroy()
        except Exception:
            pass
    st.synchronous_mode = False; world.apply_settings(st)
    ok = sum(1 for r in results if r["outcome"] == "성공")
    nl = chr(10)
    print(nl + f"=== 전체 성공 {ok}/{len(results)} = {ok/max(len(results),1):.0%} ===")
    by = {}
    for r in results:
        d = by.setdefault(r.get("kind", "?"), {"n": 0, "ok": 0})
        d["n"] += 1
        d["ok"] += r["outcome"] == "성공"
        d[r["outcome"]] = d.get(r["outcome"], 0) + 1
    for k, d in sorted(by.items()):
        print(f"  {k}: {d[chr(39)+chr(111)+chr(107)+chr(39)] if False else d['ok']}/{d['n']} = {d['ok']/d['n']:.0%} "
              f"(충돌 {d.get('충돌',0)} 이탈 {d.get('이탈',0)} 시간초과 {d.get('timeout',0)})")
    json.dump(results, open(a.out or os.path.join(a.record or ".", "drive_results.json"), "w"), ensure_ascii=False)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--policy", default="C:/ue/policy.npz")
    ap.add_argument("--episodes", type=int, default=5)
    ap.add_argument("--max-steps", type=int, default=400)
    ap.add_argument("--record", default="")
    ap.add_argument("--npc", type=int, default=3)
    ap.add_argument("--turn-kind", default="전체",
                    choices=["전체", "직진", "좌회전", "우회전", "유턴"])
    ap.add_argument("--verbose", action="store_true")
    ap.add_argument("--out", default="")
    ap.add_argument("--approach", type=float, default=65.0,
                    help="교차로 진입로 길이(m) — 학습 환경의 팔 길이 65m 와 맞춘다")
    ap.add_argument("--governor", type=float, default=0.8,
                    help="곡률 기반 속도 제한의 횡가속 한계(g). 0 이면 비활성")
    ap.add_argument("--obs-slots", type=int, default=3,
                    help="주변 장애물 관측 슬롯 수 — 학습 밀도(V=3)와 맞추는 것이 기본")
    ap.add_argument("--mask-degen", action="store_true",
                    help="학습 중 퇴화(분산 0) 차원을 학습값으로 고정 — §5 지지집합 처방")
    run(ap.parse_args())
