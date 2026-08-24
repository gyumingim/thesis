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

노면 습윤 변형 백로그: M_Asphalt_Master_Inst 의 Puddle/Roughness 파라미터는
set_material_instance_scalar_parameter_value 기본(GLOBAL) 연관으로는 전부 False —
레이어 파라미터(MFPD 계열) 추정, LAYER_PARAMETER 연관/레이어 인덱스 필요 (2026-08-24 실측).

주의: 이 장비에서 gen_0/gen_5 레벨 자산은 구성 무관하게 -game 렌더 시 D3D12 페이탈을
재현한다(시드 교체 무효, 신선한 이름 gen_10/11 은 동일 코드로 즉시 성공 — 2026-08-24 실측).
원인 미상(레벨 자산/캐시 오염 추정). 대량 생성 시 신선한 인덱스 대역을 쓸 것 (only=).
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
CROSSWALK_MESH = "/Game/Road/Kit_City_Road/SM_ROAD_19_3_0_19_crosswalk"   # 20x4m
# 건물 풀: 이름 → y-반폭(m). 커맨드릿에서 LevelInstance 는 비동기 로드라 스폰 직후
# 바운드가 미형성이고 flush_level_streaming 도 이를 올려주지 않는다(실측). 따라서 배치는
# 에디터 세션 실측(v7/v8 로그)의 반폭 테이블로 결정론적으로 한다. z 는 건드리지 않는다 —
# 히어로 빌딩은 원저작이 지면 정렬돼 있고, 미형성 바운드로 ground() 를 하면 오히려
# 공중에 뜬다(scene_5 부유 건물의 진짜 원인).
BLDG_POOL = {
    "/Game/Building/Library/Kit_Hero_Bldg/LevelInstance/Bldg_Hero_Mid_SFC_A01": 23.0,
    "/Game/Building/Library/Kit_Hero_Bldg/LevelInstance/Bldg_Hero_Mid_SFC_B01": 30.0,
    "/Game/Building/Library/Kit_Hero_Bldg/LevelInstance/Bldg_Hero_Low_CHG_Modern_A01": 33.0,
}
# 건물 풀 확장 실패 기록 (2026-08-24 밤): SFE_A01/B01·NYG_Triangle_B01 을 넣은 장면은
# -game 로드~첫 프레임에서 D3D12 페이탈이 재현된다 (기지 장면은 같은 시각 정상 렌더 —
# 머신 아닌 내용 상관 실측). 신규 히어로 빌딩 추가는 장면당 1종씩 단독 검증 후 편입할 것.
TREE_POOL = [
    "/Game/Prop/Kit_Tree_Maple_Red/Mesh/Tree_Maple_Red_A",
    "/Game/Prop/Kit_Tree_Alder/Mesh/Tree_Alder_A",
    "/Game/Prop/Kit_Tree_Birch/Mesh/SM_Tree_Birch_a",
    "/Game/Prop/Kit_Tree_Birch/Mesh/SM_Tree_Birch_c",
]
PROP_POOL = [   # (경로, 인도 배치 확률)
    ("/Game/Prop/Kit_Trashcan_A/Mesh/SM_Trashcan_A_01", 0.5),
    ("/Game/Prop/Kit_StopSign_A/Mesh/SM_StopSign_A", 0.3),
    ("/Game/Prop/Kit_Cone_C_A/Mesh/SM_Cone_C_A", 0.25),
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


def spawn_bldg(path, half_w_m, x, side, yaw):
    w = unreal.load_asset(path)
    if w is None:
        log("BLDG 로드 실패 " + path)
        return None
    y = side * (CORRIDOR_CM + half_w_m * 100 + random.uniform(0, 600))
    bl = act.spawn_actor_from_class(unreal.LevelInstance, unreal.Vector(x, y, 0),
                                    unreal.Rotator(0, 0, yaw))
    bl.set_editor_property("world_asset", w)
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


def build_scene(i, road, sw, pole, vehicles, crosswalk=None, seed_base=3000, trees=(), props=()):
    random.seed(seed_base + i)
    path = "%s/gen_%d" % (LEVEL_DIR, i)
    open_clean_level(path)

    rb = road.get_bounds()
    seg = 2 * rb.box_extent.x
    for k in range(ROAD_TILES):
        top0(spawn_sm(road, k * seg - rb.origin.x, -rb.origin.y))
    if crosswalk and random.random() < 0.6:       # 횡단보도를 도로 위에 겹쳐 깔기 (데칼처럼 2cm 위)
        cw_x = random.uniform(8, ROAD_TILES * 20 - 15) * 100
        cb = crosswalk.get_bounds()
        a = top0(spawn_sm(crosswalk, cw_x - cb.origin.x, -cb.origin.y))
        a.add_actor_world_offset(unreal.Vector(0, 0, 2), False, False)

    sb = sw.get_bounds()
    for k in range(ROAD_TILES * 20 // 6 + 2):
        for side in (-1, 1):
            a = top0(spawn_sm(sw, k * 600 - sb.origin.x,
                              side * (ROAD_HALF_W_CM + 150) - sb.origin.y))
            a.add_actor_world_offset(unreal.Vector(0, 0, 15), False, False)

    for k in range(1, ROAD_TILES):
        for side, yaw in ((-1, 0), (1, 180)):
            ground(spawn_sm(pole, k * 2200, side * (ROAD_HALF_W_CM + 150), 0, yaw))
    for k in range(1, ROAD_TILES):                     # 가로수: 가로등 사이 중간점
        for side in (-1, 1):
            if trees and random.random() < 0.6:
                ground(spawn_sm(random.choice(trees), k * 2200 + 1100,
                                side * (ROAD_HALF_W_CM + 200), 0, random.uniform(0, 360)))
    for k in range(ROAD_TILES * 2):                    # 소품: 인도 위 산포
        for m, pr in props:
            if random.random() < pr * 0.5:
                side = random.choice((-1, 1))
                ground(spawn_sm(m, random.uniform(500, ROAD_TILES * 2000),
                                side * (ROAD_HALF_W_CM + random.uniform(120, 260)), 0,
                                random.uniform(0, 360)))

    x = 2000.0
    n_bldg = 0
    while x < ROAD_TILES * 2000 + 4000:
        for side in (-1, 1):
            if random.random() < 0.8:
                path = random.choice(list(BLDG_POOL))
                if spawn_bldg(path, BLDG_POOL[path], x + random.uniform(-500, 500), side,
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

    cam_z = random.uniform(130.0, 185.0)          # 승용차~SUV 시점
    cam_yaw = random.uniform(-6.0, 6.0)
    cam = act.spawn_actor_from_class(unreal.CameraActor, unreal.Vector(0, 0, cam_z),
                                     unreal.Rotator(0, 0, cam_yaw))
    cam.set_editor_property("auto_activate_for_player", unreal.AutoReceiveInput.PLAYER0)

    n_veh = random.randint(*N_VEH_RANGE)
    placed, labels, tries = [], [], 0
    while len(labels) < n_veh and tries < 100:
        tries += 1
        m = random.choice(vehicles)
        e = m.get_bounds().box_extent
        r = math.hypot(e.x / 100, e.y / 100)
        mode = random.random()
        if mode < 0.15:
            # 평행주차: 갓길(|y|≈8.2m)에 차선과 나란히
            x = random.uniform(6, 48)
            side = random.choice((-1, 1))
            y = side * random.uniform(7.9, 8.4)
            yaw = (0.0 if side < 0 else 180.0) + random.uniform(-4, 4)
        else:
            x = random.uniform(6, 48)
            y = random.uniform(-7.5, 7.5)
            if mode < 0.85:
                # 우측통행 차선 의미론: y<0(우측 차선) 순방향, y>0 마주 옴
                yaw = (0.0 if y < 0 else 180.0) + random.uniform(-8, 8)
            else:
                yaw = random.uniform(0, 360)   # 회전 중/무단 주차 등 자유
        if any(math.hypot(x - px, y - py) < r + pr + 0.4 for px, py, pr in placed):
            continue
        a = ground(spawn_sm(m, x * 100, y * 100, 0, yaw))
        rf = random.random()
        a.static_mesh_component.set_default_custom_primitive_data_float(1, pack_rf(rf))
        wo, _ = a.get_actor_bounds(False)
        placed.append((x, y, r))
        # 라벨은 카메라 좌표계 (지터 반영: 평행이동 + -cam_yaw 회전)
        cyr = math.radians(cam_yaw)
        dx_, dy_ = wo.x / 100, wo.y / 100
        rel_x = dx_ * math.cos(cyr) + dy_ * math.sin(cyr)
        rel_y = -dx_ * math.sin(cyr) + dy_ * math.cos(cyr)
        lb = dict(mesh=m.get_name(), paint_rf=round(rf, 3),
                  relative_position_m=dict(x=rel_x, y=rel_y, z=(wo.z - cam_z) / 100),
                  relative_yaw_deg=((yaw - cam_yaw + 180) % 360) - 180,
                  size_m=dict(l=2 * e.x / 100, w=2 * e.y / 100, h=2 * e.z / 100))
        bb = bbox2d(lb)
        if bb:
            lb["bbox2d"] = bb
        labels.append(lb)

    lvl.save_current_level()
    with open(os.path.join(OUTPUT_DIR, "scene_%d.json" % i), "w") as f:
        json.dump(dict(scene=i, level=path,
                       camera=dict(fov_deg=FOV, z_m=round(cam_z / 100, 3), yaw_deg=round(cam_yaw, 2), width=W, height=H),
                       sun=dict(pitch=round(sun_pitch, 1), yaw=round(sun_yaw, 1)),
                       vehicles=labels), f, indent=2)
    log("scene_%d OK (차량 %d, 건물 %d)" % (i, len(labels), n_bldg))


def main():
    # 인자: <장면수> [only=0,5] [seed=9000]
    #   only: 해당 장면만 재생성 (특정 구성이 HighResShot 시점 D3D12 행을 유발할 때 시드 교체용)
    n, only, seed_base = 10, None, 3000
    for tok in sys.argv[1:]:
        if tok.isdigit():
            n = int(tok)
        elif tok.startswith("only="):
            only = [int(x) for x in tok[5:].split(",")]
        elif tok.startswith("seed="):
            seed_base = int(tok[5:])
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    def load_any(path):
        m = unreal.load_asset(path)
        if m is None:   # Mesh/ 하위가 아니면 키트 루트에서 이름으로 탐색
            kit = "/".join(path.split("/")[:-2]) if "/Mesh/" in path else "/".join(path.split("/")[:-1])
            name = path.split("/")[-1]
            for a in eal.list_assets(kit, recursive=True, include_folder=False):
                if a.split("/")[-1].split(".")[0] == name:
                    return unreal.load_asset(a.split(".")[0])
        return m
    road = unreal.load_asset(ROAD_MESH)
    crosswalk = unreal.load_asset(CROSSWALK_MESH)
    trees = [m for m in (load_any(t) for t in TREE_POOL) if m]
    props = [(m, pr) for m, pr in ((load_any(t), pr) for t, pr in PROP_POOL) if m]
    log("나무 %d종 소품 %d종" % (len(trees), len(props)))
    sw = unreal.load_asset(find_asset("/Game/Road/Kit_Sidewalk_A", ("Sidewalk_6_3_A",))[0])
    pole = unreal.load_asset(find_asset("/Game/Prop/Kit_StreetLamp_A", ("Pole_Large",))[0])
    vehicles = [m for m in (unreal.load_asset(v) for v in
                            find_asset("/Game/Vehicle", ("SM_veh",), VEH_EXCLUDE)) if m]
    log("재료: 차량 %d종" % len(vehicles))
    ok = 0
    for i in (only if only is not None else range(n)):
        try:
            build_scene(i, road, sw, pole, vehicles, crosswalk, seed_base, trees, props)
            ok += 1
        except Exception as e:
            unreal.log_error("[cs_build2] scene_%d 실패: %s" % (i, e))
    log("done %d/%d" % (ok, n))


# 커맨드릿 pythonscript 는 __name__ 이 보장되지 않으므로 무조건 실행
main()
