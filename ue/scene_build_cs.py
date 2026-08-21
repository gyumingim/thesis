"""CitySample 프로젝트용 장면 생성기 — 큐브 대신 City Sample 실차 메시 사용.

scene_build.py(PerceptGen)와 동일 구조/출력 스키마. 차이:
- 차량 = /Game/Vehicle/*/Mesh/SM_<본체>.uasset (바퀴 포함 본체 메시 자동 탐색)
- 크기 라벨 = 메시 바운드에서 실측 (큐브 고정치 대신)
출력: /Game/GenScenes/scene_i + C:/ue/out_cs/scene_i.json
"""
import unreal
import sys
import os
import json
import math
import random

LEVEL_DIR = "/Game/GenScenes"
OUTPUT_DIR = r"C:\ue\out_cs"
NUM_VEHICLES = 8
MIN_DIST_M, MAX_DIST_M = 6.0, 50.0
SECTOR_HALF_ANGLE_DEG = 35.0
CAMERA_LOCATION_CM = (0.0, 0.0, 150.0)
CAMERA_YAW_DEG = 0.0
FLOOR_EDGE_M = 200.0
PLANE_MESH_PATH = "/Engine/BasicShapes/Plane"
GRAY_MAT = "/Engine/BasicShapes/BasicShapeMaterial"

EXCLUDE = ("Wheel", "Brake", "Door", "MotionBlur", "Trans", "No_Wheel", "Steering",
           "Caliper", "Rotor", "Glass", "Mirror", "Bumper", "Hood", "Trunk", "seat", "Seat")


def find_vehicle_meshes():
    assets = unreal.EditorAssetLibrary.list_assets("/Game/Vehicle", recursive=True, include_folder=False)
    out = []
    for a in assets:
        name = a.split("/")[-1].split(".")[0]
        if not name.startswith("SM_veh"):
            continue
        if any(k in name for k in EXCLUDE):
            continue
        out.append(a)
    return sorted(set(out))


def world_to_camera_local_m(t):
    dx = t[0] - CAMERA_LOCATION_CM[0]
    dy = t[1] - CAMERA_LOCATION_CM[1]
    dz = t[2] - CAMERA_LOCATION_CM[2]
    y = math.radians(CAMERA_YAW_DEG)
    c, s = math.cos(y), math.sin(y)
    return (dx * c + dy * s) / 100.0, (-dx * s + dy * c) / 100.0, dz / 100.0


def main():
    n_scenes = 3
    for a in sys.argv[1:]:
        if not a.startswith("-"):
            try:
                n_scenes = max(1, int(a))
            except ValueError:
                pass
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    lvl = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    act = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)

    meshes = find_vehicle_meshes()
    unreal.log("[cs_build] 차량 본체 메시 %d개: %s" % (len(meshes), [m.split('/')[-1] for m in meshes[:8]]))
    if not meshes:
        raise RuntimeError("no vehicle meshes")
    loaded = [unreal.EditorAssetLibrary.load_asset(m) for m in meshes]
    loaded = [m for m in loaded if m is not None]
    plane = unreal.EditorAssetLibrary.load_asset(PLANE_MESH_PATH)
    gray = unreal.EditorAssetLibrary.load_asset(GRAY_MAT)

    ok = 0
    for i in range(n_scenes):
        random.seed(2000 + i)
        path = "%s/scene_%d" % (LEVEL_DIR, i)
        if unreal.EditorAssetLibrary.does_asset_exist(path):
            unreal.EditorAssetLibrary.delete_asset(path)
        if not lvl.new_level(path):
            unreal.log_error("[cs_build] new_level 실패 scene_%d" % i)
            continue
        floor = act.spawn_actor_from_class(unreal.StaticMeshActor, unreal.Vector(0, 0, 0), unreal.Rotator(0, 0, 0))
        floor.static_mesh_component.set_static_mesh(plane)
        if gray:
            floor.static_mesh_component.set_material(0, gray)
        floor.set_actor_scale3d(unreal.Vector(FLOOR_EDGE_M, FLOOR_EDGE_M, 1.0))
        sun = act.spawn_actor_from_class(unreal.DirectionalLight, unreal.Vector(0, 0, 1000), unreal.Rotator(0, -50, 30))
        sun.light_component.set_intensity(8.0)
        act.spawn_actor_from_class(unreal.SkyLight, unreal.Vector(0, 0, 1000), unreal.Rotator(0, 0, 0))
        act.spawn_actor_from_class(unreal.SkyAtmosphere, unreal.Vector(0, 0, 0), unreal.Rotator(0, 0, 0))
        cam = act.spawn_actor_from_class(unreal.CameraActor,
                                         unreal.Vector(*CAMERA_LOCATION_CM),
                                         unreal.Rotator(0, 0, CAMERA_YAW_DEG))
        cam.set_editor_property("auto_activate_for_player", unreal.AutoReceiveInput.PLAYER0)

        vehicles = []
        for k in range(NUM_VEHICLES):
            mesh = random.choice(loaded)
            b = mesh.get_bounds()
            ext = b.box_extent
            dist = random.uniform(MIN_DIST_M, MAX_DIST_M)
            az = math.radians(random.uniform(-SECTOR_HALF_ANGLE_DEG, SECTOR_HALF_ANGLE_DEG))
            x = dist * 100 * math.cos(az)
            y = dist * 100 * math.sin(az)
            # 메시 원점이 바닥이 아닐 수 있어 바운드로 지면 접지: z = -(origin.z - extent.z)
            z = -(b.origin.z - ext.z)
            yaw = random.uniform(0, 360)
            v = act.spawn_actor_from_class(unreal.StaticMeshActor, unreal.Vector(x, y, z),
                                           unreal.Rotator(0, 0, yaw))
            v.static_mesh_component.set_static_mesh(mesh)
            v.static_mesh_component.set_mobility(unreal.ComponentMobility.MOVABLE)
            lx, ly, lz = world_to_camera_local_m((x, y, z + b.origin.z))
            vehicles.append(dict(
                mesh=mesh.get_name(),
                relative_position_m=dict(x=lx, y=ly, z=lz),
                relative_yaw_deg=((yaw - CAMERA_YAW_DEG + 180) % 360) - 180,
                size_m=dict(l=2 * ext.x / 100, w=2 * ext.y / 100, h=2 * ext.z / 100),
                distance_m=dist,
            ))
        lvl.save_current_level()
        with open(os.path.join(OUTPUT_DIR, "scene_%d.json" % i), "w") as f:
            json.dump(dict(scene=i, level=path,
                           camera=dict(fov_deg=90.0, z_m=1.5), vehicles=vehicles), f, indent=2)
        unreal.log("[cs_build] scene_%d OK (차량 %d)" % (i, len(vehicles)))
        ok += 1
    unreal.log("[cs_build] done ok=%d/%d" % (ok, n_scenes))


unreal.log("[cs_build] argv=%r" % (sys.argv,))
main()
