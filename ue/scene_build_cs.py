"""CitySample 도시 장면 생성기 v2 — 도로 키트 + 히어로 빌딩 + 차량(도색·겹침배제) + 라벨.

실행(에디터 커맨드릿 — 렌더는 하지 않는다):
  UnrealEditor-Cmd.exe <CitySample.uproject> -run=pythonscript \
    -script="ue/scene_build_cs.py <장면수>" -unattended -nosplash
렌더는 ue/cs_render.sh 가 장면마다 -game 프로세스로 수행한다.

v1(회색 평면 + 흰 차) 대비 변경 — 전부 2026-08-24 실측으로 확정된 사실에 기반:
- 지면: BasicShapes 평면 → CitySample 도로 키트 타일(SM_ROAD_19_20, 20x21m) + 인도 + 가로등
- 배경: 히어로 빌딩 LevelInstance 풀. vista 메시(SM_bgcity*)는 -game 에서 렌더되지 않아 폐기.
  스폰 후 실측 바운드로 접지 + 도로 회랑(|y|<13m) 침범 시 밀어냄, y-폭 45m 초과는 퇴출.
- 도색: MassTraffic 순정 방식 — RandomFraction 을 float16 비트패킹해
  CustomPrimitiveData[1] 에 주입 (MassTrafficVehicleVisualizationProcessor.cpp 방식.
  머티리얼/에셋 생성 불필요, 레벨에 저장됨).
- 차량: 겹침 배제(반대각 원 반경 + 0.4m 마진), 스폰 후 월드바운드 실측 접지(v1의 침몰 수정 유지).
- 조명: 장면 시드 기반 랜덤화 (태양 pitch -65~-15, yaw 0~360, 세기 6~14) + 높이안개 0.003.
  노출은 자동 유지 — 수동 bias 는 실측 백화로 기각.
- 라벨: v1 스키마 + width/height + bbox2d(GT 3D 박스의 핀홀 투영, FOV90/1280x720 → fx=640).
- 레벨 재사용: delete_asset+new_level 은 OFPA 잔재로 "asset already exists" 가 나므로
  기존 레벨은 열어서 액터 전부 삭제 후 재사용한다.

출력: /Game/GenScenes/gen_<i> + C:/ue/out_cs2/scene_<i>.json  (독스트링에 역슬래시 경로 금지 — 16734e2 함정)
"""
import unreal
import sys
import os
import json
import math
import random
import struct

LEVEL_DIR = "/Game/GenScenes"
OUTPUT_DIR = r"C:\ue\out_cs2"
W, H, FOV = 1280, 720, 90.0
FX = FY = (W / 2) / math.tan(math.radians(FOV / 2))   # 640.0
CX, CY = W / 2, H / 2
CAM_Z_CM = 150.0
N_VEH_RANGE = (3, 8)
ROAD_TILES = 6                    # 20m x 6 = 120m
ROAD_HALF_W_CM = 1050
CORRIDOR_CM = 1300                # 건물 금지 회랑 반폭
ROAD_MESH = "/Game/Road/Kit_City_Road/SM_ROAD_19_20_0_0_road"
BLDG_POOL = [
    "/Game/Building/Library/Kit_Hero_Bldg/LevelInstance/Bldg_Hero_Mid_SFC_A01",
    "/Game/Building/Library/Kit_Hero_Bldg/LevelInstance/Bldg_Hero_Mid_SFC_B01",
    "/Game/Building/Library/Kit_Hero_Bldg/LevelInstance/Bldg_Hero_Mid_NYG_Triangle_A01",
    "/Game/Building/Library/Kit_Hero_Bldg/LevelInstance/Bldg_Hero_Mid_CHG_Long_A01",
    "/Game/Building/Library/Kit_Hero_Bldg/LevelInstance/Bldg_Hero_Low_CHG_Modern_A01",
]
VEH_EXCLUDE = ("Wheel", "Brake", "Door", "MotionBlur", "Trans", "No_Wheel", "Steering",
               "Caliper", "Rotor", "Glass", "Mirror", "Bumper", "Hood", "Trunk", "seat", "Seat")

eal = unreal.EditorAssetLibrary
lvl = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
act = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)


def log(s):
    unreal.log("[cs_build2] " + str(s))


def pack_rf(f):
    """RandomFraction(0..1) → float16 비트를 float32 로 재해석 (MassTraffic 패킹)."""
    h = struct.unpack('<H', struct.pack('<e', f))[0]
    return struct.unpack('<f', struct.pack('<I', h))[0]


def find_asset(root, must, exclude=()):
    out = []
    for a in eal.list_assets(root, recursive=True, include_folder=False):
        name = a.split("/")[-1].split(".")[0]
        if not name.startswith("SM_"):
            continue
        if any(k in a for k in exclude):
            continue
        if all(k in a for k in must):
            out.append(a.split(".")[0])
    return sorted(set(out))


