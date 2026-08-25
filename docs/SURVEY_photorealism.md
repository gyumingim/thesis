# 렌더 그래픽 사실화(photorealism enhancement) 문헌 서베이

2026-08-25, 조사 에이전트 수행. 인용 38편 전부 export.arxiv.org API 로 제목·저자·연도 대조 검증.
용도: 학위논문 관련연구 절 재료 + 인지 트랙 파이프라인의 학술 위치 규정.

## 1. 고전 image-to-image 번역 계보 (2016~2021)

| 논문 (연도·처소) | 한줄 기여 | arXiv |
|---|---|---|
| pix2pix — Isola et al. (CVPR 2017) | 조건부 GAN 짝지음(paired) I2I 정식화, AMT real-vs-fake 평가 정착 | 1611.07004 |
| CycleGAN — Zhu et al. (ICCV 2017) | 사이클 일관성 비짝(unpaired) 번역 — CG→실사의 출발점 | 1703.10593 |
| SimGAN — Shrivastava et al. (CVPR 2017 Best Paper) | "합성 정제로서의 sim2real" 최초 정식화 | 1612.07828 |
| UNIT (NeurIPS 2017) | 공유 잠재공간 비짝 번역 | 1703.00848 |
| CRN — Chen & Koltun (ICCV 2017) | 시맨틱 레이아웃→사진급 합성(GAN 없이) | 1707.09405 |
| MUNIT (ECCV 2018) | 콘텐츠/스타일 분리 다중모드 번역 | 1804.04732 |
| CUT (ECCV 2020) | 패치 대조학습 비짝 번역 — EPE·REGEN 의 표준 기준선 | 2007.15651 |

GTA→Cityscapes 도메인 적응 갈래: Playing for Data (ECCV 2016, 1608.02192) → FCNs in the Wild
(1612.02649) → PixelDA (CVPR 2017, 1612.05424) → CyCADA (ICML 2018, 1711.03213) →
AdaptSegNet (CVPR 2018, 1802.10349).

공통 한계 = **구조 붕괴**: 사이클/대조 제약은 간접적이라 물체 소멸·환각 빈발. EPE 가 원인을
"데이터셋 간 장면 레이아웃 분포 차이"로 분석. (딥러닝 이전 뿌리: Johnson et al. CG2Real,
IEEE TVCG 2011 — arXiv 미등재.)

## 2. 구조 조건 강화 계보 — "기하 보존" 해법의 진화

| 논문 | 한줄 기여 | arXiv |
|---|---|---|
| pix2pixHD (CVPR 2018) | 시맨틱 조건 고해상 합성 + 다중스케일 판별기 | 1711.11585 |
| Alhaija et al. (IJCV 2018) | 실배경+렌더 객체 기하 정합 증강 (주행) | 1708.01566 |
| SPADE/GauGAN (CVPR 2019) | 공간 적응 정규화 — 조건 씻김 문제 해결 | 1903.07291 |
| OASIS (ICLR 2021) | 분할 기반 판별기 시맨틱 합성 | 2012.04781 |
| **EPE** — Richter et al. (ICCV 2021→TPAMI) | **G-buffer 조건 + 시맨틱 정합 패치 샘플링 + LPIPS 제약** — 구조 붕괴 없는 GTA 사실화의 정점, sKVD 지표 제안 | 2105.04619 |

EPE 직계 후속 (Pasios & Nikolaidis 계열): CARLA2Real (2024, CARLA 플러그인화 ~13FPS,
2410.18238) → REGEN (2025, 비짝 결과를 짝 데이터로 증류, 32.14배 실시간화, 2508.17061) →
HyPER-GAN (2026, G-buffer 유도 실시간 30FPS@1080p, 2603.10604) → **Hybrid Sim2Real
(2026, 디퓨전 사실화 + 분포 정합 I2I 2단 결합 — 본 파이프라인과 설계 논리 최근접, 2605.02291)**.

## 3. 디퓨전 시대 (2021~2026)

기반: **SDEdit** (ICLR 2022, 노이즈 강도로 충실도-사실성 조절 — 본 파이프라인 strength 0.3 의
이론적 직계 조상, 2108.01073) · **ControlNet** (ICCV 2023 Best Paper, 2302.05543) ·
SDXL (2023, 2307.01952).

