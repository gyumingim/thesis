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
OUTPUT_DIR = os.environ.get("CS_OUT", r"C:\ue\out_cs2")   # 검증 세트는 CS_OUT 으로 분리
W, H, FOV = 1280, 720, 90.0
FX = FY = (W / 2) / math.tan(math.radians(FOV / 2))   # 640.0
CX, CY = W / 2, H / 2
CAM_Z_CM = 150.0
N_VEH_RANGE = (14, 26)   # x 범위를 6~48 m 에서 6~114 m 로 넓혔으므로 밀도 유지에 필요
ROAD_TILES = 6                    # 20m x 6 = 120m
ROAD_SEG_CM = 2000.0
ROAD_LEN_CM = ROAD_TILES * ROAD_SEG_CM        # 12000 = 120 m
ROAD_X_END_CM = ROAD_LEN_CM                   # 타일 원점 정렬 후 아스팔트 끝
SIDEWALK_Z_CM = 15.0              # 인도 보행면 높이 (연석 턱). 도로면은 z=0.
# ★ 2026-08-29: 이전 판은 타일을 바운드 **중심** 기준으로 깔아 아스팔트가 -10~110 m 였는데
#   나머지 요소는 전부 0~120 m 를 가정했다 — 원단 10 m 가 비고 원점 뒤 10 m 가 낭비됐다.
#   타일을 +seg/2 옮겨 0~120 m 로 맞춘다.
ROAD_HALF_W_CM = 1050
SIDEWALK_HALF_W_CM = 150.0
CORRIDOR_CM = ROAD_HALF_W_CM + 2 * SIDEWALK_HALF_W_CM + 50   # 1400 — 건물 금지 회랑 반폭
# ★ 2026-08-29: 1300 은 인도 바깥 끝(1350)보다 좁아 후퇴거리 지터가 50 cm 미만이면
#   건물이 인도를 파고들었다(재모사 6.05%, 깊이 최대 0.50 m).
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
BLDG_HALF_L = {   # 에디터 세션 실측 (v7 로그: A01 e(29,23), B01 e(30,30))
    "/Game/Building/Library/Kit_Hero_Bldg/LevelInstance/Bldg_Hero_Mid_SFC_A01": 29.0,
    "/Game/Building/Library/Kit_Hero_Bldg/LevelInstance/Bldg_Hero_Mid_SFC_B01": 30.0,
}
LANE_W_M = 3.5                    # 실제 도시부 차로 폭
LANE_CTRS = (-8.75, -5.25, -1.75, 1.75, 5.25, 8.75)      # 편도 3차로 × 2
LANE_LINES_CM = (-875.0, -525.0, -175.0, -20.0, 20.0, 175.0, 525.0, 875.0)
# ★ 2026-08-29: 도로 폭 21 m 에 선이 y=±3.5 m 두 줄뿐이라 **7 m 밴드 3개**로 보였다
#   (실제의 2배). 차량 y 도 U(-7.5, 7.5) 연속이라 차로 개념이 없었고, 주행차의 24.1%
#   가 도색선을 밟고 있었다. 중앙 이중선(±20 cm)이 없으면 가운데 두 차로가 한 덩어리로
#   읽혀 6차로로 보이지 않는다.
FLANK_YAW_JITTER = 1.5            # 측면 건물 요각 지터(도). ±10 → ±5 → ±1.5.
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
         pitch=(-62, -28), temp=(6300, 7100), lamps=True),
    dict(w=0.22, name="짙은 흐림",  overcast=True,  sun_int=(0.9, 1.8),  fog=(0.0055, 0.0090),
         pitch=(-70, -40), temp=(6600, 7400), lamps=True),
    dict(w=0.18, name="비 온 뒤",   overcast=True,  sun_int=(2.4, 4.4),  fog=(0.0020, 0.0040),
         pitch=(-55, -22), temp=(6200, 7000), lamps=0.5),
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


def ground_at(a, z_cm=0.0):
    """바닥면을 z=z_cm 에 맞춘다. ground() 의 일반화.

    2026-08-29: 인도 스트립은 상면을 z=0 에 맞춘 뒤 +15 cm 올라가는데(연석 턱),
    그 위의 가로등·가로수·소품은 전부 ground()(바닥을 z=0=도로면에 맞춤)를 써서
    **장면당 26.7개가 보행면에 15 cm 매몰**돼 있었다. 접지면도 그림자도 없이 밑동이
    잘려 보인다(scene_100.png 좌측 인도 실측). 인도 위 물체는 z_cm=SIDEWALK_Z_CM.
    """
    wo, we = a.get_actor_bounds(False)
    a.add_actor_world_offset(unreal.Vector(0, 0, z_cm - (wo.z - we.z)), False, False)
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


