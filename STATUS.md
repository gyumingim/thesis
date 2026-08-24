# STATUS

<<<<<<< HEAD
마지막 갱신: 2026-08-24 16:00

## 2026-08-24 핵심 사건: V=3 본판 완료 — 전이 붕괴 발견 (논문 주 결과 반전)

- 21일 밤 PC 종료로 배치4 사망 → 24일 12:19 재기동, 15:24 완료. 배치5(3h) 진행 중.
- **V=3 최종(1h) 전이 0%×3시드** — 그러나 초반 10~30분 피크 13~33%(평균 23%) 후 붕괴.
- 원인 규명(§6.3): in-domain 5분 포화(85%) 후의 순수 보상 최적화가 판정 경계 잔차를
  착취(스폰 직후 조향 커밋 지문, custom 이탈 0% ↔ MD 이탈 100%). 정규화 이동·지지집합
  가설은 프로브로 기각. = 시뮬레이션 최적화 편향(SOB)의 벽시계·행동 지문 실측.
- 논문 초록·§1.2·§5·§6.2·§6.3(신설)·§7 전면 갱신. "경량이 이긴다" → "정합·지지집합을
  다 맞춰도 과최적화가 전이를 파괴한다 + 두 병리 분리 진단"으로 주장 전환.
- 다음 후보 실험(사용자 결정 대기): (ii) 판정 경계 보수화 재학습 1h×1, (iii) 경량
  사전학습 10분 → MD 미세조정 50분 캐스케이드 vs MD 60분 네이티브.
=======
마지막 갱신: 2026-08-24 (장비 이전 — 4060 Laptop/Linux → RTX 5080/Windows)
>>>>>>> 63c7ee1 (docs(status): 장비 이전·윈도우 이식·언리얼 렌더 규명 기록)

## 전체 목표

가벼운(경량) 자체 시뮬레이터로 자율주행 강화학습 환경을 만들고,
**동일 wall-clock 예산**에서 고충실도 시뮬레이터(MetaDrive)와 비교하는 논문을 쓴다.
논문 본문: PAPER.md (v2, 실측 이력: docs/PAPER_worklog_v1.md)

## 지금 어디에 있나

**2026-08-21 밤 파이프라인(배치4·배치5)은 실행되지 않았다.** 따라서 §6.2 의
경량 V=3 3시드 결과와 3시간 예산확장 곡선은 여전히 미측정이다.

작업 장비를 노트북(RTX 4060 Laptop / Ryzen 7 8845HS / Linux)에서
**데스크톱(RTX 5080 16GB / Ryzen 7 7800X3D 8C16T / RAM 64GB / Windows 11)** 으로 옮겼다.
§6.2 는 동일 wall-clock 비교이므로 조건마다 장비가 다르면 표가 성립하지 않는다.
→ **본판 전 조건을 이 장비에서 재측정한다** (bench/run_all.sh).

## 이 장비 환경 (구축 완료, 검증됨)

| 항목 | 값 | 비고 |
|---|---|---|
| Python | 3.11.9 | metadrive 0.4.3 의 requires_python 이 `<3.12` |
| torch | 2.9.1+cu128 | arch_list 에 sm_120 포함, capability (12,0) 실측 |
| metadrive / gymnasium / panda3d | 0.4.3 / 1.2.3 / 1.10.13 | 코드 주석이 못 박은 버전 |
| numpy / numba | 2.4.6 / 0.67.0 | |

검증 통과:
- `bench/test_env.py` T1~T5 전부 통과. 완성 환경 SPS 969,757 (노트북 1,002,242 — 사실상 동일)
- `bench/test_equivalence.py` 세 구현 동치 (obs 최대차 2.4e-07, reward 차 0, done 불일치 0)
- MetaDrive 12워커 AsyncVectorEnv 가 윈도우 `spawn` 에서 정상 기동 (워커 12 + 메인 1)

## 윈도우 이식에서 실제로 고친 것

1. **cp949 인코딩** — 한국어 윈도우 콘솔이 유니코드 출력에서 죽는다 → `PYTHONUTF8=1` (bench/env.sh)
2. **경로/인터프리터 하드코딩** — run_main*.sh 5벌이 각자 `/home/karma/thesis` + `.venv/bin/python`
   → OS 분기를 `bench/env.sh` 한 곳으로. 본판 전체는 `bench/run_all.sh` 하나로 통합
3. **`.sh` 개행** — `.gitattributes` 로 LF 고정 (CRLF 가 붙으면 bash 가 파싱 실패)
4. **`n_vehicles` 기본값 함정** — f8aa92c 에서 2→3 으로 바뀌었고 원 run_main.sh 는 기본값에
   의존했다. 그대로 돌리면 V=2 병리 표본이 조용히 V=3 이 된다 → run_all.sh 는 조건마다 명시
