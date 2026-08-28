"""CARLA 분할화면 촬영 — K개 에피소드를 서로 다른 교차로에서 동시 재현 (2026-08-28).

각 에피소드를 별도 교차로에 정렬해 ego/NPC 를 동시에 텔레포트하고, 에피소드마다
추격 카메라 1대로 같은 틱에 촬영한다(= 진짜 병렬 캡처). 프레임별 상태·행동 로그를
JSON 으로 함께 남겨 대시보드 단계(tools/viz_dashboard.py)에서 오버레이한다.

실행: py -3.12 viz_carla_multi.py --rollout C:/carla/rollout_multi.json --out C:/carla/multi
"""
import argparse
import json
import math
import os
import queue

import carla


def junctions(world, k):
    """4거리 후보를 크기순으로 k 개 (교차로 id 중복 제거)."""
    cmap = world.get_map()
    cand, seen = [], set()
    for wp in cmap.generate_waypoints(4.0):
        j = wp.get_junction()
        if j is None or j.id in seen:
            continue
        seen.add(j.id)
        wps = j.get_waypoints(carla.LaneType.Driving)
        if len(wps) < 8:
            continue
        bb = j.bounding_box
        cand.append((bb.extent.x * bb.extent.y, bb.location,
                     wps[0][0].transform.rotation.yaw, j.id))
    cand.sort(key=lambda c: -c[0])
    return cand[:k]


def cam_K(w, h, fov):
    f = w / (2.0 * math.tan(math.radians(fov) / 2.0))
    return [[f, 0, w / 2.0], [0, f, h / 2.0], [0, 0, 1.0]]


def bbox_2d(actor, cam, K, w, h, max_m=70.0):
    """액터의 3D 바운딩박스를 카메라 이미지 2D 박스로 투영 (없으면 None)."""
    cam_tf = cam.get_transform()
    inv = cam_tf.get_inverse_matrix()
    verts = actor.bounding_box.get_world_vertices(actor.get_transform())
    pts = []
    for v in verts:
        p = [v.x, v.y, v.z, 1.0]
        c = [sum(inv[r][k] * p[k] for k in range(4)) for r in range(3)]   # UE: x전방 y우 z상
        if c[0] <= 0.5 or c[0] > max_m:
            continue
        u = K[0][0] * (c[1] / c[0]) + K[0][2]
        vv = K[1][1] * (-c[2] / c[0]) + K[1][2]
        pts.append((u, vv))
    if len(pts) < 4:
        return None
    xs, ys = [q[0] for q in pts], [q[1] for q in pts]
    x1, y1, x2, y2 = max(min(xs), 0), max(min(ys), 0), min(max(xs), w), min(max(ys), h)
    if x2 - x1 < 8 or y2 - y1 < 8:
        return None
    return [round(x1, 1), round(y1, 1), round(x2, 1), round(y2, 1)]


def level_car_bbs(world):
    """맵에 배치된 정적 차량(주차 차량 등)의 월드 바운딩박스 — GT 에 포함해야 공정하다."""
    out = []
    for lab in ("Car", "Truck", "Bus"):
        try:
            out += list(world.get_level_bbs(getattr(carla.CityObjectLabel, lab)))
        except Exception:
            pass
    return out


def bbox_2d_from_bb(bb, cam, K, w, h, max_m=70.0):
    inv = cam.get_transform().get_inverse_matrix()
    try:
        verts = bb.get_world_vertices(carla.Transform())
    except Exception:
        return None
    pts = []
    for v in verts:
        p = [v.x, v.y, v.z, 1.0]
        c = [sum(inv[r][k] * p[k] for k in range(4)) for r in range(3)]
        if c[0] <= 0.5 or c[0] > max_m:
            continue
        pts.append((K[0][0] * (c[1] / c[0]) + K[0][2], K[1][1] * (-c[2] / c[0]) + K[1][2]))
    if len(pts) < 4:
        return None
    xs, ys = [q[0] for q in pts], [q[1] for q in pts]
    x1, y1, x2, y2 = max(min(xs), 0), max(min(ys), 0), min(max(xs), w), min(max(ys), h)
    if x2 - x1 < 8 or y2 - y1 < 8:
        return None
    return [round(x1, 1), round(y1, 1), round(x2, 1), round(y2, 1)]


