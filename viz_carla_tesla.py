"""테슬라식 8카메라 리그 촬영 — 카메라만 쓰는 인지 구성의 기반 (2026-08-28).

Model 3 배치 근사: 전방 3(광각/표준/망원 대용), B필러 좌우, 후측방 좌우, 후방 1.
롤아웃을 차선 앵커로 재현하며 8채널을 동기 캡처하고, 각 카메라의 외부/내부 파라미터를
JSON 으로 남긴다(카메라 기반 BEV 복원에 필요). 라이다·레이더 없음.

실행: py -3.12 viz_carla_tesla.py --rollout C:/carla/rollout_multi.json --out C:/carla/tesla
"""
import argparse
import json
import math
import os
import queue

import carla

# (이름, x, y, z, yaw, fov) — 차량 기준 로컬 (m, 도)
RIG = [
    ("front_wide",  1.35,  0.00, 1.30,    0.0, 120.0),
    ("front_main",  1.35,  0.00, 1.30,    0.0,  60.0),
    ("front_narrow", 1.35, 0.00, 1.30,    0.0,  35.0),
    ("pillar_left", 0.95, -0.90, 1.15,  -55.0,  90.0),
    ("pillar_right", 0.95, 0.90, 1.15,   55.0,  90.0),
    ("rear_left",  -0.20, -0.95, 1.05, -115.0,  90.0),
    ("rear_right", -0.20,  0.95, 1.05,  115.0,  90.0),
    ("rear",       -2.20,  0.00, 1.10,  180.0, 110.0),
]


def approach_anchor(world, j, back_m=65.0):
    pairs = j.get_waypoints(carla.LaneType.Driving)
    best = None
    for win, wout in pairs:
        dy = abs((win.transform.rotation.yaw - wout.transform.rotation.yaw + 180) % 360 - 180)
        if dy > 20:
            continue
        prevs = win.previous(back_m)
        if prevs and (best is None or dy < best[0]):
            best = (dy, prevs[0])
    if best is None:
        for win, _ in pairs:
            prevs = win.previous(back_m * 0.6)
            if prevs:
                return prevs[0].transform
        return None
    return best[1].transform


def best_junction(world):
    cmap = world.get_map()
    seen, best = set(), None
    for wp in cmap.generate_waypoints(4.0):
        j = wp.get_junction()
        if j is None or j.id in seen:
            continue
        seen.add(j.id)
        wps = j.get_waypoints(carla.LaneType.Driving)
        if len(wps) < 8:
            continue
        a = j.bounding_box.extent.x * j.bounding_box.extent.y
        anc = approach_anchor(world, j)
        if anc and (best is None or a > best[0]):
            best = (a, anc, j.id)
    return best