5. **벽시계 측정 오염 (ppo.py 수정 6)** — 아래

### ppo.py 수정 6: 벽시계 측정 오염 제거

수식·난수·미니배치 구성은 불변이고 데이터 이동과 커널 선택만 바꾼다.

- (a) 미니배치 인덱스를 에폭당 1회만 GPU 로. 원본은 numpy 인덱스로 CUDA 텐서 6개를
  매 스텝 색인해 스텝마다 호스트→디바이스 전송과 동기화를 일으킨다.
- (b) Adam 을 fused 커널로. 기본 Adam 은 bias correction 에서 파라미터마다 `step.item()`
  을 불러 스텝당 26회 디바이스 동기화가 발생한다.

원인 실측(이 장비): `.item()` 1회 **72.5 us** vs 비동기 커널 11.1 us — 윈도우 WDDM 은
디바이스 동기화가 리눅스보다 한 자릿수 비싸다. 노트북(리눅스)에서 72K SPS 가 나온 코드가
이 장비에서 19K 로 떨어진 원인이 이것이다. 즉 이 수정은 경량 시뮬에 유리한 조작이 아니라
**플랫폼 아티팩트 제거**다.

| | 수정 전 | 수정 후 |
|---|---:|---:|
| 경량 V=3 학습포함 SPS | 22,700 | **43,480** |
| MetaDrive 학습포함 SPS | 905 | **1,076** |
| 격차 | 25× | **40×** (노트북 53×) |

두 시뮬이 같은 ppo.py 를 쓰므로 비교는 공정하다. 논문에 수정 항목으로 명시할 것.

## 역할 분담 (2026-08-24 저녁, 사용자 지시)

- **데스크톱 (RTX 5080 / Windows, 이 저장소) = 언리얼 전용**
- **노트북 (RTX 4060 Laptop / Linux, /home/karma/thesis) = 강화학습 전용**

데스크톱에서 16:05 발사했던 본배치는 역할 변경으로 즉시 중단·폐기 (산출물 없음).
원격: 데스크톱 ↔ 노트북은 Tailscale 로 연결됨 (노트북 = karma / 100.126.163.103).

## 노트북에서 할 일 (강화학습)

```bash
cd ~/thesis && git pull
systemd-inhibit bash bench/run_all.sh    # 절전 방지 포함 (리눅스엔 keepawake.ps1 대신 이것)
```

- 약 13~16h: MD 3시드 → V=3 3시드 → V=2 3시드 → 3h 확장 → 교차평가 → 그림.
  재개 가능(완주 판정 = ckpt/final.pt) — 끊겨도 같은 명령으로 이어 돈다.
- **전 조건을 새 코드로 재측정해야 한다.** ppo.py 수정 6(미니배치 인덱스 전송·fused
  Adam·예산 시계 위치)이 학습 처리량을 바꾸므로, 과거 노트북 수치(66%/5% 등)와
  새 런을 한 표에 섞으면 동일 wall-clock 비교가 깨진다. run_all.sh 가 어차피 전 조건을 돈다.
- 완료 판정: bench_results/main/DONE_ALL 존재 (plot 성공 시에만 기록됨).
- 끝나면 §6.1 처리량 표를 노트북 실측으로 갱신, §6.2 [TBD] 2곳 소거
  (PAPER.md:166 검증(c), PAPER.md:193 V=3 주 결과).

## 언리얼 / 인지 트랙 (재개, 2026-08-24)

이 장비 설치 현황: UE **5.8.1** (`C:\Program Files\Epic Games\UE_5.8`) / CitySample 96GB
(`C:\Users\a3162\Documents\Unreal Projects\CitySample`) / CARLA 0.10.0 (`C:\carla`, py3.12 휠) /
PerceptGen 최소 프로젝트 (`C:\ue\PerceptGen`).

### 상태

