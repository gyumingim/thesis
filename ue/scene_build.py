"""
UE 5.8 headless data-gen stage 1: scene_build.py
Run: UnrealEditor-Cmd.exe <proj> -run=pythonscript -script="scene_build.py <scene_count>"
Uses LevelEditorSubsystem / EditorActorSubsystem / EditorAssetLibrary (5.6+ non-deprecated paths).
"""
import unreal
import sys
import os
import json
import math
import random

# ---- config -----------------------------------------------------------
LEVEL_DIR = "/Game/Scenes"
OUTPUT_DIR = r"C:\ue\out"
DEFAULT_SCENE_COUNT = 8

NUM_VEHICLES = 8                 # N=8 고정 (스펙)
MIN_DIST_M = 5.0
MAX_DIST_M = 50.0
SECTOR_HALF_ANGLE_DEG = 35.0      # 카메라 전방 부채꼴 반각

CAMERA_LOCATION_CM = (0.0, 0.0, 150.0)   # 원점, 높이 1.5m
CAMERA_YAW_DEG = 0.0                     # +X 방향을 정면으로 사용

VEHICLE_SIZE_M = (4.5, 1.8, 1.5)         # (length_x, width_y, height_z)
FLOOR_EDGE_M = 200.0

CUBE_MESH_PATH = "/Engine/BasicShapes/Cube"
PLANE_MESH_PATH = "/Engine/BasicShapes/Plane"
GRAY_MATERIAL_PATH = "/Engine/BasicShapes/BasicShapeMaterial"


# ---- argv ---------------------------------------------------------------
def parse_scene_count(default=DEFAULT_SCENE_COUNT):
    for a in sys.argv[1:]:
        if a.startswith("-"):
            continue
        try:
            return max(1, int(a))
        except ValueError:
            continue
    return default


# ---- subsystems -----------------------------------------------------------
def get_subsystems():
    level_subsystem = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    actor_subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    return level_subsystem, actor_subsystem


def ensure_level(level_subsystem, level_path):
    if unreal.EditorAssetLibrary.does_asset_exist(level_path):
        unreal.EditorAssetLibrary.delete_asset(level_path)
    if not level_subsystem.new_level(level_path):
        raise RuntimeError("new_level failed: %s" % level_path)


# ---- geometry helpers -------------------------------------------------
def world_to_camera_local_m(target_xyz_cm, camera_xyz_cm=CAMERA_LOCATION_CM,
                             camera_yaw_deg=CAMERA_YAW_DEG):
    """카메라 기준 상대 위치(m). 카메라는 yaw만 갖는다고 가정(pitch/roll=0)."""
    dx = target_xyz_cm[0] - camera_xyz_cm[0]
    dy = target_xyz_cm[1] - camera_xyz_cm[1]
    dz = target_xyz_cm[2] - camera_xyz_cm[2]
    yaw_rad = math.radians(camera_yaw_deg)
    cos_y, sin_y = math.cos(yaw_rad), math.sin(yaw_rad)
    local_x = dx * cos_y + dy * sin_y
    local_y = -dx * sin_y + dy * cos_y
    local_z = dz
    return local_x / 100.0, local_y / 100.0, local_z / 100.0


def wrap_deg(angle_deg):
    return ((angle_deg + 180.0) % 360.0) - 180.0


# ---- actor spawn --------------------------------------------------------
def spawn_floor(actor_subsystem):
    mesh = unreal.EditorAssetLibrary.load_asset(PLANE_MESH_PATH)
    mat = unreal.EditorAssetLibrary.load_asset(GRAY_MATERIAL_PATH)
    if mesh is None:
        raise RuntimeError("cannot load mesh: %s" % PLANE_MESH_PATH)

    floor = actor_subsystem.spawn_actor_from_class(
        unreal.StaticMeshActor,
        unreal.Vector(x=0.0, y=0.0, z=0.0),
        unreal.Rotator(roll=0.0, pitch=0.0, yaw=0.0),
    )
    floor.set_actor_label("Floor_Road")
    smc = floor.static_mesh_component
    smc.set_static_mesh(mesh)
    if mat is not None:
        smc.set_material(0, mat)
    floor.set_actor_scale3d(unreal.Vector(x=FLOOR_EDGE_M, y=FLOOR_EDGE_M, z=1.0))
    smc.set_mobility(unreal.ComponentMobility.STATIC)
    return floor