def _halfproj(ux, uy, c, s, ex, ey):
    return ex * abs(ux * c + uy * s) + ey * abs(-ux * s + uy * c)


def obb_hit(a, b, pad=0.2):
    """a, b = (cx, cy, yaw_deg, ex, ey) [m]. 회전 사각형 4축 SAT 겹침 판정.

    이전 판은 외접원(반지름 hypot(ex, ey))으로 걸렀다. 횡방향에도 종방향 여유를 강제해
    배제원/실제 바닥면적이 승용 2.1~2.3배·버스 3.1배였고, 최소 중심간 거리가 차로 폭의
    147~347% 라 **인접 차로 병주가 구조적으로 불가능**했다(출하 라벨에서 횡거리 4 m 미만
    쌍이 단 한 쌍도 없다). 정체열 모드는 시도의 65.6% 가 이 원으로 기각됐다.
    """
    ax, ay, ayaw, aex, aey = a
    bx, by, byaw, bex, bey = b
    ca, sa = math.cos(math.radians(ayaw)), math.sin(math.radians(ayaw))
    cb, sb = math.cos(math.radians(byaw)), math.sin(math.radians(byaw))
    dx, dy = bx - ax, by - ay
    for ux, uy in ((ca, sa), (-sa, ca), (cb, sb), (-sb, cb)):
        ra = _halfproj(ux, uy, ca, sa, aex, aey)
        rb = _halfproj(ux, uy, cb, sb, bex, bey)
        if abs(dx * ux + dy * uy) > ra + rb + pad:
            return False
    return True


def occupancy_half_l_cm(path, yaw):
    """요각 yaw 로 놓인 건물이 x 축(도로 진행) 방향으로 점유하는 반장(cm)."""
    t = math.radians(yaw)
    hw = BLDG_POOL[path]
    hl = BLDG_HALF_L.get(path, hw * 1.6)
    return (hl * abs(math.cos(t)) + hw * abs(math.sin(t))) * 100


def place_flank(path, x, side, yaw, setback):
    """도로 양옆 배치 — 회랑 밖 보장 + **장면 공통 후퇴거리**로 전면선 정렬.

    이전 판은 건물마다 uniform(0, 600) 을 독립으로 굴려 벽면 거리가 13.0~19.0 m 로
    흩어졌다(중앙 16.0, sd 1.74). 실제 가로는 전면선이 정렬돼 있으므로 후퇴거리를
    장면 단위로 공유하고 개별 지터는 ±60 cm 만 준다. 산포의 절반은 요각이 만드는
    파사드 비평행 성분이었으므로 FLANK_YAW_JITTER 축소와 함께 적용해야 효과가 난다.
    """
    y = side * (CORRIDOR_CM + occupancy_half_w_cm(path, yaw)
                + setback + random.uniform(-60, 60))
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


NEAR = 0.3


def cam_basis(roll, pitch, yaw):
    """UE Rotator(roll, pitch, yaw) 의 회전행렬. **pitch 양수 = 기수 상향**이라
    Ry 의 부호가 오른손 표준과 반대다(검증: pitch+2 의 전방벡터 z=+0.035).

    반환값 R 에 대해 카메라 좌표는 p_cam = Rᵀ (p_world − cam_pos) 다.
    yaw 만 줄 때 이전 판의 2D 회전과 정확히 일치함을 확인했다(부동소수 한계).
    """
    cr, sr = math.cos(math.radians(roll)), math.sin(math.radians(roll))
    cp, sp = math.cos(math.radians(pitch)), math.sin(math.radians(pitch))
    cy, sy = math.cos(math.radians(yaw)), math.sin(math.radians(yaw))
    rz = ((cy, -sy, 0.0), (sy, cy, 0.0), (0.0, 0.0, 1.0))
    ry = ((cp, 0.0, -sp), (0.0, 1.0, 0.0), (sp, 0.0, cp))
    rx = ((1.0, 0.0, 0.0), (0.0, cr, -sr), (0.0, sr, cr))

    def mm(a, b):
        return tuple(tuple(sum(a[i][k] * b[k][j] for k in range(3)) for j in range(3))
                     for i in range(3))
    return mm(mm(rz, ry), rx)


