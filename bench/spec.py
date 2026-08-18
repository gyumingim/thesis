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
# 주의: max_steering / max_accel 은 MetaDrive 소스에서 아직 확인하지 않은 값이다.
# SPS(처리량)에는 영향이 없어 벤치에는 무해하나, 실제 시뮬 구현 시 반드시 대조할 것.
WHEELBASE = 2.8         # m, 자전거 모델 축거 (미확인 — 실제 시뮬에서 대조 필요)
MAX_STEER = 0.5         # rad (미확인)
MAX_ACCEL = 5.0         # m/s^2 (미확인)
MAX_SPEED = 30.0        # m/s
COLLISION_RADIUS = 2.5  # m, 원-원 충돌 근사 (미확인)

# --- 관측 차원 ---
# ego 4 (speed, heading_sin, heading_cos, lane_offset) + navi 4 + 주변차 8대 x 4 (rel x,y,vx,vy)
EGO_DIM = 4
NAVI_DIM = 4
OTHER_DIM = 4
OBS_DIM = EGO_DIM + NAVI_DIM + NUM_OTHERS * OTHER_DIM   # = 40

# --- 상태 레이아웃 ---
# ego: (E, 4)  = x, y, heading, speed
# npc: (E, V, 4) = x, y, heading, speed
STATE_DIM = 4

# --- 교차로 기하 (절차적 생성 최소판) ---
ARM_LENGTH = 60.0       # 교차로 각 진입로 길이 m
LANE_WIDTH = 3.5        # m