def spawn_lights(actor_subsystem):
    """-game 캡처가 검은 화면이 되지 않도록 광원 필수 (2026-08-20 스모크 실패로 확인)."""
    sun = actor_subsystem.spawn_actor_from_class(
        unreal.DirectionalLight,
        unreal.Vector(x=0.0, y=0.0, z=1000.0),
        unreal.Rotator(roll=0.0, pitch=-50.0, yaw=30.0),
    )
    sun.set_actor_label("Sun")
    sun.light_component.set_intensity(8.0)
    sky = actor_subsystem.spawn_actor_from_class(
        unreal.SkyLight,
        unreal.Vector(x=0.0, y=0.0, z=1000.0),
        unreal.Rotator(roll=0.0, pitch=0.0, yaw=0.0),
    )
    sky.set_actor_label("Sky")
    atmo = actor_subsystem.spawn_actor_from_class(
        unreal.SkyAtmosphere,
        unreal.Vector(x=0.0, y=0.0, z=0.0),
        unreal.Rotator(roll=0.0, pitch=0.0, yaw=0.0),
    )
    atmo.set_actor_label("Atmosphere")


def spawn_camera(actor_subsystem):
    loc = unreal.Vector(x=CAMERA_LOCATION_CM[0], y=CAMERA_LOCATION_CM[1], z=CAMERA_LOCATION_CM[2])
    rot = unreal.Rotator(roll=0.0, pitch=0.0, yaw=CAMERA_YAW_DEG)
    cam = actor_subsystem.spawn_actor_from_class(unreal.CameraActor, loc, rot)
    cam.set_actor_label("Camera_Main")
    # -game 모드에서 이 카메라가 곧바로 플레이어 0 의 뷰가 되도록 (기본 폰 시점 방지)
    cam.set_editor_property("auto_activate_for_player", unreal.AutoReceiveInput.PLAYER0)
    return cam


def spawn_vehicle(actor_subsystem, mesh, mat, index):
    dist_m = random.uniform(MIN_DIST_M, MAX_DIST_M)
    az_deg = random.uniform(-SECTOR_HALF_ANGLE_DEG, SECTOR_HALF_ANGLE_DEG)
    az_rad = math.radians(az_deg)
    dist_cm = dist_m * 100.0

    x = CAMERA_LOCATION_CM[0] + dist_cm * math.cos(az_rad)
    y = CAMERA_LOCATION_CM[1] + dist_cm * math.sin(az_rad)
    z = (VEHICLE_SIZE_M[2] * 100.0) / 2.0  # 바닥(z=0)에 닿도록 큐브 절반 높이만큼 띄움
    yaw_deg = random.uniform(0.0, 360.0)

    loc = unreal.Vector(x=x, y=y, z=z)
    rot = unreal.Rotator(roll=0.0, pitch=0.0, yaw=yaw_deg)

    actor = actor_subsystem.spawn_actor_from_class(unreal.StaticMeshActor, loc, rot)
    actor.set_actor_label("Vehicle_%02d" % index)
    smc = actor.static_mesh_component
    smc.set_static_mesh(mesh)
    if mat is not None:
        smc.set_material(0, mat)
    actor.set_actor_scale3d(unreal.Vector(x=VEHICLE_SIZE_M[0], y=VEHICLE_SIZE_M[1], z=VEHICLE_SIZE_M[2]))
    smc.set_mobility(unreal.ComponentMobility.MOVABLE)

    return {
        "world_xyz_cm": (x, y, z),
        "world_yaw_deg": yaw_deg,
        "spawn_distance_m": dist_m,
        "spawn_azimuth_deg": az_deg,
    }