def to_cam(px, py, pz, cam, rot):
    """세계 좌표(m) → 카메라 좌표(전방 x, 우 y, 상 z)."""
    r = cam_basis(*rot)
    d = (px - cam[0], py - cam[1], pz - cam[2])
    return tuple(sum(r[k][i] * d[k] for k in range(3)) for i in range(3))


def bbox2d(lb):
    """GT 3D 박스의 핀홀 투영. (bbox2d, truncation, near_clipped) 를 돌려준다.

    2026-08-29 정정 두 가지.
    (a) 이전 판은 8모서리 루프 **안**에서 x<=0.3 이면 곧바로 None 을 냈다 — 한 모서리만
        근평면 뒤에 있어도 라벨 전체가 버려진다(클리핑이 아니라 폐기). 지금은 앞쪽 모서리와
        변∩평면 보간점으로 잘린 다면체의 볼록껍질을 만들어 투영한다. 원근투영은 x>0 에서
        사영변환이므로 볼록다면체의 극값은 꼭짓점에서 달성되고, 전쌍 보간이 인접쌍을
        포함하므로 꼭짓점을 모두 덮는다(대각쌍 보간점은 껍질 내부라 bbox 를 넓히지 않는다).
    (b) 프레임 밖을 클램프만 하고 **잘린 정도를 기록하지 않았다**. 출하 4,323 라벨 중
        8.4% 가 클램프됐고, 프레임내/amodal 면적비 중앙값 0.453 · 최소 0.0025 였다 —
        0.25% 만 보이는 차량이 온전한 차량과 같은 GT 를 받는다. 이제 truncation 을 함께
        내보내고 0.7 초과는 ignore 로 표시한다.
    """
    p, s = lb["relative_position_m"], lb["size_m"]
    l2, w2, h2 = s["l"] / 2, s["w"] / 2, s["h"] / 2
    yr = math.radians(lb["relative_yaw_deg"])
    c, sn = math.cos(yr), math.sin(yr)
    pts = []
    for dx in (-l2, l2):
        for dy in (-w2, w2):
            for dz in (-h2, h2):
                pts.append((p["x"] + dx * c - dy * sn,
                            p["y"] + dx * sn + dy * c, p["z"] + dz))
    near_clipped = any(q[0] <= NEAR for q in pts)
    proj = [q for q in pts if q[0] > NEAR]
    if not proj:
        return None, 1.0, True
    if near_clipped:
        for a in pts:
            for b in pts:
                if a[0] > NEAR >= b[0]:
                    t = (NEAR - a[0]) / (b[0] - a[0])
                    proj.append((NEAR, a[1] + t * (b[1] - a[1]), a[2] + t * (b[2] - a[2])))
    us = [CX + FX * q[1] / q[0] for q in proj]
    vs = [CY - FY * q[2] / q[0] for q in proj]
    fu0, fu1, fv0, fv1 = min(us), max(us), min(vs), max(vs)
    u0, u1 = max(0.0, fu0), min(float(W), fu1)
    v0, v1 = max(0.0, fv0), min(float(H), fv1)
    if u1 - u0 < 4 or v1 - v0 < 4:
        return None, 1.0, near_clipped
    full = (fu1 - fu0) * (fv1 - fv0)
    trunc = 0.0 if full <= 0 else max(0.0, 1.0 - ((u1 - u0) * (v1 - v0)) / full)
    return ([round(u0, 1), round(v0, 1), round(u1, 1), round(v1, 1)],
            round(trunc, 3), near_clipped)