def to_carla(x, y, yaw, center, theta_deg, sim_center, dz=0.3):
    th = math.radians(theta_deg)
    dx, dy = x - sim_center[0], -(y - sim_center[1])
    return carla.Transform(
        carla.Location(x=center.x + dx * math.cos(th) - dy * math.sin(th),
                       y=center.y + dx * math.sin(th) + dy * math.cos(th),
                       z=center.z + dz),
        carla.Rotation(yaw=theta_deg - math.degrees(yaw)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rollout", default="C:/carla/rollout_multi.json")
    ap.add_argument("--out", default="C:/carla/multi")
    ap.add_argument("--width", type=int, default=640)
    ap.add_argument("--height", type=int, default=360)
    ap.add_argument("--stride", type=int, default=1)
    a = ap.parse_args()

    data = json.load(open(a.rollout))
    eps = data["episodes"]
    sim_center = data["meta"]["center"]
    os.makedirs(a.out, exist_ok=True)

    client = carla.Client("127.0.0.1", 2000); client.set_timeout(60.0)
    world = client.get_world()
    st = world.get_settings()
    st.synchronous_mode = True
    st.fixed_delta_seconds = data["meta"].get("dt", 0.1)
    world.apply_settings(st)
    for v in world.get_actors().filter("vehicle.*"):
        try: v.destroy()
        except Exception: pass

    js = junctions(world, len(eps))
    if len(js) < len(eps):
        print(f"교차로 부족: {len(js)} < {len(eps)} — 있는 만큼만"); eps = eps[:len(js)]
    print("교차로:", [(j[3], round(j[2], 1)) for j in js])

    bl = world.get_blueprint_library()
    ego_bp = (bl.filter("vehicle.dodge.charger") or bl.filter("vehicle.lincoln.mkz") or bl.filter("vehicle.*"))[0]
    if ego_bp.has_attribute("color"):
        ego_bp.set_attribute("color", "20,90,230")
    npc_pool = [b for b in bl.filter("vehicle.*")
                if not any(x in b.id for x in ("bike", "motor", "firetruck", "carlacola", "ambulance", "dodge.charger"))]
    VEH_TAGS = (14, 15, 16)      # CARLA 0.10 시맨틱 태그: 차/트럭/버스 (실측 확인)
    seg_bp = bl.find("sensor.camera.semantic_segmentation")
    for at, vv in (("image_size_x", a.width), ("image_size_y", a.height), ("fov", 95)):
        seg_bp.set_attribute(at, str(vv))
    cam_bp = bl.find("sensor.camera.rgb")
    cam_bp.set_attribute("image_size_x", str(a.width))
    cam_bp.set_attribute("image_size_y", str(a.height))
    cam_bp.set_attribute("fov", "95")

    actors, lanes = [], []
    for k, (ep, jn) in enumerate(zip(eps, js)):
        _, center, theta, jid = jn
        f0 = ep["frames"][0]
        ego = None
        for dz in (0.3, 2.0, 8.0, 25.0):
            ego = world.try_spawn_actor(ego_bp, to_carla(*f0["ego"][:3], center, theta, sim_center, dz))
            if ego:
                break
        if ego is None:
            print(f"ep{k} ego 스폰 실패"); continue
        ego.set_simulate_physics(False)
        npcs = []
        for m in range(max(len(f["npc"]) for f in ep["frames"])):
            v = None
            for dz in (0.3, 4.0, 15.0):
                v = world.try_spawn_actor(npc_pool[(k + m) % len(npc_pool)],
                                          carla.Transform(carla.Location(center.x + 250 + m * 6,
                                                                         center.y + k * 8, center.z + dz)))
                if v:
                    break
            if v:
                v.set_simulate_physics(False); npcs.append(v)
        cam = world.spawn_actor(cam_bp, carla.Transform(
            carla.Location(x=-6.5, z=3.2), carla.Rotation(pitch=-12)), attach_to=ego)
        seg = world.spawn_actor(seg_bp, carla.Transform(
            carla.Location(x=-6.5, z=3.2), carla.Rotation(pitch=-12)), attach_to=ego)
        q, qs = queue.Queue(), queue.Queue()
        cam.listen(q.put); seg.listen(qs.put)
        lanes.append(dict(k=k, ep=ep, center=center, theta=theta, ego=ego, npcs=npcs,
                          cam=cam, q=q, seg=seg, qs=qs))
        actors += [ego, cam, seg] + npcs

    LEVEL_BBS = level_car_bbs(world)
    print("레벨 정적 차량 박스:", len(LEVEL_BBS))
    n_frames = max(len(l["ep"]["frames"]) for l in lanes)
    logs = {f"ep{l['k']}": [] for l in lanes}
    try:
        for i in range(n_frames):
            for l in lanes:
                frs = l["ep"]["frames"]
                fr = frs[min(i, len(frs) - 1)]
                l["ego"].set_transform(to_carla(*fr["ego"][:3], l["center"], l["theta"], sim_center))
                for m, v in enumerate(l["npcs"]):
                    if m < len(fr["npc"]):
                        v.set_transform(to_carla(*fr["npc"][m][:3], l["center"], l["theta"], sim_center))
                    else:
                        v.set_transform(carla.Transform(carla.Location(
                            l["center"].x + 300 + m * 6, l["center"].y, l["center"].z)))
            world.tick()
            for l in lanes:
                img = l["q"].get(timeout=20.0)
                simg = l["qs"].get(timeout=20.0)
                frs = l["ep"]["frames"]
                fr = frs[min(i, len(frs) - 1)]
                if i % a.stride == 0:
                    img.save_to_disk(f"{a.out}/ep{l['k']}_{i:04d}.png")
                    K = cam_K(a.width, a.height, 95.0)
                    gt = [b for b in (bbox_2d(v, l["cam"], K, a.width, a.height)
                                      for v in l["npcs"]) if b]
                    import numpy as _np
                    tags = _np.frombuffer(simg.raw_data, dtype=_np.uint8).reshape(
                        simg.height, simg.width, 4)[:, :, 2]
                    cam_loc = l["cam"].get_transform().location
                    for bb in LEVEL_BBS:
                        if bb.location.distance(cam_loc) > 70:
                            continue
                        qb = bbox_2d_from_bb(bb, l["cam"], K, a.width, a.height)
                        if qb:
                            gt.append(qb)
                    # 가시성 필터: 박스 안에 실제 차량 픽셀이 있어야 GT 로 인정 (가림 제거)
                    vis = []
                    for b in gt:
                        x1, y1, x2, y2 = (int(b[0]), int(b[1]), int(b[2]), int(b[3]))
                        sub = tags[max(y1, 0):max(y2, 1), max(x1, 0):max(x2, 1)]
                        if sub.size < 200:
                            continue
                        frac = float(_np.isin(sub, VEH_TAGS).mean())
                        if frac >= 0.18:
                            vis.append(b)
                    gt = vis
                    logs[f"ep{l['k']}"].append(dict(gt=gt,
                        i=i, speed=fr["ego"][3], act=fr.get("act", [0, 0]),
                        rew=fr.get("rew", 0.0), n_npc=fr.get("n_npc", len(fr["npc"])),
                        outcome=l["ep"]["outcome"],
                        done=(i >= len(frs) - 1)))
        json.dump(dict(meta=data["meta"], logs=logs), open(f"{a.out}/logs.json", "w"))
        print("촬영 완료:", n_frames, "프레임 ×", len(lanes), "레인 →", a.out)
    finally:
        for l in lanes:
            for key in ("cam", "seg"):
                try: l[key].stop()
                except Exception: pass
        for x in actors:
            try: x.destroy()
            except Exception: pass
        st.synchronous_mode = False
        world.apply_settings(st)


if __name__ == "__main__":
    main()