# ---- json export ----------------------------------------------------------
def write_scene_json(scene_index, level_path, vehicle_records):
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    vehicles_out = []
    for i, rec in enumerate(vehicle_records):
        lx, ly, lz = world_to_camera_local_m(rec["world_xyz_cm"])
        rel_yaw = wrap_deg(rec["world_yaw_deg"] - CAMERA_YAW_DEG)
        vehicles_out.append({
            "id": i,
            "relative_position_m": {"x": lx, "y": ly, "z": lz},  # x=전방, y=우측, z=상방
            "relative_yaw_deg": rel_yaw,
            "spawn_distance_m": rec["spawn_distance_m"],
            "spawn_azimuth_deg": rec["spawn_azimuth_deg"],
        })

    payload = {
        "scene_index": scene_index,
        "level_path": level_path,
        "camera": {
            "location_m": {
                "x": CAMERA_LOCATION_CM[0] / 100.0,
                "y": CAMERA_LOCATION_CM[1] / 100.0,
                "z": CAMERA_LOCATION_CM[2] / 100.0,
            },
            "yaw_deg": CAMERA_YAW_DEG,
        },
        "num_vehicles": len(vehicles_out),
        "vehicles": vehicles_out,
    }

    out_path = os.path.join(OUTPUT_DIR, "scene_%d.json" % scene_index)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    return out_path


# ---- per-scene build --------------------------------------------------
def build_scene(level_subsystem, actor_subsystem, scene_index):
    random.seed(1000 + scene_index)          # 장면별 고정 시드 — 재현성
    level_path = "%s/scene_%d" % (LEVEL_DIR, scene_index)
    ensure_level(level_subsystem, level_path)

    spawn_floor(actor_subsystem)
    spawn_lights(actor_subsystem)
    spawn_camera(actor_subsystem)

    cube_mesh = unreal.EditorAssetLibrary.load_asset(CUBE_MESH_PATH)
    cube_mat = unreal.EditorAssetLibrary.load_asset(GRAY_MATERIAL_PATH)
    if cube_mesh is None:
        raise RuntimeError("cannot load mesh: %s" % CUBE_MESH_PATH)

    vehicle_records = [
        spawn_vehicle(actor_subsystem, cube_mesh, cube_mat, i)
        for i in range(NUM_VEHICLES)
    ]

    level_subsystem.save_current_level()
    json_path = write_scene_json(scene_index, level_path, vehicle_records)
    return level_path, json_path


# ---- main ---------------------------------------------------------------
def main():
    scene_count = parse_scene_count()
    level_subsystem, actor_subsystem = get_subsystems()
    if level_subsystem is None or actor_subsystem is None:
        raise RuntimeError("editor subsystems unavailable (not running as editor commandlet?)")

    unreal.log("[scene_build] scene_count=%d vehicles_per_scene=%d" % (scene_count, NUM_VEHICLES))

    ok, failed = 0, 0
    for i in range(scene_count):
        try:
            level_path, json_path = build_scene(level_subsystem, actor_subsystem, i)
            unreal.log("[scene_build] scene_%d OK level=%s json=%s" % (i, level_path, json_path))
            ok += 1
        except Exception as exc:  # noqa: BLE001 - 배치 생성 중 1건 실패로 전체 중단 방지
            unreal.log_error("[scene_build] scene_%d FAILED: %s" % (i, exc))
            failed += 1

    unreal.log("[scene_build] done: ok=%d failed=%d total=%d" % (ok, failed, scene_count))


# 커맨드릿 pythonscript 는 __name__ 값이 보장되지 않으므로 무조건 실행
unreal.log("[scene_build] sys.argv=%r" % (sys.argv,))
main()