def open_clean_level(path):
    if not eal.does_asset_exist(path):
        if not lvl.new_level(path):
            raise RuntimeError("new_level 실패 " + path)
        return
    if not lvl.load_level(path):
        raise RuntimeError("load_level 실패 " + path)
    doomed = act.get_all_level_actors()
    for a in doomed:
        act.destroy_actor(a)


def spawn_sm(mesh, x, y, z=0.0, yaw=0.0):
    a = act.spawn_actor_from_class(unreal.StaticMeshActor, unreal.Vector(x, y, z),
                                   unreal.Rotator(0, 0, yaw))
    a.static_mesh_component.set_static_mesh(mesh)
    a.static_mesh_component.set_mobility(unreal.ComponentMobility.MOVABLE)
    return a


def ground(a):
    """바닥을 z=0 에 (피벗이 메시마다 달라 월드바운드 실측 정렬 — v1의 침몰 수정)."""
    wo, we = a.get_actor_bounds(False)
    a.add_actor_world_offset(unreal.Vector(0, 0, -(wo.z - we.z)), False, False)
    return a


def top0(a):
    """상면을 z=0 에 (도로/인도 타일)."""
    wo, we = a.get_actor_bounds(False)
    a.add_actor_world_offset(unreal.Vector(0, 0, -(wo.z + we.z)), False, False)
    return a


def spawn_bldg(path, x, y, yaw):
    w = unreal.load_asset(path)
    if w is None:
        log("BLDG 로드 실패 " + path)
        return None
    bl = act.spawn_actor_from_class(unreal.LevelInstance, unreal.Vector(x, y, 0),
                                    unreal.Rotator(0, 0, yaw))
    bl.set_editor_property("world_asset", w)
    wo, we = bl.get_actor_bounds(False)
    log("BLDG %s e(%.0f,%.0f,%.0f)m" % (path.split("/")[-1], we.x / 100, we.y / 100, we.z / 100))
    if we.x < 300 or we.y < 300 or we.z < 500:
        # 인스턴스 레벨이 아직 로드되지 않아 바운드가 미형성 — 접지/회랑 로직이 전부
        # 오작동한다(scene_5 부유 건물 실측). 이 상태의 건물은 쓰지 않는다.
        log("BLDG %s 퇴출 (바운드 미형성)" % path.split("/")[-1])
        act.destroy_actor(bl)
        return None
    if we.y > 4500:                          # 회랑을 지킬 수 없는 초대형 — 퇴출
        act.destroy_actor(bl)
        return None
    bl.add_actor_world_offset(unreal.Vector(0, 0, -(wo.z - we.z)), False, False)
    wo, we = bl.get_actor_bounds(False)
    near = abs(wo.y) - we.y
    if near < CORRIDOR_CM:                   # 도로 침범 → 바깥으로
        push = (CORRIDOR_CM - near) * (1 if wo.y >= 0 else -1)
        bl.add_actor_world_offset(unreal.Vector(0, push, 0), False, False)
    return bl


def bbox2d(lb):
    """GT 3D 박스 8모서리의 핀홀 투영 (카메라 = 원점, yaw 0). 잘리면 None."""
    p, s = lb["relative_position_m"], lb["size_m"]
    l2, w2, h2 = s["l"] / 2, s["w"] / 2, s["h"] / 2
    yr = math.radians(lb["relative_yaw_deg"])
    c, sn = math.cos(yr), math.sin(yr)
    us, vs = [], []
    for dx in (-l2, l2):
        for dy in (-w2, w2):
            for dz in (-h2, h2):
                x = p["x"] + dx * c - dy * sn
                y = p["y"] + dx * sn + dy * c
                z = p["z"] + dz
                if x <= 0.3:
                    return None
                us.append(CX + FX * y / x)
                vs.append(CY - FY * z / x)
    u0, u1 = max(0, min(us)), min(W, max(us))
    v0, v1 = max(0, min(vs)), min(H, max(vs))
    if u1 - u0 < 4 or v1 - v0 < 4:
        return None
    return [round(u0, 1), round(v0, 1), round(u1, 1), round(v1, 1)]