def build_scene(i, road, sw, pole, vehicles, crosswalk=None, seed_base=3000, trees=(), props=()):
    random.seed(seed_base + i)
    level_path = "%s/gen_%d" % (LEVEL_DIR, i)
    open_clean_level(level_path)

    rb = road.get_bounds()
    seg = 2 * rb.box_extent.x
    for k in range(ROAD_TILES):
        top0(spawn_sm(road, k * seg + seg / 2 - rb.origin.x, -rb.origin.y))
    # 건물 하부 채움: 지면이 인도까지만 있으면 건물이 허공 위에 떠 보인다(scene_75 공극 실측).
    # 도로 타일을 측면 스트립으로 깔아 블록 전체를 아스팔트로 채운다 (도심 주차장/뒷길 외관).
    for k in range(ROAD_TILES):
        for yc in (-8400, -6300, -4200, -2100, 2100, 4200, 6300, 8400):
            a = top0(spawn_sm(road, k * seg + seg / 2 - rb.origin.x, yc - rb.origin.y))
            a.add_actor_world_offset(unreal.Vector(0, 0, -3), False, False)  # 본도로보다 3cm 아래
    # 원경 지면 — 스케일 타일로 도로 끝 너머(소실점 타워 아래)까지 덮는다.
    # ★ 2026-08-29 검증 렌더에서 확인: 지면이 x=120 m 에서 끝나는데 타워는 186 m 부터라
    #   **건물이 허공에 뜬 채 렌더**됐다(verify10/scene_0). 화면 가장자리 하늘 띠도 같은 원인.
    #   등배 타일로 덮으면 액터가 수백 개가 되므로 10배 스케일 타일 몇 장으로 대신한다.
    for fx in (1, 2, 3):                       # x 100~700 m 구간
        for fy in (-2, -1, 0, 1, 2):           # |y| ≤ 300 m
            a = top0(spawn_sm(road, fx * 20000.0 - rb.origin.x, fy * 20000.0 - rb.origin.y))
            a.set_actor_scale3d(unreal.Vector(10.0, 10.0, 1.0))
            a.add_actor_world_offset(unreal.Vector(0, 0, -6), False, False)  # 근경보다 6cm 아래
    if crosswalk and random.random() < 0.6:       # 횡단보도를 도로 위에 겹쳐 깔기 (데칼처럼 2cm 위)
        cw_x = random.uniform(8, ROAD_LEN_CM / 100.0 - 15) * 100
        cb = crosswalk.get_bounds()
        a = top0(spawn_sm(crosswalk, cw_x - cb.origin.x, -cb.origin.y))
        a.add_actor_world_offset(unreal.Vector(0, 0, 2), False, False)

    sb = sw.get_bounds()
    for k in range(int(ROAD_LEN_CM // 600) + 2):
        for side in (-1, 1):
            a = top0(spawn_sm(sw, k * 600 - sb.origin.x,
                              side * (ROAD_HALF_W_CM + 150) - sb.origin.y))
            a.add_actor_world_offset(unreal.Vector(0, 0, SIDEWALK_Z_CM), False, False)

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
    # 인도 액터에는 분리 검사가 없어 소품끼리·가로등·가로수와 겹치는 장면이 52.9% 였다.
    # 또 가로등 k*2200, 가로수 k*2200+1100, 인도 6 m, 도로 20 m 주기가 전부 x=0 에
    # 위상 고정이라 **시드를 바꿔도 위상 분산이 정확히 0** 이었다 — 데이터셋 평균에서
    # 합성 판별 신호가 된다. 위상 오프셋을 장면 시드로 굴린다.
    occ_prop = []

    def _prop_free(px, py, pr):
        if any(math.hypot(px - ox, py - oy) < pr + orr for ox, oy, orr in occ_prop):
            return False
        occ_prop.append((px, py, pr))
        return True

    phase = random.uniform(0, 2200)
    if lamps_on:
        for k in range(1, ROAD_TILES):
            for side, yaw in ((-1, 0), (1, 180)):
                lx = min(k * 2200 + phase, ROAD_X_END_CM)
                if _prop_free(lx, side * (ROAD_HALF_W_CM + 150), 60.0):
                    ground_at(spawn_sm(pole, lx, side * (ROAD_HALF_W_CM + 150), 0, yaw),
                              SIDEWALK_Z_CM)
    for k in range(1, ROAD_TILES):                     # 가로수: 가로등 사이 중간점
        for side in (-1, 1):
            if trees and random.random() < 0.6:
                tx = min(k * 2200 + 1100 + phase, ROAD_X_END_CM)
                if _prop_free(tx, side * (ROAD_HALF_W_CM + 200), 90.0):
                    ground_at(spawn_sm(random.choice(trees), tx,
                                       side * (ROAD_HALF_W_CM + 200), 0,
                                       random.uniform(0, 360)), SIDEWALK_Z_CM)
    for k in range(ROAD_TILES * 2):                    # 소품: 인도 위 산포
        for m, pr in props:
            if random.random() < pr * 0.5:
                side = random.choice((-1, 1))
                sx = random.uniform(500, ROAD_LEN_CM)
                sy = side * (ROAD_HALF_W_CM + random.uniform(120, 260))
                nm = m.get_name()
                # 표지판은 통행 방향을 향해야 한다(임의 방향이면 뒷면·측면이 보인다).
                # y>0 연석은 +x 로 오는 차량을, y<0 연석은 -x 로 오는 차량을 상대한다.
                if "StopSign" in nm:
                    yaw = (180.0 if side > 0 else 0.0) + random.uniform(-6, 6)
                elif "BusStopSign" in nm:            # 날개형 — 차로와 나란히
                    yaw = (90.0 if side > 0 else 270.0) + random.uniform(-6, 6)
                else:
                    yaw = random.uniform(0, 360)
                if _prop_free(sx, sy, 45.0):
                    ground_at(spawn_sm(m, sx, sy, 0, yaw), SIDEWALK_Z_CM)

    # 소실점 폐쇄: 도로 끝 너머(x=140~220m)에 타워 행렬 — "백색 공허" 제거 (3심 1순위)
    # ★ 2026-08-29: 건물-건물 분리 검사가 아예 없었다. 2만 장면 모사에서 같은 쪽 인접 쌍의
    #   87.7% 가 서로 관통했고(깊이 중앙 16.9 m, 장면당 3.4쌍) 소실점 타워는 100% 장면에서
    #   겹쳤다. 원인은 구조적이다 — x 중심간격 평균 45 m 인데 반장 합이 평균 59 m 다.
    #   구간 예약(측면)과 AABB 예약(타워)으로 막고, x 스텝을 반장 합 이상으로 넓힌다.
    setback = random.uniform(150.0, 450.0)     # 장면 공통 후퇴거리 (전면선 정렬)
    occ_side = {-1: [], 1: []}

    def reserve_side(side, cx, hl):
        lo, hi = cx - hl, cx + hl
        if any(lo < a1 and a0 < hi for a0, a1 in occ_side[side]):
            return False
        occ_side[side].append((lo, hi))
        return True

    occ_tower = []

    def reserve_tower(cx, cy, hl, hw):
        b = (cx - hl, cx + hl, cy - hw, cy + hw)
        if any(b[0] < o[1] and o[0] < b[1] and b[2] < o[3] and o[2] < b[3] for o in occ_tower):
            return False
        occ_tower.append(b)
        return True

    # 소실점 폐쇄 타워: 도로가 끝난 뒤라 회랑 규칙이 아니라 y 를 직접 준다. 다만 회전
    # 후 x-반extent 상한(=hypot(30,30)≈42.4 m)만큼 뒤로 물려야 본도로를 침범하지 않는다.
    maxhl_cm = max(math.hypot(BLDG_POOL[q], BLDG_HALF_L[q]) for q in BLDG_POOL) * 100
    tx = ROAD_X_END_CM + maxhl_cm + 1500
    for n_row, yspan in ((3, 900.0), (3, 3400.0)):
        for k in range(n_row):
            for _try in range(8):
                q = random.choice(list(BLDG_POOL))
                yw = random.uniform(0, 360)
                bx = tx + k * (2 * maxhl_cm + 1000) + random.uniform(-1000, 1000)
                by = random.choice((-1, 1)) * random.uniform(0, yspan)
                if reserve_tower(bx, by, occupancy_half_l_cm(q, yw), occupancy_half_w_cm(q, yw)):
                    spawn_bldg(q, bx, by, yw)
                    break
        tx += 2 * maxhl_cm + 6000

    x = 2000.0
    n_bldg = 0
    while x < ROAD_X_END_CM + 4000:
        for side in (-1, 1):
            if random.random() < 0.8:
                bpath = random.choice(list(BLDG_POOL))
                jit = random.uniform(-FLANK_YAW_JITTER, FLANK_YAW_JITTER)
                byaw = jit + (0 if side < 0 else 180)
                bx = x + random.uniform(-500, 500)
                if not reserve_side(side, bx, occupancy_half_l_cm(bpath, byaw)):
                    continue
                if place_flank(bpath, bx, side, byaw, setback):
                    n_bldg += 1
        # 스텝은 밀도용, 예약은 관통 방지용 — 역할을 나눈다. 6200~7000 은 장면당 약
        # 4.5동으로 "공허함" 감점을 피하면서 예약 실패율을 낮게 유지하는 값이다.
        x += random.uniform(6200, 7000)

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
    # 그레인·블룸이 조도와 완전 무상관이었다(corr = -0.003). sun_int 동적범위가 13.3배인데
    # 그레인은 항상 U(0.15,0.35) — 어두운 장면일수록 노이즈가 늘어야 카메라답다.
    dim = max(0.0, min(1.0, (12.0 - sun_int) / 11.1))         # 0=맑음 1=어두움
    ov("film_grain_intensity", 0.10 + 0.28 * dim + random.uniform(-0.03, 0.03))
    ov("scene_fringe_intensity", random.uniform(0.15, 0.4))   # 색수차 — 1.2 는 엣지 글리치(실측)
    ov("vignette_intensity", random.uniform(0.3, 0.5))
    ov("bloom_intensity", 0.24 - 0.12 * dim + random.uniform(-0.03, 0.03))   # 0.4~0.7 은 소실점 백화
    # 100% 음수(U(-1.1,-0.5))라 화면이 평균 42% 어둡게 고정돼 있었다. 백화 억제라는
    # 원래 의도는 유지하되 평균을 -0.25 로 올리고 양쪽으로 연다.
    ov("auto_exposure_bias", random.gauss(-0.25, 0.30))
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
    if overcast:
        # overcast 플래그가 정의만 되고 소비처가 0곳이었다(장면의 73.8%가 흐림 계열인데도).
        # 태양 원반각을 키워 그림자 가장자리를 풀어 준다. UI 상한이 5° 근방이므로 3~6 만.
        sun.light_component.set_editor_property("light_source_angle", random.uniform(3.0, 6.0))
        sun.light_component.set_editor_property("contact_shadow_length", 0.02)
    act.spawn_actor_from_class(unreal.SkyLight, unreal.Vector(0, 0, 1000), unreal.Rotator(0, 0, 0))
    act.spawn_actor_from_class(unreal.SkyAtmosphere, unreal.Vector(0, 0, 0), unreal.Rotator(0, 0, 0))

    cam_z = random.uniform(130.0, 185.0)          # 승용차~SUV 시점
    cam_yaw = random.uniform(-6.0, 6.0)
    # ★ 2026-08-29: 이전 판은 pitch=roll=0, x=y=0 고정이라 (a) 자차가 21 m 도로의 정중앙
    #   (중앙선 위)에 걸쳐 있었고 (b) **지평선이 v=360.0 px 에 프레임 간 표준편차 0.0** 으로
    #   못박혀 있었다. 단일 스칼라의 분산이 0 이면 데이터셋 수준에서 즉시 합성 판별이 된다.
    # 자차는 **순방향 차로**에만 둔다. 우측통행이므로 y>0 이다 — 음수 차로를 섞으면
    # 대시캠이 역주행 차로에 서서 마주오는 차를 자기 차선에서 보는 장면이 된다
    # (검증 세트 10장에서 절반이 그랬다).
    # 최외곽 차로(8.75)는 연석 주차열(y≈9.0~9.4)과 맞닿아 실제로는 주차 차로다.
    # 주행 중인 대시캠은 안쪽 두 차로에 둔다.
    cam_y = random.choice((1.75, 5.25)) + random.gauss(0.0, 0.15)
    cam_pitch = random.gauss(-1.0, 1.2)
    cam_roll = random.gauss(0.0, 0.4)
    cam_rot = (cam_roll, cam_pitch, cam_yaw)
    cam = act.spawn_actor_from_class(unreal.CameraActor,
                                     unreal.Vector(0, cam_y * 100.0, cam_z),
                                     unreal.Rotator(cam_roll, cam_pitch, cam_yaw))
    cam.set_editor_property("auto_activate_for_player", unreal.AutoReceiveInput.PLAYER0)

    # 차로 경계: 도로 키트의 도색 buffer 스트립 (플레인+기본머티리얼은 저대비로 비가시 실측)
    buf = unreal.load_asset("/Game/Road/Kit_City_Road/SM_ROAD_19_5_0_19_buffer")
    if buf:
        bb2 = buf.get_bounds()
        for ly in LANE_LINES_CM:
            lx = 0.0
            while lx < ROAD_LEN_CM:
                a = spawn_sm(buf, lx - bb2.origin.x, ly - bb2.origin.y, 0, 0)
                wo, we = a.get_actor_bounds(False)
                a.add_actor_world_offset(unreal.Vector(0, 0, 1.5 - (wo.z + we.z)), False, False)
                lx += 2 * bb2.box_extent.x
    # 방향성 도색(화살표·주차선)과 낙서를 한 리스트에 합쳐 같은 uniform(0,360) 으로
    # 굴리고 있었다 — 도로축 45° 이상 기운 것이 50.2%, 즉 차로 화살표가 사선으로 눕는다.
    # 낙서는 자유 요각이 정상이므로 풀을 나눈다.
    _load = lambda pats: [m for m in (unreal.load_asset(a) for a in pats) if m]
    arrows = _load(find_asset(DECAL_DIR, ("Painted_Arrow",)))
    plines = _load(find_asset(DECAL_DIR, ("Parking_Line",)))
    graffi = _load(find_asset(DECAL_DIR, ("SprayPaint",))[:6])

    def _drop(mesh, dx, dy, dyaw):
        a = spawn_sm(mesh, dx, dy, 0, dyaw)
        wo, we = a.get_actor_bounds(False)
        a.add_actor_world_offset(unreal.Vector(0, 0, 1.5 - (wo.z - we.z)), False, False)

    for _ in range(random.randint(0, 3)):          # 차로 화살표: 차로 중심, 도로축 정렬
        if arrows:
            _drop(random.choice(arrows), random.uniform(600, ROAD_LEN_CM - 600),
                  random.choice(LANE_CTRS) * 100.0,
                  random.choice((0.0, 180.0)) + random.uniform(-2, 2))
    for _ in range(random.randint(0, 2)):          # 주차선: 연석 안쪽, 도로축 정렬
        if plines:
            _drop(random.choice(plines), random.uniform(600, ROAD_LEN_CM - 600),
                  random.choice((-1, 1)) * random.uniform(850, 1020),
                  random.choice((0.0, 180.0)) + random.uniform(-2, 2))
    for _ in range(random.randint(2, 5)):          # 낙서: 자유 요각 유지
        if graffi:
            _drop(random.choice(graffi), random.uniform(600, ROAD_LEN_CM - 600),
                  random.uniform(-900, 900), random.uniform(0, 360))

    n_veh = random.randint(*N_VEH_RANGE)
    placed, labels, tries = [], [], 0
    while len(labels) < n_veh and tries < 150:   # 새 기각 경로가 시도를 더 쓴다
        tries += 1
        m = random.choice(vehicles)
        e = m.get_bounds().box_extent
        mode = random.random()
        if mode < 0.34 and placed:
            # 정체 열: 직전 차량 뒤 6~9m 같은 차선 (실도로 밀도의 핵심 — 3심 지적).
            # ★ 2026-08-29 정정: 이전 판은 직전 차량의 **카메라 좌표**(라벨 값)를 세계
            # 좌표로 오용했다. 카메라는 ±6° 요각 지터가 있어, x=30m 지점에서 최대 3m,
            # 전 구간 최대 5.0m(차로 폭의 143%)의 횡 어긋남이 생긴다 — 한 차선에 나란히
            # 서야 할 정체 열이 옆 차선으로 새거나 차선을 밟는다(모사 2만 회: 중앙값
            # 1.13m, 90분위 3.08m). 세계 좌표는 placed 에 있으므로 그것을 쓴다.
            px, py, pyaw, _pex, _pey = placed[-1]
            # 앞차의 요각을 상속한다. 이전 판은 새 y 의 부호로 요각을 **재결정**해
            # |Δyaw|>90° 인 배치가 6.31%(그런 쌍 포함 장면 15.0%) 나왔다 — 원인의 91%는
            # 앞차가 자유요각으로 놓인 경우였다(중앙선 넘김은 9%뿐).
            _ax = abs(((pyaw + 180) % 360) - 180)
            if min(_ax, abs(_ax - 180)) > 20:      # 앞차가 도로 정렬이 아니면 열을 만들지 않는다
                continue
            _fwd = 1.0 if _ax < 90 else -1.0       # 앞차 진행이 +x 인가
            x = px - _fwd * random.uniform(6.0, 9.0)   # 언제나 앞차 '뒤'에 붙는다
            y = py + random.uniform(-0.3, 0.3)
            if (y * py) <= 0.0:                    # 열이 중앙선을 넘지 않게 반사
                y = py - (y - py)
            yaw = pyaw + random.uniform(-2, 2)
            if x < 6.0 or x > ROAD_X_END_CM / 100.0 - 5.0:
                continue
        elif mode < 0.52:   # 노변 주차열 증량 (생활감)
            # 평행주차: 갓길에 차선과 나란히. x 도 도로 전 구간으로 폈다 — 6~48 m 로
            # 묶어 두면 원경 연석이 비어 보인다.
            x = random.uniform(6, ROAD_X_END_CM / 100.0 - 6.0)
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
            # x 를 도로 전 구간에 퍼뜨리되 **근경을 더 뽑는다** — 원경만 차면 화면이
            # 비어 보인다. 지수 0.55 는 반대로 원경 편향이었다(검증 세트에서 중앙값
            # 75.4 m, 25 m 이내 12%). 1.4 로 바꿔 중앙값 47 m, 25 m 이내 27% 로 맞춘다.
            x = 6.0 + (ROAD_X_END_CM / 100.0 - 12.0) * (random.random() ** 1.4)
            if mode < 0.88:
                # 우측통행 차선 의미론: **y>0 이 우측 차선**(순방향), y<0 이 마주 옴.
                # ★ 2026-08-29 정정: UE 좌수계에서 +y 는 카메라 오른쪽이다(이 파일의
                # bbox2d 가 u = CX + FX*y/x 로 그렇게 투영한다). 이전 판은 y<0 을 우측
                # 차선으로 잘못 적어 **좌측통행 장면**을 만들고 있었다 — 출하된 464장면
                # 4,323 라벨 실측에서 순방향의 88.6% 가 화면 왼쪽, 마주옴의 90.6% 가
                # 화면 오른쪽이었다. 평가 도메인(Udacity CrowdAI, 캘리포니아)은 우측통행이므로
                # 학습·평가가 좌우 거울상이었다.
                # 차로 중심에 이산 배치 — 연속 U(-7.5,7.5) 는 차로 개념이 없어
                # 주행차의 24.1% 가 도색선을 밟았다.
                y = random.choice(LANE_CTRS) + random.gauss(0.0, 0.20)
                yaw = (180.0 if y < 0 else 0.0) + random.uniform(-8, 8)
            else:
                yaw = random.uniform(0, 360)   # 회전 중/무단 주차 등 자유
                _t = math.radians(yaw)
                _hy = abs(e.x / 100.0 * math.sin(_t)) + abs(e.y / 100.0 * math.cos(_t))
                _lim = ROAD_HALF_W_CM / 100.0 - _hy - 0.2
                if _lim <= 0.5:               # 자유요각이 연석을 넘는 조합은 버린다
                    continue
                y = random.uniform(-_lim, _lim)
        _bo = m.get_bounds().origin           # 로컬 바운드 중심(cm) — 피벗과 다르다
        _cy, _sy = math.cos(math.radians(yaw)), math.sin(math.radians(yaw))
        cand = (x + (_bo.x * _cy - _bo.y * _sy) / 100.0,
                y + (_bo.x * _sy + _bo.y * _cy) / 100.0,
                yaw, e.x / 100.0, e.y / 100.0)
        if any(obb_hit(cand, o) for o in placed):
            continue
        a = ground(spawn_sm(m, x * 100, y * 100, 0, yaw))
        rf = random.random()
        a.static_mesh_component.set_default_custom_primitive_data_float(1, pack_rf(rf))
        wo, _ = a.get_actor_bounds(False)
        placed.append(cand)
        # 라벨은 카메라 좌표계. yaw 만이던 2D 회전을 roll·pitch 까지 반영한 3D 변환으로
        # 바꿨다(yaw 만 줄 때 이전 판과 부동소수 한계까지 일치). relative_yaw_deg 는
        # 여전히 yaw 성분만 쓴다 — pitch·roll 이 ±3° 이내라 박스 자체의 방위 오차가
        # 30 m 거리에서 3 px 미만이기 때문이다.
        rel_x, rel_y, rel_z = to_cam(wo.x / 100.0, wo.y / 100.0, wo.z / 100.0,
                                     (0.0, cam_y, cam_z / 100.0), cam_rot)
        lb = dict(mesh=m.get_name(), paint_rf=round(rf, 3),
                  relative_position_m=dict(x=rel_x, y=rel_y, z=rel_z),
                  relative_yaw_deg=((yaw - cam_yaw + 180) % 360) - 180,
                  size_m=dict(l=2 * e.x / 100, w=2 * e.y / 100, h=2 * e.z / 100))
        bb, trunc, nclip = bbox2d(lb)
        if bb:
            lb["bbox2d"] = bb
            lb["truncation"] = trunc
            lb["near_clipped"] = bool(nclip)
            if trunc > 0.7:
                lb["ignore"] = True
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
        # ★ level 은 반드시 레벨 경로여야 한다. 이전 판은 건물 루프가 같은 이름
        # (path)을 덮어써서 출하된 464/464 JSON 이 마지막 건물 에셋 경로를 기록했다.
        assert level_path.startswith(LEVEL_DIR)
        json.dump(dict(scene=i, level=level_path,
                       camera=dict(fov_deg=FOV, z_m=round(cam_z / 100, 3),
                                   y_m=round(cam_y, 3), yaw_deg=round(cam_yaw, 2),
                                   pitch_deg=round(cam_pitch, 2), roll_deg=round(cam_roll, 2),
                                   width=W, height=H),
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
