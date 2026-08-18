# STATUS

마지막 갱신: 2026-08-18

## 전체 목표

가벼운(경량) 자체 시뮬레이터로 자율주행 강화학습 환경을 만들고,
**동일 wall-clock 예산**에서 고충실도 시뮬레이터와 비교하는 논문을 쓴다.

## 세부 목표

1. 경량 시뮬레이터 자체 구현 — 렌더링 없음, 벡터 상태 관측, 대량 병렬
2. 고충실도 비교군(MetaDrive)과 **같은 과제·같은 관측·같은 알고리즘**으로 정렬
3. 동일 wall-clock 학습 → **교차 평가**(경량에서 학습한 정책을 고충실도에서 평가)
4. 역전 지점과 실패 모드를 찾아 보고

## 했던 일 (2026-08-18)

- 선행연구 1차 출처 확인 (README 아닌 실제 소스 열람)
  - HighJax (HumanCompatibleAI, MIT, 2026-03 생성, 현재도 활발) — highway-env의 JAX 재구현.
    `highjax/env.py` 확인: gymnax API, flax dataclass 상태, 이산 5행동, 관측 (n_veh, n_feat) 기본 5x5.
    → **"경량 JAX 주행 시뮬을 만든다" 자체는 선점됨.**
  - GPUDrive (Emerge-Lab) — 1M FPS. `pyproject.toml` 확인: Madrona/CMake/CUDA 빌드, repo 622MB, Waymo 데이터셋 필요.
  - Waymax (waymo-research) — JAX, Waymo Open Motion Dataset 필요.
  - MetaDrive (Apache-2.0, 별 1.2k) — 절차적 생성, 데이터셋 불필요, 1000~1500 FPS.
    `metadrive/obs/state_obs.py` 확인: ego 6차원 + navi 10차원 + 라이다 광선.
  - highway-env (Farama, 별 3.3k) — 순수 파이썬 2D, 초당 수백~수천.
- 하드웨어 실측: RTX 4060 Laptop(VRAM 8GB), Ryzen 7 8845HS 16스레드, RAM 14GB(여유 ~7GB), 디스크 여유 74GB
- 논문 주장 확정: **동일 wall-clock 비교** (사용자 결정, 2026-08-18)
- 작업 범위 확정: `/home/karma/thesis` 만. ros2_ws/drone 은 보지 않음 (사용자 지시, 2026-08-18)

## 하고 있는 일

- **스택 검토 (2026-08-18)** — 사용자 제안: Python+NumPy+Numba 자체 시뮬 → Custom RL Env API
  → PPO/SAC/Custom RL → PyTorch → TensorBoard/W&B
  - 동의: PyTorch+PPO(PufferLib이 CPU시뮬+PyTorch로 400k~4M SPS 달성), 시뮬 모듈 분해, TensorBoard
  - **반대: Custom RL Environment API** — gymnasium 1.2.3의 VectorEnv/SyncVectorEnv/AsyncVectorEnv가
    이미 설치돼 있음(확인 완료). 자체 API는 MetaDrive 어댑터를 추가로 요구하고 기존 PPO 구현 재사용을 막음
  - **반대: Custom RL(알고리즘 자작)** — 시뮬 비교 논문에 RL 구현 차이가 교란변수로 들어감.
    두 시뮬에 동일한 PPO 구현 하나(CleanRL 또는 SB3)를 써야 비교 성립
  - **미해결 리스크: Numba 처리량 미지수.** PufferLib 문서 기준 NumPy벡터+PyTorch ~3,500 SPS /
    순수파이썬 100k~500k / C 100M+. MetaDrive가 1000~1500 FPS이므로 3,500 SPS면 격차 2~3배에 그쳐
    "연산량 압도" 전제가 무너짐. Numba가 어디 떨어지는지는 실측 필요
- 시뮬레이터 스택 최종 확정 대기 (마이크로벤치 승인 대기)
- RL 알고리즘 미정 (SAC는 리플레이버퍼 기반이라 대량병렬 이점 못 살림 + 연속행동 전용 → 주력 부적합)
- 주행 과제 미정

## 할 일

1. [보류] 스택 결정 → 그 전까지 코딩 금지 (사용자 지시)
2. [보류] RL 알고리즘 결정
3. [보류] 주행 과제 확정 — MetaDrive 시나리오 중 택일하면 경량 시뮬 스펙이 따라옴
4. MetaDrive 실제 설치 후 이 노트북에서의 **실측 FPS** 측정 (문헌값 1000~1500은 남의 장비 기준)
5. 경량 시뮬 목표 처리량 실측 근거 확보

## 사용 기술 (확정된 것만)

- 비교군: MetaDrive (Apache-2.0, pip 설치, 절차적 생성)
- 현재 설치됨: gymnasium 1.2.3, numpy 1.26.4, networkx, pydantic
- 미설치: torch, jax, numba

## 문제점 및 해결방안

| 문제 | 해결방안 | 상태 |
|---|---|---|
| "경량 시뮬 만들었다"는 novelty 선점됨 (HighJax, GPUDrive) | 시뮬은 도구로 두고, 주장을 실험 결과(동일 wall-clock + 교차평가)로 옮김 | 방향 확정 |
| 동일 wall-clock 비교만 하면 결과가 자명(샘플 1000배 차) | **교차 평가 필수** — 경량에서 학습→고충실도에서 평가. 역전 지점·실패 모드가 기여 | 사용자 승인 대기 |
| CARLA는 RAM 14GB(여유 7GB)로 실무 최소치 16GB 미달 | 비교군을 MetaDrive로. CARLA는 여유 있을 때만 | 사용자 승인 대기 |
| 두 시뮬 관측이 다르면 비교 무효 | MetaDrive `state_obs.py` 구조를 경량 시뮬이 복제 (ego 6 + navi 10 + 광선) | 설계 반영 예정 |
| VRAM 8GB — 픽셀 관측 대량 병렬 불가 | 벡터 상태 관측만 사용. 경량성 주장과도 일치 | 확정 |