def build_scene(i, road, sw, pole, vehicles):
    random.seed(3000 + i)
    path = "%s/gen_%d" % (LEVEL_DIR, i)
    open_clean_level(path)

    rb = road.get_bounds()
    seg = 2 * rb.box_extent.x
    for k in range(ROAD_TILES):
        top0(spawn_sm(road, k * seg - rb.origin.x, -rb.origin.y))

    sb = sw.get_bounds()
    for k in range(ROAD_TILES * 20 // 6 + 2):
        for side in (-1, 1):
            a = top0(spawn_sm(sw, k * 600 - sb.origin.x,
                              side * (ROAD_HALF_W_CM + 150) - sb.origin.y))
            a.add_actor_world_offset(unreal.Vector(0, 0, 15), False, False)

    for k in range(1, ROAD_TILES):
        for side, yaw in ((-1, 0), (1, 180)):
            ground(spawn_sm(pole, k * 2200, side * (ROAD_HALF_W_CM + 150), 0, yaw))

    x = 2000.0
    n_bldg = 0
    while x < ROAD_TILES * 2000 + 4000:
        for side in (-1, 1):
            if random.random() < 0.8:
                if spawn_bldg(random.choice(BLDG_POOL), x + random.uniform(-500, 500),
                              side * random.uniform(2400, 3600),
                              random.uniform(-10, 10) + (0 if side < 0 else 180)):
                    n_bldg += 1
        x += random.uniform(3500, 5500)

    fog = act.spawn_actor_from_class(unreal.ExponentialHeightFog,
                                     unreal.Vector(0, 0, 0), unreal.Rotator(0, 0, 0))
    fog.component.set_editor_property("fog_density", random.uniform(0.001, 0.006))
    fog.component.set_editor_property("fog_height_falloff", 0.2)

    sun_pitch = random.uniform(-65, -15)
    sun_yaw = random.uniform(0, 360)
    sun = act.spawn_actor_from_class(unreal.DirectionalLight, unreal.Vector(0, 0, 1000),
                                     unreal.Rotator(0, sun_pitch, sun_yaw))
    sun.light_component.set_intensity(random.uniform(6.0, 14.0))
    act.spawn_actor_from_class(unreal.SkyLight, unreal.Vector(0, 0, 1000), unreal.Rotator(0, 0, 0))
    act.spawn_actor_from_class(unreal.SkyAtmosphere, unreal.Vector(0, 0, 0), unreal.Rotator(0, 0, 0))

    cam = act.spawn_actor_from_class(unreal.CameraActor, unreal.Vector(0, 0, CAM_Z_CM),
                                     unreal.Rotator(0, 0, 0))
    cam.set_editor_property("auto_activate_for_player", unreal.AutoReceiveInput.PLAYER0)

    n_veh = random.randint(*N_VEH_RANGE)
    placed, labels, tries = [], [], 0
    while len(labels) < n_veh and tries < 100:
        tries += 1
        m = random.choice(vehicles)
        e = m.get_bounds().box_extent
        r = math.hypot(e.x / 100, e.y / 100)
        d = random.uniform(6, 48)
        az = math.radians(random.uniform(-32, 32))
        x, y = d * math.cos(az), d * math.sin(az)
        if abs(y) > 8.5:
            continue
        if any(math.hypot(x - px, y - py) < r + pr + 0.4 for px, py, pr in placed):
            continue
        yaw = random.uniform(0, 360)
        a = ground(spawn_sm(m, x * 100, y * 100, 0, yaw))
        rf = random.random()
        a.static_mesh_component.set_default_custom_primitive_data_float(1, pack_rf(rf))
        wo, _ = a.get_actor_bounds(False)
        placed.append((x, y, r))
        lb = dict(mesh=m.get_name(), paint_rf=round(rf, 3),
                  relative_position_m=dict(x=wo.x / 100, y=wo.y / 100, z=(wo.z - CAM_Z_CM) / 100),
                  relative_yaw_deg=((yaw + 180) % 360) - 180,
                  size_m=dict(l=2 * e.x / 100, w=2 * e.y / 100, h=2 * e.z / 100))
        bb = bbox2d(lb)
        if bb:
            lb["bbox2d"] = bb
        labels.append(lb)

    lvl.save_current_level()
    with open(os.path.join(OUTPUT_DIR, "scene_%d.json" % i), "w") as f:
        json.dump(dict(scene=i, level=path,
                       camera=dict(fov_deg=FOV, z_m=CAM_Z_CM / 100, width=W, height=H),
                       sun=dict(pitch=round(sun_pitch, 1), yaw=round(sun_yaw, 1)),
                       vehicles=labels), f, indent=2)
    log("scene_%d OK (차량 %d, 건물 %d)" % (i, len(labels), n_bldg))


def main():
    n = 10
    for tok in sys.argv[1:]:
        if tok.isdigit():
            n = int(tok)
            break
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    road = unreal.load_asset(ROAD_MESH)
    sw = unreal.load_asset(find_asset("/Game/Road/Kit_Sidewalk_A", ("Sidewalk_6_3_A",))[0])
    pole = unreal.load_asset(find_asset("/Game/Prop/Kit_StreetLamp_A", ("Pole_Large",))[0])
    vehicles = [m for m in (unreal.load_asset(v) for v in
                            find_asset("/Game/Vehicle", ("SM_veh",), VEH_EXCLUDE)) if m]
    log("재료: 차량 %d종" % len(vehicles))
    ok = 0
    for i in range(n):
        try:
            build_scene(i, road, sw, pole, vehicles)
            ok += 1
        except Exception as e:
            unreal.log_error("[cs_build2] scene_%d 실패: %s" % (i, e))
    log("done %d/%d" % (ok, n))


# 커맨드릿 pythonscript 는 __name__ 이 보장되지 않으므로 무조건 실행
main()
