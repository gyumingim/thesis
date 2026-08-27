"""CARLA 0.10 실사 재현 — 경량 RL 환경의 롤아웃을 CARLA 교차로에 옮겨 촬영 (2026-08-28).

우리 시뮬 좌표(m, yaw CCW)를 CARLA 4거리 교차로에 정렬해 ego/NPC 를 프레임마다
텔레포트하고, 추격 카메라 + 탑다운 카메라로 PNG 를 찍는다. 물리는 끈다(궤적 재현).
실행: py -3.12 viz_carla_replay.py --rollout C:/carla/rollout.json --out C:/carla/replay
"""
import argparse
import json
import math
import os
import queue

import carla


def pick_junction(world):
    """가장 큰 4거리 교차로와 기준 방향을 고른다."""
    cmap = world.get_map()
    best = None
    seen = set()
    for wp in cmap.generate_waypoints(4.0):
        j = wp.get_junction()
        if j is None or j.id in seen:
            continue
        seen.add(j.id)
        bb = j.bounding_box
        area = bb.extent.x * bb.extent.y
        arms = len(j.get_waypoints(carla.LaneType.Driving))
        if arms >= 8 and (best is None or area > best[0]):
            entry = j.get_waypoints(carla.LaneType.Driving)[0][0]
            best = (area, bb.location, entry.transform.rotation.yaw, j.id, arms)
    return best


def to_carla(x, y, yaw, center, theta_deg, sim_center):
    """시뮬(m, CCW) → CARLA(좌표계 y 반전, yaw 시계방향 도)."""
    th = math.radians(theta_deg)
    dx, dy = x - sim_center[0], -(y - sim_center[1])      # y 반전
    cx = center.x + dx * math.cos(th) - dy * math.sin(th)
    cy = center.y + dx * math.sin(th) + dy * math.cos(th)
    cyaw = theta_deg - math.degrees(yaw)
    return carla.Transform(carla.Location(x=cx, y=cy, z=center.z + 0.3),
                           carla.Rotation(yaw=cyaw))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rollout", default="C:/carla/rollout.json")
    ap.add_argument("--out", default="C:/carla/replay")
    ap.add_argument("--episode", type=int, default=0)
    ap.add_argument("--width", type=int, default=1280)
    ap.add_argument("--height", type=int, default=720)
    ap.add_argument("--stride", type=int, default=2, help="N 프레임마다 촬영")
    a = ap.parse_args()

    data = json.load(open(a.rollout))
    ep = data["episodes"][a.episode]
    frames = ep["frames"]
    sim_center = data["meta"]["center"]
    os.makedirs(a.out, exist_ok=True)

    client = carla.Client("127.0.0.1", 2000)
    client.set_timeout(60.0)
    world = client.get_world()
    st = world.get_settings()
    st.synchronous_mode = True
    st.fixed_delta_seconds = data["meta"].get("dt", 0.1)
    world.apply_settings(st)

    jn = pick_junction(world)
    if jn is None:
        print("교차로 탐색 실패"); return
    _, center, theta, jid, arms = jn
    print(f"교차로 id={jid} arms={arms} center=({center.x:.1f},{center.y:.1f}) yaw={theta:.1f}")

    bl = world.get_blueprint_library()
    ego_bp = bl.filter("vehicle.*")[0]
    npc_bps = [b for b in bl.filter("vehicle.*")][1:6]
    max_npc = max(len(f["npc"]) for f in frames)

    actors = []
    ego_tf = to_carla(*frames[0]["ego"][:3], center, theta, sim_center)
    ego = world.try_spawn_actor(ego_bp, ego_tf)
    if ego is None:
        ego_tf.location.z += 1.0
        ego = world.spawn_actor(ego_bp, ego_tf)
    ego.set_simulate_physics(False)
    actors.append(ego)
    npcs = []
    for k in range(max_npc):
        tf = carla.Transform(carla.Location(x=center.x + 200 + k * 5, y=center.y, z=center.z + 0.3))
        v = world.try_spawn_actor(npc_bps[k % len(npc_bps)], tf)
        if v:
            v.set_simulate_physics(False)
            npcs.append(v); actors.append(v)

    cam_bp = bl.find("sensor.camera.rgb")
    cam_bp.set_attribute("image_size_x", str(a.width))
    cam_bp.set_attribute("image_size_y", str(a.height))
    cam_bp.set_attribute("fov", "90")
    chase = world.spawn_actor(cam_bp, carla.Transform(
        carla.Location(x=-7.0, z=3.6), carla.Rotation(pitch=-13)), attach_to=ego)
    top = world.spawn_actor(cam_bp, carla.Transform(
        carla.Location(x=center.x, y=center.y, z=center.z + 55),
        carla.Rotation(pitch=-90, yaw=theta)))
    actors += [chase, top]
    qc, qt = queue.Queue(), queue.Queue()
    chase.listen(qc.put); top.listen(qt.put)

    try:
        for i, fr in enumerate(frames):
            ego.set_transform(to_carla(*fr["ego"][:3], center, theta, sim_center))
            for k, v in enumerate(npcs):
                if k < len(fr["npc"]):
                    v.set_transform(to_carla(*fr["npc"][k][:3], center, theta, sim_center))
                else:
                    v.set_transform(carla.Transform(
                        carla.Location(x=center.x + 300 + k * 5, y=center.y, z=center.z)))
            world.tick()
            ic, it = qc.get(timeout=20.0), qt.get(timeout=20.0)
            if i % a.stride == 0:
                ic.save_to_disk(f"{a.out}/chase_{i:04d}.png")
                it.save_to_disk(f"{a.out}/top_{i:04d}.png")
        print("촬영 완료:", len(frames) // a.stride, "쌍 →", a.out)
    finally:
        chase.stop(); top.stop()
        for x in actors:
            try: x.destroy()
            except Exception: pass
        st.synchronous_mode = False
        world.apply_settings(st)


if __name__ == "__main__":
    main()
