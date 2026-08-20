"""CARLA 0.10.0 기반 인지 데이터 생성기 v0 (5080에서 실행).

정적 장면 방식: 스폰포인트에 차량 K대 배치 → 카메라 1프레임 캡처 → 50m 내 차량의
카메라 기준 상대 3D 위치·요각을 JSON 저장 → 차량 회수 → 다음 프레임.
출력 스키마는 PerceptGen(scene_build.py)과 동일 — 두 데이터 소스를 섞어 쓸 수 있게.

실행: py -3.12 carla_datagen.py <프레임수>
"""
import carla
import json
import math
import os
import queue
import random
import sys

OUT = r"C:\carla\out"
W, H, FOV = 1280, 720, 90.0
K_VEHICLES = 10
DETECT_M = 50.0
CAM_Z = 1.5


def rel_in_cam(cam_tf, loc):
    """월드 좌표 → 카메라 로컬 (x=전방, y=우측, z=상방, m)."""
    inv = cam_tf.get_inverse_matrix()
    p = [loc.x, loc.y, loc.z, 1.0]
    out = [sum(inv[r][c] * p[c] for c in range(4)) for r in range(3)]
    return out[0], out[1], out[2]


def main():
    n_frames = int(sys.argv[1]) if len(sys.argv) > 1 else 10
    os.makedirs(OUT, exist_ok=True)
    rng = random.Random(7)

    client = carla.Client("127.0.0.1", 2000)
    client.set_timeout(60.0)
    world = client.get_world()

    settings = world.get_settings()
    settings.synchronous_mode = True
    settings.fixed_delta_seconds = 0.05
    world.apply_settings(settings)

    bl = world.get_blueprint_library()
    vehicle_bps = bl.filter("vehicle.*")
    cam_bp = bl.find("sensor.camera.rgb")
    cam_bp.set_attribute("image_size_x", str(W))
    cam_bp.set_attribute("image_size_y", str(H))
    cam_bp.set_attribute("fov", str(FOV))

    sps = world.get_map().get_spawn_points()
    print(f"spawn points: {len(sps)}, vehicle bps: {len(vehicle_bps)}")

    q = queue.Queue()
    cam = None
    for i in range(n_frames):
        rng.seed(500 + i)
        cam_sp = rng.choice(sps)
        cam_tf = carla.Transform(
            carla.Location(cam_sp.location.x, cam_sp.location.y, cam_sp.location.z + CAM_Z),
            cam_sp.rotation,
        )
        # 카메라 주변 스폰포인트에 차량 배치
        near = [s for s in sps if s.location.distance(cam_sp.location) < 70.0
                and s.location.distance(cam_sp.location) > 8.0]
        rng.shuffle(near)
        vehicles = []
        for s in near[:K_VEHICLES]:
            bp = rng.choice(list(vehicle_bps))
            v = world.try_spawn_actor(bp, s)
            if v is not None:
                vehicles.append(v)

        cam = world.spawn_actor(cam_bp, cam_tf)
        cam.listen(q.put)
        # 결함수정(2026-08-20): 물리 켠 채 몇 틱 → 차량 노면 안착 후 고정,
        # 워밍업 12틱으로 자동노출 수렴 (v0에서 어두운 프레임/부양 차량 발견)
        for v in vehicles:
            v.set_simulate_physics(True)
        for _ in range(6):
            world.tick()
        for v in vehicles:
            v.set_simulate_physics(False)
        for _ in range(6):
            world.tick()
        img = None
        while not q.empty():
            img = q.get()
        if img is None:
            img = q.get(timeout=10.0)
        img.save_to_disk(os.path.join(OUT, f"frame_{i}.png"))

        labels = []
        for v in vehicles:
            loc = v.get_transform().location
            fx, fy, fz = rel_in_cam(cam_tf, loc)
            d = math.sqrt(fx * fx + fy * fy)
            if d < DETECT_M and fx > 0.5:          # 전방 50m 내만 라벨
                bb = v.bounding_box
                labels.append(dict(
                    type=v.type_id,
                    relative_position_m=dict(x=fx, y=fy, z=fz),
                    relative_yaw_deg=(v.get_transform().rotation.yaw - cam_tf.rotation.yaw + 180) % 360 - 180,
                    size_m=dict(l=2 * bb.extent.x, w=2 * bb.extent.y, h=2 * bb.extent.z),
                    distance_m=d,
                ))
        with open(os.path.join(OUT, f"frame_{i}.json"), "w") as f:
            json.dump(dict(frame=i, camera=dict(fov_deg=FOV, width=W, height=H,
                                                z_offset_m=CAM_Z), vehicles=labels), f, indent=2)
        print(f"frame_{i}: 차량 {len(vehicles)}대 배치, 라벨 {len(labels)}건")

        cam.stop(); cam.destroy(); cam = None
        for v in vehicles:
            v.destroy()

    settings.synchronous_mode = False
    world.apply_settings(settings)
    print("done")


if __name__ == "__main__":
    main()