sim2real 적용: DIDEX (WACV 2024, 2312.01850) · DGInStyle (ECCV 2024, +2.5 mIoU,
2312.03048) · DriveGEN (CVPR 2025, training-free 3D 기하 보존 증강, 2503.11122) ·
Sim2Real Diffusion (2025 RA-L, 지각 갭 40%+ 축소, 2507.00236) · Driving with DINO
(2026, 파운데이션 특징 브리지, 2602.06159) · Ontology-Guided Diffusion (2026, 2603.18719).

비디오 일관성: vid2vid (NeurIPS 2018, 1808.06601) → Video ControlNet (2023, 광류 기반,
2305.19193) → Mirage (2025, 2512.24227) → RealMaster (2026, 2603.23462) → Wavelet
Phase Diffusion (2026, 2607.21628) → AutoWeather4D (2026, G-buffer 이중 패스 비디오
날씨 변환 — 2·3절 계보의 합류점, 2603.26546).

인접 갈래(번역이 아닌 무로부터 생성 — 구분 서술): DriveDreamer (ECCV 2024, 2309.09777) ·
MagicDrive (ICLR 2024, 2310.02601).

## 4. 엔진 내 접근 (후처리와의 대비 축)

Deferred Neural Rendering (SIGGRAPH 2019, 1904.12356) · RGB↔X (SIGGRAPH 2024,
G-buffer↔실사 디퓨전 양방향 — "디퓨전을 렌더러로", 2405.00666) · GeRM (2026, 2604.09304) ·
NeRF (2003.08934) / 3DGS (2308.04079) · GeoSim (CVPR 2021, 2101.06543) · Block-NeRF
(CVPR 2022, 2202.05263) · **UniSim** (CVPR 2023, 폐루프 멀티센서 뉴럴 시뮬, 2308.01898) ·
**NeuRAD** (CVPR 2024, 센서 모델링 포함 주행 NVS, 2311.15260) · Street Gaussians
(ECCV 2024, 2401.01339) · OmniRe (ICLR 2025, 2408.16760).

대비 논점: 재구성 기반은 외형 갭이 작지만 기록 로그 근방으로 시나리오 제한. 엔진 렌더+후처리
(본 연구)는 임의 시나리오가 자유롭되 외형 갭을 후단에서 갚는다 — 상호보완 구도로 서술.

## 5. 평가 관행 3축

1. 사람 실험: AMT real-vs-fake (pix2pix 정착), EPE 는 시간 무제한 쌍대비교로 전 기준선 대비
   95% 신뢰수준 선호.
2. 분포 거리: FID (1706.08500) · KID (1801.01401) · LPIPS (1801.03924) ·
   **sKVD (EPE 제안 — 시맨틱 정합 패치 KVD, 구조 보존+사실성 동시 측정, 사실상 분야 표준)** ·
   CMMD (CVPR 2024, 2401.09603).
3. 다운스트림: 번역 데이터 학습→실사 성능. CARLA2Real mIoU 최대 2배 / DGInStyle +2.5 mIoU /
   Sim2Real Diffusion 갭 40%+ / REGEN 32.14배 고속화. 학위논문도 2+3 조합이 관행.

## 6. 본 파이프라인의 위치

**필수 인용 10선**: CycleGAN · SimGAN · CUT · CyCADA · EPE · SDEdit · ControlNet ·
SDXL · Sim2Real Diffusion · NeuRAD (+CARLA2Real·REGEN·**Hybrid Sim2Real 2605.02291 강권**).

위치 요약: 구성요소(깊이-ControlNet, 저강도 img2img, 다운스트림 지향)는 각각 2023~2025 표준이나,
**결정론적 색정합 전처리 + 개입 강도 0.3 이중 봉쇄 + 센서 시뮬의 전체 체인**은 Hybrid
Sim2Real(2026)과 병행 등장한 소수 조합 — EPE 계열(풍부한 G-buffer 조건)과 순수 디퓨전(환각
위험) 사이의 실용적 절충으로 위치. 한계로 명시할 것: (1) 깊이 단일 조건은 G-buffer 조건의
부분집합 (2) 프레임 단위 처리라 시간 일관성 미해결. 평가는 sKVD류 + 다운스트림(+가능하면
소규모 사람 실험) 조합이 심사 방어에 유리.

이번 조사로 발견된 후보 기법: G-buffer 조건 디퓨전(RGB↔X 계열), sKVD 지표 추가, 파운데이션
특징 브리지(DINO), 비디오 일관성 5부작, 카메라 시뮬 GAN 평가(2209.06710).
