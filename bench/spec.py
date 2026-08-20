"""마이크로벤치 공통 스펙.

모든 구현(NumPy / Numba / PyTorch)이 동일한 연산을 하도록 상수와 형상을 여기서만 정의한다.
값의 출처는 MetaDrive 소스이며, 근거를 각 줄에 남긴다. 값을 바꾸면 PAPER.md 3.4절도 같이 고쳐야 한다.
"""

# --- MetaDrive 복제 파라미터 (출처: 소스 직접 확인) ---
DT_PHYS = 0.02          # base_env.py:190  physics_world_step_size=2e-2
DECISION_REPEAT = 5     # base_env.py:191  decision_repeat=5
DT = DT_PHYS * DECISION_REPEAT   # 0.1s = 제어 주기 10Hz
DETECT_RADIUS = 50.0    # base_env.py:170  lidar distance=50
NUM_OTHERS = 8          # 사용자 결정 2026-08-18 (base_env.py:170 기본값은 0)
HORIZON = 1000          # metadrive_env.py:58

# --- 차량 물리 상수 ---
MAX_SPEED_KMH = 80.0    # pg_space.py:233 max_speed_km_h=ConstantSpace(80)
MAX_SPEED = MAX_SPEED_KMH / 3.6          # 22.22 m/s
import numpy as _np
MAX_STEER = float(_np.deg2rad(40.0))     # pg_space.py:232 max_steering=ConstantSpace(40) [deg]
WHEELBASE = 2.8         # m, 자전거 모델 축거 (MetaDrive 는 Bullet 강체 — 근사값, 논문에 명시)
MAX_ACCEL = 5.0         # m/s^2 (근사값 — MetaDrive 는 엔진 힘 곡선. 논문에 명시)
COLLISION_RADIUS = 2.5  # m, 원-원 충돌 근사 (MetaDrive 는 박스 충돌 — 근사, 논문에 명시)

# --- 관측 정규화 상수 (설치된 metadrive 0.4.3 소스 확인) ---
NAVI_POINT_DIST = 50.0  # base_navigation.py:20
CURVE_RADIUS_MAX = 60.0 # pg_space.py:286 BoxSpace(min=25, max=60)
CURVE_ANGLE_MAX = 135.0 # pg_space.py:287 (deg)
N_LANES = 3             # 편도 차선 수 — MetaDrive X맵 실측 (current_ref_lanes == 3)
TOTAL_WIDTH = 18.0      # 실측: MAX_LANE_NUM=3, MAX_LANE_WIDTH=4.5 → (3+1)*4.5 (2026-08-20 프로브)

# --- 관측 차원 (MetaDrive 51차원 정합; 벤치 커널의 구 40차원은 kernel_*.py 에만 남음) ---
EGO_DIM = 9
NAVI_DIM = 10
OTHER_DIM = 4
OBS_DIM = EGO_DIM + NAVI_DIM + NUM_OTHERS * OTHER_DIM   # = 51

# --- 보상 (metadrive_env.py:72~78 확인값) ---
DRIVING_REWARD = 1.0
SPEED_REWARD = 0.1
SUCCESS_REWARD = 10.0
OUT_OF_ROAD_PENALTY = 5.0
CRASH_VEHICLE_PENALTY = 5.0

# --- 상태 레이아웃 ---
# ego: (E, 4)  = x, y, heading, speed
# npc: (E, V, 4) = x, y, heading, speed
STATE_DIM = 4

# --- 교차로 기하 (절차적 생성 최소판) ---
ARM_LENGTH = 60.0       # 교차로 각 진입로 길이 m
LANE_WIDTH = 3.5        # m