def to_carla(x, y, yaw, anchor, sim_ref, dz=0.3):
    th = math.radians(anchor.rotation.yaw)
    dx, dy = x - sim_ref[0], -(y - sim_ref[1])
    return carla.Transform(
        carla.Location(x=anchor.location.x + dx * math.cos(th) - dy * math.sin(th),
                       y=anchor.location.y + dx * math.sin(th) + dy * math.cos(th),
                       z=anchor.location.z + dz),
        carla.Rotation(yaw=anchor.rotation.yaw - math.degrees(yaw)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rollout", default="C:/carla/rollout_multi.json")
    ap.add_argument("--out", default="C:/carla/tesla")
    ap.add_argument("--episode", type=int, default=0)
    ap.add_argument("--width", type=int, default=480)
    ap.add_argument("--height", type=int, default=270)
    ap.add_argument("--stride", type=int, default=3)
    a = ap.parse_args()

    data = json.load(open(a.rollout))
    ep = data["episodes"][a.episode]
    frames = ep["frames"]
    os.makedirs(a.out, exist_ok=True)

    client = carla.Client("127.0.0.1", 2000); client.set_timeout(60.0)
    world = client.get_world()
    st = world.get_settings(); st.synchronous_mode = True
    st.fixed_delta_seconds = data["meta"].get("dt", 0.1)
    world.apply_settings(st)
    for v in world.get_actors().filter("vehicle.*"):
        try: v.destroy()
        except Exception: pass

    jb = best_junction(world)
    if jb is None:
        print("교차로 없음"); return
    _, anchor, jid = jb
    print("교차로", jid, "앵커", round(anchor.rotation.yaw, 1))

    bl = world.get_blueprint_library()
    ego_bp = (bl.filter("vehicle.dodge.charger") or bl.filter("vehicle.*"))[0]
    if ego_bp.has_attribute("color"):
        ego_bp.set_attribute("color", "20,90,230")
    npc_pool = [b for b in bl.filter("vehicle.*")
                if not any(x in b.id for x in ("firetruck", "carlacola", "ambulance", "dodge.charger"))]

    sim_ref = [frames[0]["ego"][0], frames[0]["ego"][1]]
    ego = None
    for dz in (0.3, 2.0, 8.0):
        ego = world.try_spawn_actor(ego_bp, to_carla(*frames[0]["ego"][:3], anchor, sim_ref, dz))
        if ego:
            break
    if ego is None:
        print("ego 스폰 실패"); return
    ego.set_simulate_physics(False)

    npcs = []
    for m in range(max(len(f["npc"]) for f in frames)):
        for dz in (0.3, 4.0):
            v = world.try_spawn_actor(npc_pool[m % len(npc_pool)], carla.Transform(
                carla.Location(anchor.location.x + 200 + m * 6, anchor.location.y, anchor.location.z + dz)))
            if v:
                v.set_simulate_physics(False); npcs.append(v); break

    cam_bp = bl.find("sensor.camera.rgb")
    cam_bp.set_attribute("image_size_x", str(a.width))
    cam_bp.set_attribute("image_size_y", str(a.height))
    cams, qs, calib = {}, {}, {}
    for name, x, y, z, yaw, fov in RIG:
        bp = bl.find("sensor.camera.rgb")
        bp.set_attribute("image_size_x", str(a.width))
        bp.set_attribute("image_size_y", str(a.height))
        bp.set_attribute("fov", str(fov))
        c = world.spawn_actor(bp, carla.Transform(carla.Location(x=x, y=y, z=z),
                                                  carla.Rotation(yaw=yaw)), attach_to=ego)
        q = queue.Queue(); c.listen(q.put)
        cams[name], qs[name] = c, q
        f = a.width / (2.0 * math.tan(math.radians(fov) / 2.0))
        calib[name] = dict(x=x, y=y, z=z, yaw=yaw, fov=fov, fx=f, fy=f,
                           cx=a.width / 2.0, cy=a.height / 2.0, w=a.width, h=a.height)
    json.dump(dict(rig=calib, dt=st.fixed_delta_seconds), open(f"{a.out}/calib.json", "w"), indent=1)

    logs = []
    try:
        for i, fr in enumerate(frames):
            ego.set_transform(to_carla(*fr["ego"][:3], anchor, sim_ref))
            for m, v in enumerate(npcs):
                if m < len(fr["npc"]):
                    v.set_transform(to_carla(*fr["npc"][m][:3], anchor, sim_ref))
                else:
                    v.set_transform(carla.Transform(carla.Location(
                        anchor.location.x + 300 + m * 6, anchor.location.y, anchor.location.z)))
            world.tick()
            imgs = {n: qs[n].get(timeout=25.0) for n in cams}
            if i % a.stride:
                continue
            for n, im in imgs.items():
                im.save_to_disk(f"{a.out}/{n}_{i:04d}.png")
            # GT: ego 기준 상대 좌표(전방 x, 좌 y) — 카메라 기반 복원의 정답
            etf = ego.get_transform()
            inv = etf.get_inverse_matrix()
            gt = []
            for v in npcs:
                l = v.get_location()
                p = [l.x, l.y, l.z, 1.0]
                c = [sum(inv[r][k] * p[k] for k in range(4)) for r in range(3)]
                if abs(c[0]) < 80 and abs(c[1]) < 40:
                    gt.append([round(c[0], 2), round(-c[1], 2)])      # (전방, 좌+)
            logs.append(dict(i=i, ego=fr["ego"], act=fr.get("act", [0, 0]),
                             rew=fr.get("rew", 0.0), gt_bev=gt, outcome=ep["outcome"]))
        json.dump(dict(meta=data["meta"], logs=logs), open(f"{a.out}/logs.json", "w"))
        print("촬영:", len(logs), "프레임 ×", len(cams), "카메라 →", a.out)
    finally:
        for c in cams.values():
            try: c.stop(); c.destroy()
            except Exception: pass
        for v in [ego] + npcs:
            try: v.destroy()
            except Exception: pass
        st.synchronous_mode = False; world.apply_settings(st)


if __name__ == "__main__":
    main()
