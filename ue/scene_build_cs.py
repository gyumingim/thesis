"""CitySample 도시 장면 생성기 v2 — 도로 키트 + 히어로 빌딩 + 차량(도색·겹침배제) + 라벨.

실행(에디터 커맨드릿 — 렌더는 하지 않는다):
  UnrealEditor-Cmd.exe <CitySample.uproject> -run=pythonscript \
    -script="ue/scene_build_cs.py <장면수>" -unattended -nosplash
렌더는 ue/cs_render.sh 가 장면마다 -game 프로세스로 수행한다.

v1(회색 평면 + 흰 차) 대비 변경 — 전부 2026-08-24 실측으로 확정된 사실에 기반:
- 지면: BasicShapes 평면 → CitySample 도로 키트 타일(SM_ROAD_19_20, 20x21m) + 인도 + 가로등
- 배경: 히어로 빌딩 LevelInstance 풀. vista 메시(SM_bgcity*)는 -game 에서 렌더되지 않아 폐기.
  스폰 후 실측 바운드로 접지 + 도로 회랑(|y|<13m) 침범 시 밀어냄, y-폭 45m 초과는 퇴출.
  건물은 요각까지 반영한 점유 반폭으로 회랑 밖에 배치한다(2026-08-29 수정:
  요각 미반영이던 이전 판은 측면 건물의 52.7% 가 회랑을 최대 6.8 m 침범했다).
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
N_VEH_RANGE = (6, 14)
ROAD_TILES = 6                    # 20m x 6 = 120m
ROAD_HALF_W_CM = 1050
CORRIDOR_CM = 1300                # 건물 금지 회랑 반폭
ROAD_MESH = "/Game/Road/Kit_City_Road/SM_ROAD_19_20_0_0_road"
CROSSWALK_MESH = "/Game/Road/Kit_City_Road/SM_ROAD_19_3_0_19_crosswalk"   # 20x4m
DECAL_DIR = "/Game/Road/Kit_MeshDecals_A"
# 건물 풀: 이름 → y-반폭(m). 커맨드릿에서 LevelInstance 는 비동기 로드라 스폰 직후
# 바운드가 미형성이고 flush_level_streaming 도 이를 올려주지 않는다(실측). 따라서 배치는
# 에디터 세션 실측(v7/v8 로그)의 반폭 테이블로 결정론적으로 한다. z 는 건드리지 않는다 —
# 히어로 빌딩은 원저작이 지면 정렬돼 있고, 미형성 바운드로 ground() 를 하면 오히려
# 공중에 뜬다(scene_5 부유 건물의 진짜 원인).
BLDG_POOL = {
    "/Game/Building/Library/Kit_Hero_Bldg/LevelInstance/Bldg_Hero_Mid_SFC_A01": 23.0,
    "/Game/Building/Library/Kit_Hero_Bldg/LevelInstance/Bldg_Hero_Mid_SFC_B01": 30.0,
}
# x-반장 (도로 진행 방향). 회랑 침범 계산에만 쓴다 — 요각이 0 이 아니면 건물의 y-방향
# 점유폭이 half_w 가 아니라 half_w*|cos| + half_l*|sin| 이 되기 때문이다. 커맨드릿에서는
# LevelInstance 바운드가 미형성이라 실측이 불가하므로 에디터 세션 값의 상한을 쓴다.
# 과대추정은 건물을 도로에서 더 멀리 밀 뿐이라 침범 방향으로는 안전하다.
BLDG_HALF_L = {
    "/Game/Building/Library/Kit_Hero_Bldg/LevelInstance/Bldg_Hero_Mid_SFC_A01": 34.0,
    "/Game/Building/Library/Kit_Hero_Bldg/LevelInstance/Bldg_Hero_Mid_SFC_B01": 42.0,
}
FLANK_YAW_JITTER = 5.0            # 측면 건물 요각 지터(도). ±10 에서 축소.
# 요각 보정만으로도 침범은 0 이 되지만, 지터가 클수록 건물이 회랑 밖으로 더 밀려나
# 가로 협곡이 벌어진다(±10° 는 B동 기준 6.9 m 추가). 실제 가로의 전면이 거의 평행한
# 점을 감안해 5° 로 둔다.
# Low_CHG_Modern_A01 은 3심 판정에서 "검은 유리 큐브 = 미완성 맵" 지적으로 퇴출 (08-25)
# 건물 풀 확장 실패 기록 (2026-08-24 밤): SFE_A01/B01·NYG_Triangle_B01 을 넣은 장면은
# -game 로드~첫 프레임에서 D3D12 페이탈이 재현된다 (기지 장면은 같은 시각 정상 렌더 —
# 머신 아닌 내용 상관 실측). 신규 히어로 빌딩 추가는 장면당 1종씩 단독 검증 후 편입할 것.
TREE_POOL = [
    "/Game/Prop/Kit_Tree_Maple_Red/Mesh/Tree_Maple_Red_A",
    "/Game/Prop/Kit_Tree_Alder/Mesh/Tree_Alder_A",
    "/Game/Prop/Kit_Tree_Birch/Mesh/SM_Tree_Birch_a",
    "/Game/Prop/Kit_Tree_Birch/Mesh/SM_Tree_Birch_c",
]
PROP_POOL = [   # (경로, 인도 배치 확률) — v5: 생활감 증량 (판정단: 공허함이 최대 감점)
    ("/Game/Prop/Kit_Trashcan_A/Mesh/SM_Trashcan_A_01", 0.7),
    ("/Game/Prop/Kit_StopSign_A/Mesh/SM_StopSign_A", 0.4),
    ("/Game/Prop/Kit_Cone_C_A/Mesh/SM_Cone_C_A", 0.35),
    ("/Game/Prop/Kit_NewsDispenser_A/Mesh/SM_NewsDispenser_A_01", 0.5),
    ("/Game/Prop/Kit_BusStopSign_A/Mesh/SM_BusStopSign_A", 0.3),
]
# 기상·시간 프리셋 (2026-08-29). 각 항목은 (가중치, 태양 세기, 안개 밀도, 태양 pitch,
# 색온도, 가로등 점등확률) 를 서로 정합하게 묶는다. 개별 파라미터를 따로 굴리면
# "안개는 짙은데 그림자는 쨍한" 물리적으로 불가능한 조합이 나온다(구판의 실제 결함).
WEATHER = [
    dict(w=0.34, name="흐림",       overcast=True,  sun_int=(1.5, 3.2),  fog=(0.0030, 0.0055),
         pitch=(-62, -28), temp=(5400, 6600), lamps=True),
    dict(w=0.22, name="짙은 흐림",  overcast=True,  sun_int=(0.9, 1.8),  fog=(0.0055, 0.0090),
         pitch=(-70, -40), temp=(6000, 7200), lamps=True),
    dict(w=0.18, name="비 온 뒤",   overcast=True,  sun_int=(2.4, 4.4),  fog=(0.0020, 0.0040),
         pitch=(-55, -22), temp=(5000, 6200), lamps=0.5),
    dict(w=0.14, name="옅은 해",    overcast=False, sun_int=(5.0, 8.0),  fog=(0.0015, 0.0030),
         pitch=(-50, -20), temp=(4800, 5800), lamps=0.2),
    dict(w=0.08, name="맑음",       overcast=False, sun_int=(8.0, 12.0), fog=(0.0008, 0.0018),
         pitch=(-52, -18), temp=(4400, 5400), lamps=0.05),
    dict(w=0.04, name="이른 아침",  overcast=False, sun_int=(3.0, 5.5),  fog=(0.0045, 0.0080),
         pitch=(-22, -8),  temp=(4200, 5000), lamps=0.6),
]


def _weighted_choice(table):
    r = random.random() * sum(t["w"] for t in table)
    acc = 0.0
    for t in table:
        acc += t["w"]
        if r <= acc:
            return t
    return table[-1]


VEH_EXCLUDE = ("vehCar_vehicle02",  # 후면 저폴리 붕괴 (3심 v3 판정 실측)
               "trailer", "Trailer", "Wheel", "Brake", "Door", "MotionBlur", "Trans", "No_Wheel", "Steering",
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


def spawn_bldg(path, x, y_cm, yaw):
    """저수준 배치 — y 를 그대로 쓴다. 회랑 계산은 호출자 몫."""
    w = unreal.load_asset(path)
    if w is None:
        log("BLDG 로드 실패 " + path)
        return None
    bl = act.spawn_actor_from_class(unreal.LevelInstance, unreal.Vector(x, y_cm, 0),
                                    unreal.Rotator(0, 0, yaw))
    bl.set_editor_property("world_asset", w)
    return bl


def occupancy_half_w_cm(path, yaw):
    """요각 yaw 로 놓인 건물이 y 축 방향으로 점유하는 반폭(cm).

    직사각 평면의 축정렬 바운드: half_w*|cos| + half_l*|sin|. 기존 코드는 |cos|=1,
    |sin|=0 을 가정해 half_w 만 썼고, 그래서 요각 지터가 있는 측면 건물이 도로 회랑을
    파고들었다(인도 위로 벽면이 내려앉는 장면의 원인).
    """
    t = math.radians(yaw)
    hw = BLDG_POOL[path]
    hl = BLDG_HALF_L.get(path, hw * 1.6)
    return (hw * abs(math.cos(t)) + hl * abs(math.sin(t))) * 100


def place_flank(path, x, side, yaw):
    """도로 양옆 배치 — 회랑(|y| < CORRIDOR_CM) 밖을 요각까지 반영해 보장한다."""
    y = side * (CORRIDOR_CM + occupancy_half_w_cm(path, yaw) + random.uniform(0, 600))
    return spawn_bldg(path, x, y, yaw)


def visibility(labels, step=8):
    """OBB 레이캐스트 z-버퍼로 라벨별 가시비(보이는 픽셀 / 자기 실루엣 픽셀)를 낸다.

    왜 필요한가. 이 생성기는 절두체 안에 있고 4px 이상이면 모두 GT 박스를 붙여 왔다.
    출하된 464장면 4,320 라벨을 재검사하니 **20.7~22.8% 가 다른 차량에 완전히 가려**
    한 픽셀도 보이지 않는데 온전한 박스를 달고 있었고, 그런 라벨이 하나 이상인 장면이
    76~80% 였다. 검출기 학습셋에서 이는 순수한 오탐 지도다.

    구현 제약: UE 5.8 내장 파이썬에는 numpy 가 없다(실측). `build_scene` 이 main 의
    try/except 안이라 ImportError 가 삼켜져 산출물이 0개가 되므로 **순수 파이썬**으로 쓴다.
    step=8 에서 장면당 0.058s (실측, 라벨 9개 기준).
    """
    boxes = []
    for lb in labels:
        p, s = lb["relative_position_m"], lb["size_m"]
        yr = math.radians(lb["relative_yaw_deg"])
        boxes.append((p["x"], p["y"], p["z"], s["l"] / 2, s["w"] / 2, s["h"] / 2,
                      math.cos(yr), math.sin(yr)))
    n = len(boxes)
    am = [0] * n
    hit = [0] * n
    v = step / 2.0
    while v < H:
        dz = -(v - CY) / FY
        u = step / 2.0
        while u < W:
            dy = (u - CX) / FX
            best = 1e18
            bi = -1
            for i, (px, py, pz, ex, ey, ez, c, sn) in enumerate(boxes):
                # 광선 원점(카메라)=0, 방향 (1, dy, dz) 를 박스 로컬로 옮긴다
                lox = -px * c - py * sn
                loy = px * sn - py * c
                loz = -pz
                ldx = c + dy * sn
                ldy = -sn + dy * c
                ldz = dz
                tmin, tmax, ok = 0.0, 1e18, True
                for lo, ld, e in ((lox, ldx, ex), (loy, ldy, ey), (loz, ldz, ez)):
                    if abs(ld) < 1e-12:
                        if lo < -e or lo > e:
                            ok = False
                            break
                        continue
                    t1 = (-e - lo) / ld
                    t2 = (e - lo) / ld
                    if t1 > t2:
                        t1, t2 = t2, t1
                    if t1 > tmin:
                        tmin = t1
                    if t2 < tmax:
                        tmax = t2
                    if tmin > tmax:
                        ok = False
                        break
                if ok and tmax >= tmin:
                    am[i] += 1
                    if tmin < best:
                        best = tmin
                        bi = i
            if bi >= 0:
                hit[bi] += 1
            u += step
        v += step
    return [0.0 if am[i] == 0 else hit[i] / float(am[i]) for i in range(n)]


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
    # 건물 하부 채움: 지면이 인도까지만 있으면 건물이 허공 위에 떠 보인다(scene_75 공극 실측).
    # 도로 타일을 측면 스트립으로 깔아 블록 전체를 아스팔트로 채운다 (도심 주차장/뒷길 외관).
    for k in range(ROAD_TILES):
        for yc in (-4200, -2100, 2100, 4200):
            a = top0(spawn_sm(road, k * seg - rb.origin.x, yc - rb.origin.y))
            a.add_actor_world_offset(unreal.Vector(0, 0, -3), False, False)  # 본도로보다 3cm 아래
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

    # 기상·시간 프리셋. 판정 기준은 "예쁜 사진"이 아니라 "평범한 실사"이므로 표본을
    # 일상적 조건에 몰아준다 — 황혼·역광 같은 극적 조건은 사진으로는 좋아 보여도
    # 렌더 티가 드러나고, 무엇보다 실제 주행 데이터의 다수가 아니다.
    # 가중치 합 1.0. 노면 재질이 젖은 상태로 고정돼 있어(위 주석) 마른 노면을 전제하는
    # 쨍한 정오는 비중을 낮게 둔다 — 마른 노면 변형을 만들면 그때 재조정할 것.
    preset = _weighted_choice(WEATHER)
    overcast = preset["overcast"]
    sun_int = random.uniform(*preset["sun_int"])
    fog_d = random.uniform(*preset["fog"])
    lamps_on = preset["lamps"] if isinstance(preset["lamps"], bool) else random.random() < preset["lamps"]
    if lamps_on:
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

    # 소실점 폐쇄: 도로 끝 너머(x=140~220m)에 타워 행렬 — "백색 공허" 제거 (3심 1순위)
    endx = ROAD_TILES * 2000
    # 이 두 행은 도로가 끝난 뒤(x > 120m)라 회랑 규칙이 적용되지 않는다 — 오히려 도로
    # 축 근처에 놓아야 소실점이 막힌다. 따라서 y 를 직접 준다.
    for k in range(3):
        spawn_bldg(random.choice(list(BLDG_POOL)), endx + 2000 + k * 3500,
                   random.choice((-1, 1)) * random.uniform(0, 900), random.uniform(0, 360))
    for k in range(3):                        # 2열 — 측면 틈으로 새는 수평선 봉쇄
        spawn_bldg(random.choice(list(BLDG_POOL)), endx + 9000 + k * 4000,
                   random.choice((-1, 1)) * random.uniform(1200, 3400), random.uniform(0, 360))
    x = 2000.0
    n_bldg = 0
    while x < ROAD_TILES * 2000 + 4000:
        for side in (-1, 1):
            if random.random() < 0.8:
                path = random.choice(list(BLDG_POOL))
                jit = random.uniform(-FLANK_YAW_JITTER, FLANK_YAW_JITTER)
                if place_flank(path, x + random.uniform(-500, 500), side,
                               jit + (0 if side < 0 else 180)):
                    n_bldg += 1
        x += random.uniform(3500, 5500)

    fog = act.spawn_actor_from_class(unreal.ExponentialHeightFog,
                                     unreal.Vector(0, 0, 0), unreal.Rotator(0, 0, 0))
    fog.component.set_editor_property("fog_density", fog_d)
    fog.component.set_editor_property("fog_height_falloff", 0.2)

    # 카메라/센서 층 (크롭 판정 2026-08-24 밤: 게임 티 1순위 = 노이즈·광학결함·롤오프 부재)
    ppv = act.spawn_actor_from_class(unreal.PostProcessVolume,
                                     unreal.Vector(0, 0, 0), unreal.Rotator(0, 0, 0))
    ppv.set_editor_property("unbound", True)
    st = ppv.get_editor_property("settings")            # 구조체 복사본 — 재설정 필수
    def ov(name, val):
        st.set_editor_property("override_" + name, True)
        st.set_editor_property(name, val)
    ov("film_grain_intensity", random.uniform(0.15, 0.35))
    ov("scene_fringe_intensity", random.uniform(0.15, 0.4))   # 색수차 — 1.2 는 엣지 글리치(실측)
    ov("vignette_intensity", random.uniform(0.3, 0.5))
    ov("bloom_intensity", random.uniform(0.12, 0.28))        # 0.4~0.7 은 소실점 백화(3심 재지적)
    ov("auto_exposure_bias", random.uniform(-1.1, -0.5))     # 하이라이트 보존 (백화 억제)
    ppv.set_editor_property("settings", st)

    sun_pitch = random.uniform(*preset["pitch"])
    sun_yaw = random.uniform(0, 360)
    sun = act.spawn_actor_from_class(unreal.DirectionalLight, unreal.Vector(0, 0, 1000),
                                     unreal.Rotator(0, sun_pitch, sun_yaw))
    sun.light_component.set_intensity(sun_int)
    # 접지 밀착 그림자 — 판정단 최종 라운드 1순위 지적(차량 부양감)의 정공 해결
    sun.light_component.set_editor_property("contact_shadow_length", 0.06)
    sun.light_component.set_editor_property("contact_shadow_length_in_ws", False)
    # 시안 단색조 타파 — 물리 색온도 사용 (3심: 청백 일변도 재지적)
    sun.light_component.set_editor_property("use_temperature", True)
    sun.light_component.set_editor_property("temperature", random.uniform(*preset["temp"]))
    act.spawn_actor_from_class(unreal.SkyLight, unreal.Vector(0, 0, 1000), unreal.Rotator(0, 0, 0))
    act.spawn_actor_from_class(unreal.SkyAtmosphere, unreal.Vector(0, 0, 0), unreal.Rotator(0, 0, 0))

    cam_z = random.uniform(130.0, 185.0)          # 승용차~SUV 시점
    cam_yaw = random.uniform(-6.0, 6.0)
    cam = act.spawn_actor_from_class(unreal.CameraActor, unreal.Vector(0, 0, cam_z),
                                     unreal.Rotator(0, 0, cam_yaw))
    cam.set_editor_property("auto_activate_for_player", unreal.AutoReceiveInput.PLAYER0)

    # 차로 경계: 도로 키트의 도색 buffer 스트립 (플레인+기본머티리얼은 저대비로 비가시 실측)
    buf = unreal.load_asset("/Game/Road/Kit_City_Road/SM_ROAD_19_5_0_19_buffer")
    if buf:
        bb2 = buf.get_bounds()
        for ly in (-350.0, 350.0):
            lx = 0.0
            while lx < ROAD_TILES * 2000:
                a = spawn_sm(buf, lx - bb2.origin.x, ly - bb2.origin.y, 0, 0)
                wo, we = a.get_actor_bounds(False)
                a.add_actor_world_offset(unreal.Vector(0, 0, 1.5 - (wo.z + we.z)), False, False)
                lx += 2 * bb2.box_extent.x
    decals = [m for m in (unreal.load_asset(a) for a in
              (find_asset(DECAL_DIR, ("Painted_Arrow",)) + find_asset(DECAL_DIR, ("Parking_Line",))
               + find_asset(DECAL_DIR, ("SprayPaint",))[:6])) if m]
    for _ in range(random.randint(3, 8)):
        if decals:
            a = spawn_sm(random.choice(decals), random.uniform(600, ROAD_TILES * 2000),
                         random.uniform(-900, 900), 0, random.uniform(0, 360))
            wo, we = a.get_actor_bounds(False)
            a.add_actor_world_offset(unreal.Vector(0, 0, 1.5 - (wo.z - we.z)), False, False)

    n_veh = random.randint(*N_VEH_RANGE)
    placed, labels, tries = [], [], 0
    while len(labels) < n_veh and tries < 100:
        tries += 1
        m = random.choice(vehicles)
        e = m.get_bounds().box_extent
        r = math.hypot(e.x / 100, e.y / 100)
        mode = random.random()
        if mode < 0.34 and placed:
            # 정체 열: 직전 차량 뒤 6~9m 같은 차선 (실도로 밀도의 핵심 — 3심 지적).
            # ★ 2026-08-29 정정: 이전 판은 직전 차량의 **카메라 좌표**(라벨 값)를 세계
            # 좌표로 오용했다. 카메라는 ±6° 요각 지터가 있어, x=30m 지점에서 최대 3m,
            # 전 구간 최대 5.0m(차로 폭의 143%)의 횡 어긋남이 생긴다 — 한 차선에 나란히
            # 서야 할 정체 열이 옆 차선으로 새거나 차선을 밟는다(모사 2만 회: 중앙값
            # 1.13m, 90분위 3.08m). 세계 좌표는 placed 에 있으므로 그것을 쓴다.
            px, py, _pr = placed[-1]
            x = px + random.uniform(6.0, 9.0)
            y = py + random.uniform(-0.3, 0.3)
            yaw = (180.0 if y < 0 else 0.0) + random.uniform(-4, 4)
            if x > 55:            # 도로 끝(세계 좌표 기준) 밖이면 버린다
                continue
        elif mode < 0.52:   # 노변 주차열 증량 (생활감)
            # 평행주차: 갓길(|y|≈8.2m)에 차선과 나란히
            x = random.uniform(6, 48)
            side = random.choice((-1, 1))
            # 연석에서 역산한다. 고정 7.4~7.9m 는 차폭·요각을 무시해 차체 바깥면–연석
            # 간격이 중앙값 1.6~1.9m(최대 2.2m)까지 벌어졌다 — 실제 평행주차 0.2~0.5m 의
            # 4~8배이고, 6차로 환산 시 최외곽 차로를 통째로 점유하는 폭이다.
            _jit = math.radians(4.0)
            y = side * (ROAD_HALF_W_CM / 100.0 - e.y / 100.0
                        - abs(e.x / 100.0 * math.sin(_jit))
                        - random.uniform(0.20, 0.45))
            yaw = (180.0 if side < 0 else 0.0) + random.uniform(-4, 4)
        else:
            x = random.uniform(6, 48)
            y = random.uniform(-7.5, 7.5)
            if mode < 0.88:
                # 우측통행 차선 의미론: **y>0 이 우측 차선**(순방향), y<0 이 마주 옴.
                # ★ 2026-08-29 정정: UE 좌수계에서 +y 는 카메라 오른쪽이다(이 파일의
                # bbox2d 가 u = CX + FX*y/x 로 그렇게 투영한다). 이전 판은 y<0 을 우측
                # 차선으로 잘못 적어 **좌측통행 장면**을 만들고 있었다 — 출하된 464장면
                # 4,323 라벨 실측에서 순방향의 88.6% 가 화면 왼쪽, 마주옴의 90.6% 가
                # 화면 오른쪽이었다. 평가 도메인(Udacity CrowdAI, 캘리포니아)은 우측통행이므로
                # 학습·평가가 좌우 거울상이었다.
                yaw = (180.0 if y < 0 else 0.0) + random.uniform(-8, 8)
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

    # 가시비 부여 — 완전 가림 라벨은 지우지 않고 ignore 로 표시한다(3D-only GT 보존).
    _vis_src = [l for l in labels if "bbox2d" in l]
    if _vis_src:
        for _lb, _v in zip(_vis_src, visibility(_vis_src)):
            _lb["visibility"] = round(_v, 3)
            if _v < 0.15:
                _lb["ignore"] = True

    lvl.save_current_level()
    with open(os.path.join(OUTPUT_DIR, "scene_%d.json" % i), "w") as f:
        json.dump(dict(scene=i, level=path,
                       camera=dict(fov_deg=FOV, z_m=round(cam_z / 100, 3), yaw_deg=round(cam_yaw, 2), width=W, height=H),
                       sun=dict(pitch=round(sun_pitch, 1), yaw=round(sun_yaw, 1)),
                       weather=dict(preset=preset["name"], sun_intensity=round(sun_int, 2),
                                    fog_density=round(fog_d, 5), lamps=bool(lamps_on)),
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
