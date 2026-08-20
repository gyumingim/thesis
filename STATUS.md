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

- **파일럿 본실험 실행 중 (2026-08-20 시작, ~2시간)** — 사용자 승인 (축소판)
  - 구성: 30분 × 2시드 × {custom(1024env×64step), metadrive(12env×256step)}, **순차 실행**
    (동시 실행은 CPU 경합으로 wall-clock 공정성 오염 — run_pilot.sh 주석 참조)
  - PPO 업데이트 하이퍼파라미터는 양쪽 동일(CleanRL 기본). 수집 구성만 각자 처리량 최적
  - ppo.py 수정 4: --time-budget-s / --checkpoint-every-s (agent + obs_rms 저장)
  - evaluate.py: 동결 정규화 적용 교차 평가 (custom/metadrive 타깃, 결정론 정책)
  - 종료 후: 4런 × 7체크포인트를 metadrive 시험장에서 평가 → wall-clock 성공률 곡선
- 평가 시드(1000+)는 학습 시드(1,2)와 분리

## 할 일

1. [보류] 스택 결정 → 그 전까지 코딩 금지 (사용자 지시)
2. [보류] RL 알고리즘 결정
3. [보류] 주행 과제 확정 — MetaDrive 시나리오 중 택일하면 경량 시뮬 스펙이 따라옴
4. MetaDrive 실제 설치 후 이 노트북에서의 **실측 FPS** 측정 (문헌값 1000~1500은 남의 장비 기준)
5. 경량 시뮬 목표 처리량 실측 근거 확보

## 사용 기술 (확정된 것만)

- 환경 API: **Gymnasium VectorEnv** (사용자 확정 2026-08-18). 자체 API 만들지 않음
- RL 알고리즘: **PPO, 기존 구현 사용** (사용자 확정 2026-08-18). 자작하지 않음
- PPO 구현: **CleanRL** 추천 (승인 대기)
  - 근거: `cleanrl/ppo.py:162`가 `gym.vector.SyncVectorEnv`를 직접 사용 → 어댑터 불필요
  - SB3는 자체 VecEnv API(공식문서: "not the same as Gym API", reset()이 튜플 아닌 obs만 반환)라
    gymnasium.vector 지원이 issue #1745로 미해결 → 어댑터 필요하므로 탈락
  - 라이선스 MIT (LICENSE 파일 직접 확인. GitHub API는 NOASSERTION으로 오표기)
  - 단일 파일이라 두 시뮬에 동일 구현이 쓰였음을 `diff`로 증명 가능
- 학습 프레임워크: PyTorch (미설치)
- 로깅: TensorBoard (CleanRL에 `SummaryWriter` 내장)
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