- CARLA 경로: **500프레임 완주** (`C:\carla\out\` PNG 500 + JSON 500) — 저장소에서 이미지를
  만드는 코드는 `ue/carla_datagen.py:93` 한 곳뿐이다.
- UE 경로: 장면 생성(`/Game/GenScenes/scene_0~9` + `C:\ue\out_cs\scene_0~9.json`)까지 성공,
  **헤드리스 캡처는 미성공.**

### 캡처 실패 원인 (2026-08-24 규명)

`C:\ue\scripts\cs_capture.bat` 의 두 결함:
1. `start "" /b ... > log 2>&1` — 리다이렉션이 `start` 자신에 걸려 UE 출력이 로그에 안 담긴다
   (`cs_capture.log` 0바이트의 원인). 실패 원인을 볼 수단이 없었다.
2. `timeout /t 180` 후 `taskkill` — UE 로그(CitySample.log)는 `Game Engine Initialized` 와
   Python 초기화까지만 찍히고 끊긴다. 맵 로드도 `HighResShot` 실행도 없다. **부팅 중 잘렸다.**

추가로 `-game -RenderOffscreen -ExecCmds="HighResShot"` 경로 자체가 타이밍에 취약하다
(ExecCmds 는 엔진 초기화 시점에 실행되는데 그때는 맵이 아직 없다).

### 채택할 설계

파이썬 커맨드릿 안에서 **SceneCapture2D → TextureRenderTarget2D → export_render_target**.
부팅 1회로 N장면 처리, 타이밍 경합 없음, 라벨에 적히는 FOV 를 렌더에 실제로 강제할 수 있다.

UE 5.8.1 설치본에서 API 실측 확인:
`SceneCaptureComponent2D.capture_scene()` / `fov_angle` / `capture_source`,
`RenderingLibrary.create_render_target2d` / `export_render_target`,
`SceneCaptureSource.SCS_FINAL_COLOR_LDR`, `TextureRenderTargetFormat.RTF_RGBA8_SRGB`.
MoviePipeline(MRQ)은 이 프로젝트에 미탑재.

### 렌더 외 남은 결손 (코드 근거 확인됨)

- 해상도·출력 포맷이 UE 쪽에 미정의. `scene_build_cs.py:127` 은 `fov_deg=90` 을 하드코딩해
  라벨에 쓰지만 실제 렌더가 그 화각이라는 보장이 없다
- 포스트프로세스·노출 제어 없음, 조명이 전 장면 동일(도메인 랜덤화 0)
- 바닥이 회색 평면 1장, 배경·가림물 없음, 차량 겹침 배제 없음
- 이미지공간 라벨(`bbox2d`)이 UE 쪽에 없음 (CARLA 쪽에만 있음)
- `scene_build_cs.py` 는 레벨이 이미 있으면 `new_level` 이 거부되어 재생성 불가
  (scene_build.py 의 `ensure_level` 은 삭제 후 생성하는데 cs 판엔 그 처리가 없다)

## ⚠ PAPER.md §6.3 정정 필요 (2026-08-24 검증)

`bench/percept_v0.py` 의 "지면평면 거리추정"이 **대수적으로 항등 소거된다.**
`box_corners` 가 하단 모서리를 정확히 `z=-h_cam` 에 놓고 `h_cam` 을 라벨에서 역산하므로
`FX=FY` 조건에서 `d_gp = FX·h_cam/(v1−CY) = x_min` (최근접 바닥 모서리의 종방향 거리).

CARLA 500프레임 1,000건 실측:

```
|d_gp − x_min|                     최대 3.6e-14   ← 부동소수점 오차 수준
오차(d_gp − gt_x) 부호              음수 100.0%
|오차| vs 예측 오프셋 l/2·|cos|+w/2·|sin|   최대차 3.3e-14
 4-15m  σ=0.84m  평균오차 −3.04m
15-30m  σ=1.10m  평균오차 −2.53m
30-50m  σ=1.17m  평균오차 −2.48m
```

σ 0.84/1.10/1.17 은 PAPER.md 게재값과 정확히 일치한다. 그러나 이 σ 는 평면 가정이나
캘리브레이션 오차가 아니라 **"박스 중심 vs 최근접 모서리"라는 정의 차이에서 오는 결정론적
기하 오프셋의 산포**다 (평균오차가 −2.5~−3.0m 로 전부 한쪽으로 쏠린 것이 증거).
B4 관측 노이즈 주입의 σ 로 쓰면 랜덤 노이즈가 아닌 것을 노이즈로 넣는 해석 오류가 된다.

처리 방향(미결정): 논문에 "체계적 편향이지 노이즈가 아니다"로 정정 게재하거나,
추정기를 중심 거리 추정으로 고치거나, `bbox2d` 기반 실검출로 전환.

## 확정된 본판 수치 (노트북 4060/Linux 실측 — 재측정 대상)

- MetaDrive 네이티브: 66% ± 10% (63/57/77)
- 경량 V=2 (지지집합 결함): 5% ± 7% (0/10)
- 경량 V=2 + 퇴화차원 마스킹: 13.5% ± 5% (10/17)
- 역방향(MD정책→경량 V=3): 2% ± 3%
- 동일 시뮬 소거 실험: V=2 정책을 V=2 평가 81/89% ↔ V=3 평가 22/36%
- 처리량: 경량 1.0M SPS vs MetaDrive 12proc 6,965 SPS = 138×

## 보류

- bottleneck 일반화, 노이즈 주입 실험 (위 §6.3 정정이 선행되어야 함)
