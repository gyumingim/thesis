# 리서치 로드맵 — 4축 심층 문헌 조사 (2026-08-26)

조사: 멀티에이전트 4축 병렬(웹검색+export.arxiv.org 실존 검증), 113편 중 109편 검증(나머지 4편 2차 검증 통과).
모드: 리서치 전용(사용자 지시) — 아래 권고는 실행 전 사용자 승인 대상.

## RL 위치 정립 — 착취·벽시계·조기정지·부정전이

### 1. Simulation Optimization Bias / 물리 근사 착취 (sim overfitting, reality gap exploitation)

| 논문 | 연도 | ID | 검증 | 관련성·차별점 |
|---|---|---|---|---|
| Assessing Transferability from Simulation to Reality for Reinforcement | 2019 | 1907.04685 | O | Muratore, Gienger, Peters (TPAMI 2021). SOB(Simulation Optimization Bias) 개념의 원전 — 옵티마이저가 시뮬 모델링 오차를 착취해 낙관 편향된 정책을 만든다고 정식화하고 부트스트랩 추정량으로 정량화. 차별점: 이들은 같은 파라미터 분포에서 샘플된 도메인 간 전이(도메인 랜덤화 설정)를 다루며 SOB를 기대수익 편향으로 측정. 우리는 코드베이스가 다른 이종 시뮬레이터 간(sim-to-sim) 전이에서, 과제 포화 이후에 착취가 시작되는 시간적 구조와 δ=0.5 경계 보수화 무력 실증으로 착취 대상이 경계가 아닌 물리 근사임을 인과적으로 국소화. |
| Robot Learning from Randomized Simulations: A Review | 2021 | 2111.00956 | O | Muratore, Ramos, Turk, Yu, Gienger, Peters. SOB·도메인 랜덤화 계열 문헌의 표준 리뷰 — '약간 결함 있는 시뮬레이터에서의 최적화는 SOB 최대화로 흐른다'를 명시. 차별점: 처방이 랜덤화(분포 확장)인 반면 우리는 랜덤화 이전 단계에서 벽시계 통제 실측으로 붕괴의 원인 분해를 제공. |
| Sim2Real Predictivity: Does Evaluation in Simulation Predict Real-Worl | 2019 | 1912.06321 | O | Kadian, Truong, Gokaslan, Clegg, Wijmans, Lee, Savva, Chernova, Batra. SRCC 지표 제안 + 에이전트가 'sliding' 충돌 동역학을 착취해 물리적으로 불가능한 경로로 성공하는 구체적 물리 근사 착취 사례 보고 — 우리 발견의 가장 가까운 실증 선행. 차별점: 내비게이션 도메인에서 사후 진단이며 착취 발생 시점(과제 포화 후)이나 학습 예산 통제가 없음. 우리는 3시드 통제 실험으로 착취를 시간축 위에서 재현. |
| Theoretical Foundations and Effective Algorithms for Policy-Aware Simu | 2026 | 2605.29032 | O | '강력한 RL 옵티마이저는 사소한 모델 부정확성을 필연적으로 착취한다'를 미니맥스(모델 대 적대 정책) 게임으로 정식화한 최신 이론 — 우리 발견의 필연성을 이론적으로 뒷받침. 차별점: 학습된 시뮬레이터의 목적함수 설계 문제이고, 우리는 수작업 경량 시뮬 대 무거운 시뮬의 실측 비교. |
| Objective Mismatch in Model-based Reinforcement Learning | 2020 | 2002.04523 | O | Lambert, Amos, Yadan, Calandra. 모델(시뮬) 정확도와 다운스트림 제어 성능이 비상관일 수 있음을 실증 — '시뮬 성능≠전이 성능' 분리를 뒷받침하는 인접 선행. 차별점: 학습된 동역학 모델의 우도 대 제어 성능 문제이며 시뮬레이터 간 전이가 아님. |
| A Study on Overfitting in Deep Reinforcement Learning | 2018 | 1804.06893 | O | Zhang, Vinyals, Munos, Bengio. RL 에이전트가 훈련 환경의 비본질적 특성에 과적합함을 체계적으로 보인 고전 — 우리 '시뮬 과적합' 프레임의 기초 인용. 차별점: 같은 엔진 내 훈련/시험 분할이며 물리 근사 착취 메커니즘은 다루지 않음. |
| The Surprising Creativity of Digital Evolution: A Collection of Anecdo | 2018 | 1803.03453 | O | Lehman 외 다수. 최적화가 시뮬레이터 물리 버그·근사를 착취한 일화 모음의 고전(에너지 보존 위반 착취 등) — 서론의 역사적 맥락용. 차별점: 일화적이며 통제 실험·정량화 없음. |
| The Reality Gap in Robotics: Challenges, Solutions, and Best Practices | 2025 | 2510.20808 | O | reality gap 원인(액추에이터 마찰·지연 등 정책이 착취하는 오차원 포함)과 대응책을 정리한 최신 서베이 — 관련 문헌 지도로 유용. 차별점: 서베이이며 벽시계 공정 비교나 포화-착취 전이 관찰 없음. |
| One Frozen Simulator Is Not Enough: Simulator Collapse in Multi-Agent  | 2026 | 2608.12253 | O | 'simulator collapse' 용어로 고정 시뮬 과적합에 의한 붕괴를 다루는 동시대 연구 — 우리 '완전 붕괴(0%)' 표현의 인접 용례. 차별점: 멀티에이전트 설정의 학습된 시뮬레이터 문제. |
| Overcoming the Sim-to-Real Gap: Leveraging Simulation to Learn to Expl | 2024 | 2410.20254 | O | NeurIPS 2024. 직접 전이가 실패해도 시뮬은 탐사 정책 학습이라는 다른 가치를 가진다고 논증 — '경량 시뮬의 가치는 대체가 아니라 다른 역할'이라는 우리 결론 프레임의 강력한 우군. 차별점: 그들의 대안 역할은 탐사, 우리는 진단. |

**시사점**: SOB(Muratore)가 개념적 원조이고 Kadian의 sliding 착취가 가장 가까운 실증 사례이므로 둘 다 필수 인용. 그러나 (a) 이종 시뮬레이터 간 전이에서 (b) 동일 벽시계 통제 하에 (c) '과제 포화 → 물리 근사 착취'라는 시간적 위상 전이를 관찰하고 (d) 경계 보수화 개입(δ=0.5)으로 경계 착취 가설을 반증해 원인을 국소화한 조합은 선행에 없음 — 이 4중 조합이 우리 기여 1의 신규성 주장 라인.

### 2. 벽시계/컴퓨트 공정 RL 비교 방법론 (throughput-oriented sim 평가 관행)

| 논문 | 연도 | ID | 검증 | 관련성·차별점 |
|---|---|---|---|---|
| Isaac Gym: High Performance GPU-Based Physics Simulation For Robot Lea | 2021 | 2108.10470 | O | Makoviychuk 외. GPU 상주 시뮬로 2-3자릿수 벽시계 단축 주장 — 처리량 시대의 대표 논문. 차별점: 벽시계 단축은 같은 시뮬 내 주장이며, 저충실도 대체재와의 동일 벽시계 대조 실험은 없음. |
| Brax — A Differentiable Physics Engine for Large Scale Rigid Body Simu | 2021 | 2106.13281 | O | Freeman 외. JAX 기반 초고속 물리 엔진, 수분 내 학습 데모 — '빠른 근사 물리' 노선의 표준 인용. 차별점: 근사 물리의 전이 비용(우리의 붕괴 발견)은 평가하지 않음. |
| Learning to Walk in Minutes Using Massively Parallel Deep Reinforcemen | 2021 | 2109.11978 | O | Rudin, Hoeller, Reist, Hutter. '벽시계 몇 분'을 명시적 성과 지표로 내세운 대표작 — 시간-도달 성능 보고 관행의 근거 인용. 차별점: 단일 시뮬 내 스케일링이며 충실도 축의 트레이드오프는 비교하지 않음. |
| Sample Factory: Egocentric 3D Control from Pixels at 100000 FPS with A | 2020 | 2006.11751 | O | Petrenko 외. 처리량 최적화 학습 시스템 — 'SPS가 성능 축'이라는 관행의 사례. 차별점: 동일 벽시계에서 이종 환경 비교 없음. |
| EnvPool: A Highly Parallel Reinforcement Learning Environment Executio | 2022 | 2206.10558 | O | Weng 외. 환경 실행 처리량 병목을 다룸 — 경량 자체 시뮬(수만 SPS)의 공학적 맥락 인용처. 차별점: 충실도 저하 없이 같은 환경을 가속하는 노선이라 우리의 근사-착취 문제가 아예 발생하지 않는 축. |
| GPUDrive: Data-driven, multi-agent driving simulation at 1 million FPS | 2024 | 2408.01584 | O | Kazemkhani 외 (Madrona 엔진 기반). 주행 도메인의 초고처리량 시뮬 — 우리 도메인(주행)과 직접 겹치는 처리량 노선 최신작. 차별점: 처리량 확보를 위해 물리를 단순화하면서도 그 근사가 전이에 미치는 비용은 정량화하지 않음 — 우리 결과가 이 노선에의 경고로 위치. |
| An Extensible, Data-Oriented Architecture for High-Performance, Many-W | 2023 | N/A (ACM TOG/SIGGRAPH 2023, arXiv 미등재) | X | Shacklett 외. 배치 시뮬레이션 엔진 설계의 대표작 — 처리량 지향 시뮬 생태계 인용. 차별점: 엔진 논문이며 학습-전이 평가 없음. |
| Parallel Q-Learning: Scaling Off-policy Reinforcement Learning under M | 2023 | 2307.12983 | O | Li 외. Isaac Gym 위에서 PPO 대 off-policy를 벽시계 기준으로 비교한 드문 사례 — '벽시계가 공정 축'이라는 방법론 인용처. 차별점: 알고리즘 간 비교이지 시뮬레이터(충실도) 간 비교가 아님. |
| Deep Reinforcement Learning at the Edge of the Statistical Precipice | 2021 | 2108.13264 | O | Agarwal, Schwarzer, Castro, Courville, Bellemare. 소수 시드 RL 보고의 통계 규범(IQM, 층화 부트스트랩) — 우리 3시드·±표준편차 보고 방식의 정당화 인용. 차별점: 보고 통계이지 예산 통제 설계는 아님. |
| Deep Reinforcement Learning that Matters | 2017 | 1709.06560 | O | Henderson 외. RL 비교 실험의 공정성 문제 제기의 고전 — 비교 방법론 장의 출발점 인용. 차별점: 샘플 축 비교의 재현성 문제이며 벽시계-충실도 축은 다루지 않음. |
| Time-Fair Benchmarking for Metaheuristics: A Restart-Fair Protocol for | 2025 | 2509.08986 | O | 동일 벽시계 예산을 명시적 프로토콜로 정식화한 유일하게 발견된 최신 사례 — 단, 분야가 메타휴리스틱. 차별점: RL/시뮬레이터 비교가 아니므로, RL에서의 동일 벽시계 교차-시뮬 프로토콜은 우리가 선점 주장 가능. |
| MetaDrive: Composing Diverse Driving Scenarios for Generalizable Reinf | 2021 | 2109.12674 | O | Li, Peng, Feng, Zhang, Xue, Zhou. 우리 비교 대상 시뮬 원 논문 — 정확한 스펙·평가 관행 인용 필수. 차별점: MetaDrive 논문 자체도 샘플 축 평가이며 경량 대체재와의 벽시계 대조는 없음. |

**시사점**: 처리량 지향 시뮬 논문들은 '같은 환경을 빠르게'의 벽시계 단축을 보고할 뿐, '더 싼(저충실도) 환경 대 더 비싼 환경을 동일 벽시계로 학습시키고 비싼 환경에서 평가'하는 교차-시뮬레이터 고정 시간 프로토콜은 발견되지 않음(가장 가까운 명시적 fixed-time 프로토콜은 타 분야 2509.08986). 우리 실험 설계 자체가 방법론적 기여로 주장 가능하며, GPUDrive처럼 물리를 단순화한 주행 시뮬 노선에 대한 직접적 경고 사례로 위치시킬 수 있음.

### 3. RL 조기정지·체크포인트 선택 (proxy 신호 기반 전이 시점 결정)

| 논문 | 연도 | ID | 검증 | 관련성·차별점 |
|---|---|---|---|---|
| Assessing Transferability from Simulation to Reality for Reinforcement | 2019 | 1907.04685 | O | Muratore 외. SOB 추정량을 훈련 정지 기준으로 사용 — '시뮬 과적합이 시작되면 멈춘다'는 proxy 조기정지의 가장 직접적 선행. 차별점: 정지 신호가 다중 도메인 롤아웃 기반 SOB 추정(추가 시뮬 비용 큼)인 반면 우리는 경량 시뮬 내부의 값싼 학습 신호만 사용하고, '붕괴는 피하지만 경쟁력은 회복 못 한다(0%→18%)'는 한계 정량화까지 제공. |
| Hyperparameter Selection for Offline Reinforcement Learning | 2020 | 2007.09055 | O | Paine 외. 환경 접근 없이 오프라인 신호(OPE 등)로 정책/체크포인트를 고르는 문제의 표준 정식화 — proxy 선택 문헌의 기둥. 차별점: 오프라인 RL 설정이며 '언제 다른 시뮬로 갈아탈지'라는 전이 시점 문제가 아님. |
| Model Selection for Offline Reinforcement Learning: Practical Consider | 2021 | 2107.11003 | O | Tang, Wiens. OPE를 검증 proxy로 쓰는 체크포인트/조기정지 파이프라인을 실무적으로 검토. 차별점: 타깃 환경 접근 불가 가정의 오프라인 설정 — 우리는 타깃 시뮬 접근이 가능하되 벽시계가 비싼 설정. |
| Model Selection for Off-policy Evaluation: New Algorithms and Experime | 2025 | 2502.08021 | O | OPE 자체의 선택 문제까지 다룬 최신 프로토콜 논문 — proxy 신호의 신뢰성 논의 인용처. 차별점: 통계적 OPE 문제이며 시뮬 간 전이 시점 결정이 아님. |
| Post-Convergence Sim-to-Real Policy Transfer: A Principled Alternative | 2025 | 2504.15414 | O | Khor, Weng. 수렴 후 어느 체크포인트를 실기 전이할지 최악-성능 최적화(QCLP)로 고르는 원리적 방법 — '전이용 체크포인트 선택'의 가장 가까운 최신 선행. 차별점: 수렴 후 선택이며, 우리는 포화 직후·착취 이전이라는 시간 창을 겨냥한 조기정지. |
| Uncertainty-Guided Checkpoint Selection for Reinforcement Finetuning o | 2025 | 2511.09864 | O | 불확실성 기반 체크포인트 랭킹 — proxy 신호 설계의 최신 사례(LLM-RL). 차별점: 도메인이 LLM RFT이고 전이 문제 아님. |
| Predicting Closed-Loop Performance of Latent World Models: Offline Che | 2026 | 2607.01736 | O | 1스텝 예측 지표가 체크포인트 선택 기준으로 나쁠 수 있고 구조적 진단이 낫다는 발견 — 'proxy 신호의 배신' 논의 인용처. 차별점: 월드모델-MPC 설정. |

**시사점**: proxy 기반 체크포인트/정지 선택은 오프라인 RL·sim-to-real에서 각각 성숙 중이나, '값싼 시뮬의 내부 신호만으로 비싼 시뮬로의 전이 시점을 고르는' 문제 설정은 SPOTA의 SOB 정지 기준 외에 직접 선행이 없음. 우리 기여는 방법의 성공담이 아니라 한계 정량화(붕괴 회피는 되지만 0%→18%로 경쟁력 회복 불가)라는 점에서 차별화 — 이 부정적 캘리브레이션 결과 자체가 '경량 시뮬=진단 도구' 결론을 지지하는 증거 사슬로 연결됨.

### 4. 커리큘럼/워름스타트의 해악 (negative transfer in RL) — 캐스케이드 기각과의 연결

| 논문 | 연도 | ID | 검증 | 관련성·차별점 |
|---|---|---|---|---|
| On Warm-Starting Neural Network Training | 2019 | 1910.08475 | O | Ash, Adams (NeurIPS 2020). 워름스타트가 동일 최종 손실에도 일반화를 해친다는 고전적 실증 — 캐스케이드 열세(39% vs 66%)의 학습이론적 배경. 차별점: 지도학습이며, 우리는 소스 자체가 착취로 오염된 RL 정책이라는 추가 악재가 있는 설정. |
| The Primacy Bias in Deep Reinforcement Learning | 2022 | 2205.07802 | O | Nikishin, Schwarzer, D'Oro, Bacon, Courville (ICML 2022). 초기 경험 과적합이 이후 학습을 영구 손상 — 경량 시뮬 10분이 심은 초기 편향이 MD 50분으로 못 지워지는 우리 관찰의 메커니즘 후보. 차별점: 단일 환경 내 리플레이 과적합이며 리셋 처방을 제안 — 우리 결과는 '리셋(네이티브 학습)이 실제로 이겼다'는 그들의 처방의 교차-시뮬 버전 실증으로 읽을 수 있음. |
| Fine-tuning Reinforcement Learning Models is Secretly a Forgetting Mit | 2024 | 2402.02868 | O | Wolczyk 외 (ICML 2024). RL 파인튜닝 초기에 사전학습 능력의 망각이 일어나 전이 이득이 소실됨을 실증 — 캐스케이드의 높은 분산(±21%)과 이득 소실을 설명하는 최신 프레임. 차별점: 이들은 유익한 사전지식의 보존이 목표이나, 우리 소스 정책은 물리 근사 착취로 오염되어 있어 '보존할수록 해로운' 반대 극단. |
| Efficient Online Reinforcement Learning Fine-Tuning Need Not Retain Of | 2024 | 2412.07762 | O | Zhou 외. 오프라인→온라인 파인튜닝 초기의 분포 불일치가 급격한 언러닝을 유발함을 분석 — 경량→MD 전환 직후 붕괴 역학의 인접 분석. 차별점: 데이터 분포 불일치(같은 환경)이며 우리는 물리 자체의 불일치. |
| Curriculum Learning for Reinforcement Learning Domains: A Framework an | 2020 | 2003.04960 | O | Narvekar, Peng, Leonetti, Sinapov, Taylor, Stone (JMLR 2020). 커리큘럼 RL 표준 서베이 — 잘못된 소스 과제가 음의 전이를 낳을 수 있고 이를 정식으로 다룬 연구가 드물다고 명시. 차별점: 우리 캐스케이드 기각은 이 서베이가 지적한 공백(소스가 해가 되는 조건)의 벽시계 통제 실증 사례. |
| Causally Aligned Curriculum Learning | 2025 | 2503.16799 | O | 인과적으로 비정렬된 소스 과제 훈련이 타깃 성능을 해침을 이론화 — '경량 시뮬=비정렬 소스'로 우리 결과를 이론 프레임에 접속 가능. 차별점: 혼란변수 기반 이론이며 물리 충실도 축이 아님. |
| Reinforcement Learning with Multi-Fidelity Simulators | 2014 | ICRA 2014 (arXiv 미등재) | X | Cutler, Walsh, How. 저충실도→고충실도 순차 활용 프레임워크의 원조 — 캐스케이드 아이디어의 지적 원류로 반드시 인용. 차별점: 저충실도가 항상 정보를 준다는 가정(Q값 휴리스틱 전이) 위에 있으며, 우리는 벽시계 예산 하에서 이 가정이 깨지는 반례(39%±21% < 66%±10%)를 제시. |
| Multi-Fidelity Hybrid Reinforcement Learning via Information Gain Maxi | 2025 | 2509.14848 | O | 다충실도 RL의 최신 발전 — 어느 충실도에서 샘플할지를 정보이득으로 고르는 노선. 차별점: 저충실도의 가치를 전제하는 낙관 노선의 최신판이라, 우리 부정 결과와 정면 대조되는 인용 상대. |
| Too Much of a Good Thing: When sim2real Efforts Impede Policy Learning | 2026 | 2606.02636 | O | Morgenstein 외. sim2real 노력(충실도 집착)이 오히려 정책 학습을 해칠 수 있다는 동시대 문제의식 — '충실도-학습성 트레이드오프' 논의의 최신 우군. 차별점: 방향이 반대(고충실도 집착의 해악)여서, 우리(저충실도 의존의 해악)와 함께 놓으면 '양방향 모두 순진한 선택은 실패한다'는 균형 프레임 구성 가능. |

**시사점**: 캐스케이드 기각은 고립된 결과가 아니라 워름스타트 일반화 손상(Ash&Adams), primacy bias(Nikishin), RL 파인튜닝 망각(Wolczyk)이라는 세 메커니즘 선행과 정합적. 특히 primacy bias의 처방(주기적 리셋)이 우리 실험에서 '네이티브 학습이 캐스케이드를 이긴다'로 자연 실증됐다고 쓸 수 있음. 동시에 다충실도 RL 낙관 노선(Cutler&How, 2509.14848)의 암묵 가정을 벽시계 예산 조건에서 깨는 반례로 위치시키면 기여가 선명해짐.

### 이 축의 권고

1. Muratore 외 SOB/SPOTA (1907.04685, 검증됨) + 리뷰 (2111.00956, 검증됨): 관련 연구 장의 축. '물리 근사 착취'를 SOB의 sim-to-sim·벽시계 통제·포화 후 위상 전이 확장으로 서술하고, δ=0.5 경계 보수화 반증 실험으로 SOB 문헌에 없는 원인 국소화를 기여로 주장.
2. Kadian 외 Sim2Real Predictivity (1912.06321, 검증됨): sliding 착취 사례와 SRCC — '시뮬 성능이 전이를 예측하는가'라는 질문 구조가 우리와 동형. 우리 결론(경량 시뮬=진단 도구)을 SRCC의 sim-to-sim 대응물로 프레이밍하면 강력.
3. 동일 벽시계 교차-시뮬 프로토콜의 직접 선행 부재: Isaac Gym(2108.10470)·Brax(2106.13281)·Rudin(2109.11978)·GPUDrive(2408.01584) 모두 같은 시뮬 내 벽시계 단축만 보고 — '이종 충실도 시뮬을 동일 벽시계로 학습·교차 평가'는 방법론적 신규성으로 명시적으로 주장할 것(타 분야 유일 선례 2509.08986만 각주로).
4. 캐스케이드 기각의 메커니즘 3연: Ash&Adams(1910.08475) + Primacy Bias(2205.07802) + Wolczyk(2402.02868) — 39%±21%의 높은 분산과 이득 소실을 이 세 문헌으로 설명하고, Cutler&How(ICRA 2014)류 다충실도 낙관 가정의 벽시계 조건 반례로 위치.
5. 2026년 이론 지원: Policy-Aware Simulator Learning(2605.29032, 검증됨)의 '강력한 옵티마이저는 필연적으로 모델 오차를 착취한다' 정식화를 서론에 인용하면 우리 실측이 최신 이론의 예측 실증이 됨.
6. 결론 프레임 보강: Lambert 외 Objective Mismatch(2002.04523)의 '정확도≠성능' 분리 + Overcoming the Sim-to-Real Gap(2410.20254)의 '직접 전이 실패해도 시뮬은 다른 가치' — '대체·가속이 아니라 진단' 결론을 양쪽에서 지지하는 인용 쌍.
7. 보고 통계: Agarwal 외 Statistical Precipice(2108.13264)를 따라 3시드 결과를 IQM/구간추정으로 보고하면 소시드 비판 선제 방어.

## 부정적 결과 방어 — 통계 표준·프레이밍

### 1. RL 재현성·통계 위기 문헌과 소수 시드(5시드, 30ep) 보고 표준

| 논문 | 연도 | ID | 검증 | 관련성·차별점 |
|---|---|---|---|---|
| Deep Reinforcement Learning that Matters (Henderson et al., AAAI 2018) | 2018 | arXiv:1709.06560 | O | 시드만 바꿔도 학습곡선이 겹치지 않음을 보인 원조 재현성 위기 논문. '소수 시드 결과는 본질적으로 불확실하다'는 우리 한계 서술의 표준 인용. |
| How Many Random Seeds? Statistical Power Analysis in Deep RL Experimen | 2018 | arXiv:1806.08295 | O | 시드 수 ↔ 통계 검정력의 정량 관계 튜토리얼. n=5는 '큰 효과(large effect)'만 검출 가능 → 우리 '전이 붕괴'는 초대형 효과라 n=5로도 검정력이 충분하다는 방어 논리의 근거. |
| A Hitchhiker's Guide to Statistical Comparisons of RL Algorithms (Cola | 2019 | arXiv:1904.06979 | O | 소표본에서 Welch t-test/부트스트랩/순위 검정의 위양성률·검정력 실증 비교. 어떤 검정을 왜 골랐는지 각주 한 줄로 방어 가능. |
| Deep RL at the Edge of the Statistical Precipice (Agarwal et al., Neur | 2021 | arXiv:2108.13264 / 라이브러리 github.com/google-research/rliable | O | 핵심 처방전: IQM, 층화(stratified) 부트스트랩 95% CI, performance profile, probability of improvement. README가 명시적으로 'reliable evaluation, even with a handful of runs'를 표방 — 3~5시드 체제의 사실상 심사 표준. |
| Accounting for Variance in Machine Learning Benchmarks (Bouthillier et | 2021 | arXiv:2103.03098 | O | 적은 예산에서는 여러 변동 요인을 함께 랜덤화해 분산을 통째로 보고하는 것이 더 신뢰할 수 있는 결론을 준다는 근거. 5시드 보강 설계 정당화에 사용. |
| Empirical Design in Reinforcement Learning (Patterson, Neumann, White, | 2024 | arXiv:2304.01315 (JMLR 2024) | O | 2023-2026 후속의 종합판. 몇 에피소드/몇 스텝을 셀지, 온라인·오프라인 평가, 집계 방식, 실험자 편향까지 다루는 실험설계 교과서 — 논문의 '평가 프로토콜' 절 전체의 뼈대 인용. |
| AdaStop: adaptive statistical testing for sound comparisons of Deep RL | 2024 | arXiv:2306.10882 / github.com/TimotheeMathieu/adastop | O | 'Deep RL 논문 다수가 5회 미만 실행으로 비교하며 이는 일반적으로 불충분'을 명시한 최신 근거 + 순차검정으로 필요한 시드 수를 결정. 3→5시드 보강 결정을 사후 정당화하는 인용. |
| Replicability in Reinforcement Learning (NeurIPS 2023) | 2023 | arXiv:2305.19562 | O | 재현성(replicability)의 형식적 정의를 RL에 도입한 2023 이론 후속 — 위기 문헌 계보가 2023 이후에도 이어짐을 보이는 인용. |
| REFORMS: Reporting Standards for Machine Learning Based Science (Kapoo | 2023 | arXiv:2308.07832 | O | ML 기반 과학 보고 체크리스트. 학위논문 부록에 '본 논문은 REFORMS 항목을 따름' 체크리스트를 넣으면 심사 방어력이 올라감. |
| A Tale of Two Variances: When Single-Seed Benchmarks Fail (Bayesian DL | 2026 | arXiv:2604.23114 | O | 단일/소수 시드 벤치마크가 실패하는 조건을 다룬 2026년 최신 후속 — '위기는 현재진행형'임을 보이는 최신 인용. |

**시사점**: 구체 처방(시드 5, 30ep): (1) 분석 단위는 '시드'다 — 시드당 30에피소드 평균을 1개 점수로 만들고, 150에피소드를 독립 표본처럼 합치지 말 것(Patterson 2024, Agarwal 2021). (2) 조건별로 5개 시드 점수 전부를 점으로 찍고(strip plot), 집계는 IQM + 층화 부트스트랩 95% CI로 보고, 조건 간 비교는 probability of improvement(+CI)로 제시. 여러 환경/조건을 묶을 때만 performance profile 사용. (3) 기각된 처방 2건은 'p>0.05라 효과 없음'이 아니라 CI 상한으로 '최대 이만큼의 개선 가능성까지 배제/미배제'로 서술(소표본에서 유일하게 정직한 화법). 적용 문장 제안 — (a) "Following Agarwal et al. (2021), we report interquartile means with 95% stratified bootstrap confidence intervals over 5 seeds, treating the seed—not the evaluation episode—as the unit of analysis; each seed's score is the mean over 30 evaluation episodes." (b) "With n=5 runs per condition, only large effects are statistically detectable (Colas et al., 2018); the transfer collapse we document is far beyond this threshold, whereas for the rejected remedies we report bootstrap confidence intervals on the effect size rather than binary significance claims." (c) "Our protocol follows the post-Henderson (2018) reporting standards consolidated by Agarwal et al. (2021), Patterson et al. (2024), and Mathieu et al. (2024), which explicitly target the few-run regime typical of computationally constrained studies."

### 2. 부정적 결과 논문의 성공 사례와 통한 프레이밍

| 논문 | 연도 | ID | 검증 | 관련성·차별점 |
|---|---|---|---|---|
| I Can't Believe It's Not Better! (ICBINB) 워크숍 시리즈 — NeurIPS 2020 Proce | 2020 | PMLR v137; dblp.org/db/conf/icbinb/icbinb2020.html; sites.google.com/view/icbinb-2023 | O | 부정적 결과 전용 정식 venue. 통한 프레임 = '명시적 가설을 세우고 실험으로 반증(empirical falsification)'. 우리 처방 2/3 기각을 이 형식으로 재서술 가능. |
| Position: Embracing Negative Results in Machine Learning (Karl et al., | 2024 | arXiv:2406.03980 | O | '예측 성능만이 논문 가치가 아니며 부정적 결과 출판이 커뮤니티 비효율을 줄인다'는 ICML 채택 position paper. 서론에서 부정적 결과의 학술적 정당성을 선제 방어하는 인용. |
| Are GANs Created Equal? A Large-Scale Study (Lucic et al., NeurIPS 201 | 2018 | arXiv:1711.10337 | O | '어떤 알고리즘도 일관되게 우월하지 않다'는 순수 부정적 결과로 톱학회 통과·고인용. 통한 프레임 = 중립적(neutral)·동일 예산·대규모 통제 실험이라는 방법적 엄밀성. |
| A Metric Learning Reality Check (Musgrave et al., ECCV 2020) | 2020 | DOI:10.1007/978-3-030-58595-2_41 | O | '10년간의 개선이 실은 평가 결함이었다'는 reality check 프레임. 부정적 결과 + 올바른 평가 프로토콜 제안을 묶어 기여로 만든 모범. |
| Deep RL that Matters (Henderson et al.) — 부정적 결과 논문으로서 | 2018 | arXiv:1709.06560 | O | 그 자체가 '재현 안 된다'는 부정적 결과 논문인데 분야 표준을 바꾼 최고 성공 사례. 프레임 = 실패의 원인 분해(extrinsic/intrinsic) + 커뮤니티 처방. |
| Deep Reinforcement Learning Doesn't Work Yet (Alex Irpan, 블로그) | 2018 | alexirpan.com/2018/02/14/rl-hard.html | O | 학술지 밖에서도 '정직한 실패 목록 + 그래도 되는 조건'을 제시해 표준 인용이 된 사례. 실패를 조건부 지식으로 바꾸는 어조의 참고. |

**시사점**: 성공한 부정적 결과의 공통 프레이밍 4가지: (1) 가설-반증 구조(ICBINB): '우리는 X가 도움이 된다는 가설을 세웠고, 통제 실험으로 기각했다'. (2) 중립·동일예산 대규모 통제(Lucic): 결과가 아니라 실험 설계의 엄밀성을 팔았다. (3) reality check(Musgrave/Henderson): 실패의 '원인 메커니즘'을 분해해 보여줌 — 실패 보고가 아니라 실패의 해부. (4) 조건부 지식화(Irpan): '언제는 되고 언제는 안 되는가'의 경계 지도. 적용 문장 제안 — (a) "Rather than reporting that the remedies 'did not work', we formulate each as an explicit falsifiable hypothesis and reject two of three under controlled, seed-matched conditions — following the empirical-falsification framing advocated by the ICBINB workshop series." (b) "In the spirit of neutral large-scale studies (Lucic et al., 2018) and evaluation reality checks (Musgrave et al., 2020), the contribution of this chapter is not a method but a carefully controlled map of where, and why, lightweight-simulation transfer breaks down." (c) "Negative results of this kind are increasingly recognized as first-class scientific output in machine learning (Karl et al., ICML 2024)."

### 3. 학위논문 심사에서 부정적 결과 방어 — '그래서 기여가 뭐냐'의 모범 답안 구조

| 논문 | 연도 | ID | 검증 | 관련성·차별점 |
|---|---|---|---|---|
| How to Write About Negative (Or Null) Results in Academic Research (Se | 2023 | servicescape.com/blog/how-to-write-about-negative-or-null-results-in-academic-research | O | 'negative results'가 아니라 '초기 가설을 기각한 결과'로 용어 자체를 재프레임하고 문헌으로 정당화하라는 실전 작성 가이드. |
| Is a PhD thesis with negative results acceptable? (ResearchGate Q&A) / | 2020 | researchgate.net/post/Is-a-PhD-thesis-with-negative-results-acceptable-for-the-award-of-the-degree; findaphd.com thread 16787 | O | 심사자 관점 합의: 기술적 문제로 인한 실패는 불충분하지만, '엄밀한 분석을 견디는 고품질 부정적 결과(다중 측정 + 좁은 CI)'는 학위 수여 사유가 된다. 즉 통계 품질이 방어의 전부. |
| Hints for PhD Defenses (Henning Schulzrinne, Columbia CS) | 2020 | cs.columbia.edu/~hgs/etc/defense-hints.html | O | 디펜스 표준 조언: 기여를 심사자가 평가하기 쉬운 형태(주장 목록)로 먼저 제시하고, '계속한다면 무엇을 할지'로 끝맺으라 — 부정적 결과 논문에 특히 유효. |
| Position: Embracing Negative Results in ML (기여 논거의 학술적 뒷받침) | 2024 | arXiv:2406.03980 | O | 심사 질의에서 '부정적 결과도 기여인가'가 나오면 ICML 채택 position paper를 직접 인용해 커뮤니티 차원의 합의로 응수. |

**시사점**: '그래서 기여가 뭐냐'의 모범 답안은 3층 구조로 준비: 층1 지식 주장(knowledge claims) — '경량 시뮬 전이는 조건 C에서 붕괴하며, 그 원인은 M이다'라는 검증된(반증 가능했던) 명제 자체가 신규 지식. 층2 경계 지도(boundary mapping) — 널리 가정되는 처방 2건이 효과 없음을 보임으로써 후속 연구자의 중복 노력을 차단(탐색 공간 축소가 곧 기여). 층3 재사용 가능한 산출물 — 진단 프로토콜·통계 파이프라인·공개 코드/시드별 원시 점수. 각 층을 claim → evidence(그림/CI) → implication(누가 무엇을 아끼는가) 순으로 1분 안에 말할 수 있게 리허설. 마지막에 '계속한다면'의 구체적 다음 실험 2개를 반드시 준비(심사자들이 '연구자로서 준비됨'을 확인하는 지점). 적용 문장 제안 — (a) "This thesis makes three contributions: (i) it documents and mechanistically explains the collapse of policy transfer from lightweight simulation under conditions C1–C3; (ii) it experimentally falsifies two widely assumed remedies, narrowing the search space for future work; (iii) it delivers a low-cost diagnostic protocol, with code and per-seed raw scores, that lets practitioners detect such collapse before committing to full-fidelity training." (b) "A rigorously established boundary of failure is a positive scientific claim about the world, even when the engineering outcome is negative." (c) 심사 구두 답변용: "기여는 '방법이 성공했다'가 아니라 '어떤 가정이 틀렸는지를 통제 실험과 신뢰구간으로 확정했다'는 것이며, 이는 같은 길을 갈 다음 연구자의 실험 비용을 직접 절약한다."

### 4. '진단 도구로서의 경량 시뮬' 프레임과 유사한 성공 프레임 (probe/diagnostic benchmark)

| 논문 | 연도 | ID | 검증 | 관련성·차별점 |
|---|---|---|---|---|
| Behaviour Suite for Reinforcement Learning (bsuite; Osband et al., ICL | 2020 | OpenReview: rygf-kSYwH (arXiv:1908.03568) | O | 그랜드 챌린지 대체가 아니라 '핵심 능력을 조사하는 진단 실험 모음'으로 스스로를 규정해 성공. 경량 환경의 가치를 '통찰 생산'으로 정의한 원형 — 우리 프레임의 1순위 인용. |
| MinAtar: An Atari-Inspired Testbed for Thorough and Reproducible RL Ex | 2019 | arXiv:1903.03176 | O | 10x10 경량화 Atari — 경량 시뮬을 '철저하고 재현 가능한 실험을 가능하게 하는 과학 기구'로 판 성공 사례. '경량이라서 가능한 것'을 파는 화법. |
| Beyond Accuracy: Behavioral Testing of NLP Models with CheckList (Ribe | 2020 | arXiv:2005.04118 / ACL 2020.acl-main.442 | O | held-out 정확도가 과대평가임을 전제로, 소프트웨어 유닛테스트식 '행동 진단'을 방법론으로 격상해 최우수논문. '본평가 이전의 저비용 진단 계층'이라는 프레임의 최고 성공례. |
| Sim2Real Predictivity: Does Evaluation in Simulation Predict Real-Worl | 2020 | arXiv:1912.06321 (IEEE RA-L 5(4):6670-6677) | O | 우리와 가장 가까운 성공 프레임: 기본 시뮬 설정의 예측력(SRCC)이 0.18로 처참하다는 '부정적 결과'를 Sim-vs-Real Correlation Coefficient라는 진단 지표로 승화하고, 파라미터 튜닝으로 0.844까지 올리는 처방까지 제시. 시뮬레이터를 '예측력으로 평가되는 진단 기구'로 재정의. |
| Deep RL at the Edge of the Statistical Precipice — 진단 관점 재인용 | 2021 | arXiv:2108.13264 | O | 진단 프레임에서도 재인용: 경량 시뮬로 낸 점수의 '신뢰구간'이 곧 진단 도구의 측정 오차라는 논리 연결. |

**시사점**: 성공한 진단 프레임의 공통 공식: (1) 자기 규정 — '본 평가의 대체물'이 아니라 '본 평가 전에 싸게 실행하는 진단 계층'으로 명시(bsuite, CheckList). (2) 가치 지표의 전환 — 경량 시뮬의 성능이 아니라 '완전 충실도(또는 실환경) 결과에 대한 예측력'을 가치 척도로 삼음(Kadian SRCC). 우리 논문에 SRCC 유사 지표(경량 시뮬 점수 vs 전이 후 점수의 순위 상관)를 정의하면 '진단 도구' 주장이 정량화되고, 낮은 상관 그 자체가 핵심 부정적 발견의 정량적 표현이 됨. (3) 실패 사례의 생산성 — 진단이 잡아낸 실패(policy cheating 등)를 카탈로그화. 적용 문장 제안 — (a) "We position lightweight simulation not as a training substitute but as a diagnostic instrument — in the sense of bsuite (Osband et al., 2020) and CheckList (Ribeiro et al., 2020) — whose value is measured by its predictivity of full-fidelity outcomes rather than by its own task scores." (b) "Following Kadian et al. (2020), we quantify this predictivity with a sim-vs-target correlation coefficient; the low correlation we observe is itself the central measurement of this thesis, delimiting the regime in which lightweight simulation can be trusted as a proxy." (c) "A diagnostic that reliably reveals when transfer will collapse is useful precisely because it is cheap: it converts an expensive deployment failure into an inexpensive pre-flight test."

### 이 축의 권고

1. 통계 프로토콜을 rliable 표준으로 전면 교체: 시드당 30에피소드 평균을 1개 점수로 하는 '시드=분석 단위' 원칙, 조건별 5개 점수 전부 표시(strip plot) + IQM + 층화 부트스트랩 95% CI + probability of improvement. 코드 github.com/google-research/rliable — README의 'reliable evaluation, even with a handful of runs'가 5시드 체제의 직접 근거.
2. 기각된 처방 2건은 '유의하지 않음'이 아니라 효과크기 CI의 상한으로 서술('최대 X 이상의 개선은 배제됨'). n=5에서 이것이 유일하게 정직하고 심사 방어 가능한 화법 (Colas 2018 power analysis + Agarwal 2021 인용).
3. 전이 붕괴 결과는 '초대형 효과라 n=5로도 검정력 충분'을 Colas(arXiv:1806.08295)로 명시하고, 3→5시드 보강 결정은 AdaStop(arXiv:2306.10882)의 '5회 미만은 일반적으로 불충분' 문장으로 정당화.
4. 프레이밍은 3층 구조로: (1) 가설-반증(ICBINB식 empirical falsification), (2) 경계 지도(어디서/왜 붕괴하는가 — Lucic 2018, Musgrave 2020식 통제 연구), (3) 진단 도구(bsuite/CheckList식 자기 규정). 서론에서 ICML 2024 position paper(arXiv:2406.03980)로 부정적 결과의 정당성을 선제 인용.
5. Kadian et al.(arXiv:1912.06321)의 SRCC를 본떠 '경량 시뮬 점수 vs 전이 후 점수'의 순위 상관 지표를 정의할 것 — 낮은 상관 자체가 논문의 핵심 발견을 정량화하며 '진단 도구로서의 경량 시뮬' 주장을 측정 가능한 주장으로 바꿔줌.
6. 심사 답변 리허설: '기여가 뭐냐' → 지식 주장(무엇이 왜 실패하는가) / 탐색 공간 축소(기각된 처방=후속 연구 비용 절감) / 재사용 산출물(진단 프로토콜+코드+시드별 원시 점수) 순으로 각 1분. 마지막에 '계속한다면 할 다음 실험 2개'를 반드시 준비 (Columbia defense-hints).
7. 관련연구에 Henderson(2018)→Colas(2018/19)→Agarwal(2021)→Patterson(JMLR 2024)→AdaStop(TMLR 2024) 계보를 한 단락으로 넣어 '본 논문의 평가 프로토콜은 2026년 현재의 보고 표준을 따른다'를 명시하고, 부록에 REFORMS(arXiv:2308.07832) 체크리스트를 첨부.

## 사실화 다음 수 — 글리프·다중조건·머티리얼·규모

### 1. 텍스트/글리프 보존·생성 디퓨전 — 번호판·간판 의사문자 해결 레시피

| 논문 | 연도 | ID | 검증 | 관련성·차별점 |
|---|---|---|---|---|
| TextDiffuser: Diffusion Models as Text Painters | 2023 | 2305.10855 | O | 계보 기점. 문자 단위 세그멘테이션 마스크를 먼저 생성 후 조건부 디퓨전. 코드 공개(MS unilm). SD 기반이라 우리 SDXL 파이프라인엔 직접 이식 불가. 난이도 상, 지금 쓸 이유는 없음(후속작에 대체됨). |
| GlyphControl: Glyph Conditional Control for Visual Text Generation | 2023 | 2305.18259 | O | 렌더된 글리프 이미지를 ControlNet 브랜치로 주입하는 '글리프 조건' 방식의 원조. 코드/가중치 공개. 순수 인페인팅 대비 글리프 조건이 OCR 정확도에서 일관되게 우세함을 보인 첫 계열. |
| AnyText: Multilingual Visual Text Generation And Editing | 2023 | 2311.03054 | O | 글리프+위치+마스크 이미지의 보조 latent와 OCR 인지 손실 결합. '편집 모드'가 정확히 우리 용례(마스크 영역만 텍스트 재생성). 다국어(한글 포함) 지원, AnyWord-3M 데이터셋·코드·가중치 전부 공개(ModelScope/GitHub). SD1.5 기반 별도 후처리 패스로 사용 — 난이도 중. |
| AnyText2: Visual Text Generation and Editing With Customizable Attribu | 2024 | 2411.15245 | O | WriteNet+AttnX 구조로 AnyText 대비 사실성 개선 + 추론 19.8% 고속화, 폰트·색 속성 제어. 코드·체크포인트·데모 공개(2025.03). 지역 인페인팅 후처리 패스의 현실적 1순위 후보. 난이도 중, 기대 효과: 번호판·간판 의사문자 제거(육안 품질 직접 개선). |
| TextCtrl: Diffusion-based Scene Text Editing with Prior Guidance Contr | 2024 | 2410.10133 | O | NeurIPS 2024. 장면 텍스트 '편집' 특화 — 원본 스타일(폰트·조명·기울기) 보존 사전을 명시적으로 인코딩. 코드+가중치 공개. 간판처럼 스타일 유지가 중요한 영역에 적합. 난이도 중. |
| FLUX-Text: A Simple and Advanced Diffusion Transformer Baseline for Sc | 2025 | 2505.03329 | O | FLUX DiT 기반 STE SOTA: 영어 Sen.ACC 84.19%로 AnyText2 대비 +5.04%p. Regional Text Perceptual Loss + 2단계 학습, 학습 데이터 0.1M(기존의 3%)으로 충분. 코드(AMAP-ML/FluxText)+HF 체크포인트(GD-ML/FLUX-Text) 공개. VRAM 요구 큼 — 난이도 중상, 기대 효과 최고. |
| TextFlux: An OCR-Free DiT Model for High-Fidelity Multilingual Scene T | 2025 | 2505.17778 | O | OCR 인코더 제거, 마스크 영역에 글리프를 직접 렌더해 시각 특징으로 사용 — 학습 어휘 밖 문자(한글 희귀 글자 등) 제로샷 일반화. 코드 공개. 다국어 간판에 유리. |
| SceneVTG++: Controllable Multilingual Visual Text Generation in the Wi | 2025 | 2501.02962 | O | 야외(in-the-wild) 텍스트 생성 특화 — 거리 간판·표지판 도메인이 우리와 가장 근접. 참고용 벤치마크·설계 근거로 유용. |

**시사점**: 검증된 레시피는 '영역 인페인팅 단독'이 아니라 '텍스트 검출 → 마스크 + 렌더된 글리프 조건 인페인팅'. 글리프 조건이 순수 인페인팅 대비 OCR 정확도에서 전 계열 일관 우세(GlyphControl→AnyText→FLUX-Text로 수치 계속 갱신). 우리 적용: (a) 최우선은 사실 엔진 쪽 — strength 0.3 img2img는 구조를 보존하므로 UE에서 실제 폰트 데칼(번호판 생성기+한글 폰트 간판 텍스처)을 렌더하면 의사문자가 원천 차단됨(난이도 하, 가장 확실). (b) 그래도 남는 손상은 PP-OCR/DBNet류로 텍스트 영역 자동 검출 후 AnyText2(코드·가중치 공개, 중) 또는 FLUX-Text(SOTA, 중상)로 크롭-업스케일-편집-합성 후처리. 원거리 소형 번호판은 크롭 확대 후 편집이 필수. 기대 효과: sKVD 수치보다는 육안 결함(의사문자) 제거에 직접 효과.

### 2. 다중 조건 ControlNet (depth+seg+normal/G-buffer) — 인도·건물 클래스 결함 대응

| 논문 | 연도 | ID | 검증 | 관련성·차별점 |
|---|---|---|---|---|
| T2I-Adapter: Learning Adapters to Dig out More Controllable Ability fo | 2023 | 2302.08453 | O | 경량 어댑터, 조건 합성(composable) 지원. TencentARC가 SDXL용 공개 가중치 배포(depth/canny/lineart/openpose/sketch) — 단 seg용 SDXL 어댑터는 없음. ControlNet보다 가볍지만 제어력 약간 낮음. 난이도 하. |
| Uni-ControlNet: All-in-One Control to Text-to-Image Diffusion Models | 2023 | 2305.16322 | O | 단일 모델 다중 조건(로컬 조건 어댑터 1개+글로벌 1개)의 원형. SD1.5 기반 — 우리 SDXL엔 개념 참고용. |
| ControlNet++: Improving Conditional Controls with Efficient Consistenc | 2024 | 2404.07987 | O | ECCV 2024. 생성 이미지에서 조건을 재추출해 사이클 일관성 보상으로 파인튜닝 — seg mIoU·depth 충실도 대폭 개선. 코드 공개(liming-ai). 단 공개 가중치는 SD1.5 기반이라 RealVisXL에 쓰려면 재학습 필요(난이도 상). '조건 충실도 자체를 올리는' 방법론으로 장기 참고. |
| xinsir/controlnet-union-sdxl-1.0 (+ProMax) — HF 공개 가중치 (논문 없음, Control | 2024 | HF:xinsir/controlnet-union-sdxl-1.0 | X | SDXL용 단일 모델 12조건(depth, normal, segment 포함) + 멀티조건 동시 입력 학습됨. arXiv 논문은 없으나 가중치·코드 완전 공개, 커뮤니티 검증 충분. 우리 파이프라인에 depth+seg(+normal) 동시 조건의 최단 경로. 난이도 하(diffusers에서 모델 교체 수준). |
| abovzv/sdxl_segmentation_controlnet_ade20k — HF 공개 SDXL seg 가중치 | 2024 | HF:abovzv/sdxl_segmentation_controlnet_ade20k | X | ADE20K 프로토콜 SDXL seg ControlNet 단독 가중치(5GB). diffusers Multi-ControlNet으로 기존 depth ControlNet과 스택 가능. SargeZT/sdxl-controlnet-seg도 대안. 난이도 하-중. |
| SimGen: Simulator-conditioned Driving Scene Generation | 2024 | 2406.09386 | O | 시뮬레이터 레이아웃(depth+seg) 조건 주행 씬 생성 — '시뮬 조건 → 실사 스타일'이라는 우리 문제 정의와 동일한 프레이밍. 시뮬-실사 혼합 학습으로 조건 불일치 극복. 방법론 참고. |
| RGB↔X: Image decomposition and synthesis using material- and lighting- | 2024 | 2405.00666 | O | SIGGRAPH 2024. albedo/normal/roughness/metallic/irradiance 등 intrinsic 채널(=G-buffer)→RGB 생성. 채널 일부만 지정하고 나머지는 모델이 채우는 설계 — UE G-buffer를 공짜로 가진 우리에게 개념적으로 이상적. 단 실내 도메인 중심 + SDXL 아님. 난이도 상. |
| RGBX-Next: Towards Realistic Generative Rendering from G-Buffers | 2026 | 2608.13929 | O | 2026.08 최신. G-buffer 조건 생성 렌더링의 사실성을 직접 겨냥한 후속 — 우리 '차기 단계' 방향과 정확히 일치. 코드 공개 여부 추적 필요. 난이도 상, 연구 기여 지점으로 유망. |

**시사점**: 인도 0.61의 원인 진단: depth 단독 조건은 평평한 인도에서 거의 정보가 없어(깊이 그라디언트 균일) 텍스처 사전을 소환하지 못함 — seg 조건으로 'sidewalk' 클래스를 명시하면 포장 패턴·연석 통계가 제대로 걸림. 건물 0.31도 동일 논리(파사드 텍스처). 실행 경로: (1) 최단 — xinsir union SDXL 하나로 depth+seg 동시 조건(UE에서 GT seg 무료, ADE20K 팔레트 매핑만 필요), 난이도 하. (2) 대안 — abovzv ADE20K seg를 기존 depth ControlNet과 diffusers Multi-ControlNet 스택, 난이도 하-중. (3) 장기 — UE G-buffer 전체(albedo/normal/roughness)를 조건으로 쓰는 RGBX-Next 방향이 우리 파이프라인의 자연스러운 진화이자 논문 기여 지점. 기대 효과: 인도 sKVD 0.61의 유의미한 하락(클래스 정체성 보존+올바른 텍스처 사전 소환이 정확히 이 지표가 재는 것).

### 3. 머티리얼/표면 사실성 — 백색 발광면 문제 (엔진 vs 후처리)

| 논문 | 연도 | ID | 검증 | 관련성·차별점 |
|---|---|---|---|---|
| Close the Sim2real Gap via Physically-based Structured Light Synthetic | 2024 | 2407.12449 | O | ICRA 2024. 조명·센서를 물리 기반으로 정합하면 후처리 없이도 gap이 닫힌다는 실증 — '엔진 쪽 수정 우선' 논거의 대표 문헌. 산업 도메인이지만 원리는 이식 가능. |
| RGB↔X: Image decomposition and synthesis using material- and lighting- | 2024 | 2405.00666 | O | 후처리 쪽 해법: 발광/과노출면을 intrinsic 분해 후 재합성으로 교정하는 개념 증명. irradiance 채널이 조명을 분리 표현 — 백색 클리핑면에 정보를 되살릴 수 있는 유일한 후처리 계열. 실내 도메인 한계, 난이도 상. |
| DiffusionRenderer: Neural Inverse and Forward Rendering with Video Dif | 2025 | 2501.18590 | O | CVPR 2025 oral, 코드 공개(nv-tlabs). G-buffer+조명→포토리얼 '비디오' 생성 — 발광면 광택·블룸을 데이터 기반으로 근사하고, 비디오 디퓨전이라 우리 프레임 단위 처리의 시간 일관성 부재까지 동시에 겨냥 가능. 난이도 상, 장기 기대 효과 최대. |
| UniRelight: Learning Joint Decomposition and Synthesis for Video Relig | 2025 | 2506.15673 | O | 분해+재조명 결합 비디오 릴라이팅 — 조명 사실성 후처리의 최신 계열. 참고용. |
| CARLA2Real: a tool for reducing the sim2real appearance gap in CARLA s | 2024 | 2410.18238 | O | EPE를 실시간(13FPS) 도구화. EPE의 G-buffer 판별자가 정확히 '발광·과노출면' 같은 렌더링 특유 아티팩트를 잡는 메커니즘 — 우리가 아는 EPE 계보의 실용 배포판. 코드 공개. |
| REGEN: Real-Time Photorealism Enhancement in Games via a Dual-Stage Ge | 2025 | 2508.17061 | O | 2단계(디퓨전으로 사실성 → 경량 GAN으로 분포 정합+실시간화). Hybrid Sim2Real 2026(2605.02291)이 이것과 FLUX 디퓨전을 결합 — 우리가 이미 아는 계보의 직계. |

**시사점**: 결론은 '엔진 쪽이 하 난이도·즉효, 후처리 쪽은 아직 연구 단계'. 백색 발광면의 근본 원인은 두 가지: (1) emissive 값이 물리 단위(nit) 없이 과대 → 톤매퍼에서 클리핑, (2) 순백·무텍스처 면은 img2img strength 0.3이 복원할 저주파 정보 자체가 없음. 엔진 쪽 처방: UE 물리 조명 단위 사용 + auto exposure(eye adaptation) 대신 EV 고정 수동 노출 + 발광면에 미세 roughness/dirt 텍스처 variation 부여 + bloom 억제 — 물리 기반 정합이 gap을 닫는다는 실증(2407.12449)이 이 방향을 지지. 후처리 쪽은 RGB↔X/DiffusionRenderer 계열이 원리적 해법이지만 주행 도메인 이식은 미해결 — 단기 적용 비권장, 장기 연구 기여 지점. 실무 순서: 엔진 수정(하) → 그래도 남으면 해당 영역만 strength 높인 마스크 인페인팅(중).

### 4. 데이터셋 규모·품질 트레이드오프 — 장수 vs 다양화 vs 정제, 무엇이 mAP를 올리나

| 논문 | 연도 | ID | 검증 | 관련성·차별점 |
|---|---|---|---|---|
| Scaling Laws of Synthetic Images for Model Training ... for Now | 2023 | 2312.04567 | O | 핵심 실증: 합성 이미지는 지도학습에서 실사보다 스케일링이 확연히 나쁨(수확 체감 빠름) — '장수 늘리기'의 한계를 정량화. 프롬프트 다양성·CFG 등 생성 설정이 스케일링 기울기를 좌우. |
| Diversify, Don't Fine-Tune: Scaling Up Visual Recognition Training wit | 2023 | 2312.02253 | O | 제목이 곧 결론: 같은 예산이면 다양화가 파인튜닝·장수 확대보다 낫다. 다양성 축 확대 시 스케일링이 지속됨을 보임. |
| Evaluating the Impact of Synthetic Data on Object Detection Tasks in A | 2025 | 2503.09803 | O | 주행 도메인 직접 실증: 실사/합성/혼합 비교(2D+3D, 카메라+LiDAR). 혼합이 우세하되 합성 비율·구성이 관건 — 우리 실험 설계의 직접 비교군. |
| Synthetic-to-Real Object Detection using YOLOv11 and Domain Randomizat | 2025 | 2509.15045 | O | 실증 결론: 시점·배경 다양화가 gap 해소의 결정 요인, 장수 확대는 부차적. 우리 절차 생성 파라미터 설계에 바로 이식 가능. |
| SDQM: Synthetic Data Quality Metric for Object Detection Dataset Evalu | 2025 | 2510.06596 | O | 학습 없이 합성 데이터셋의 mAP 기여를 예측하는 품질 메트릭 — '정제 품질' 축의 도구화. 우리 sKVD를 프레임 선별 지표로 쓰는 것과 동형의 아이디어라 방법 비교·인용 필수. |
| Robustness of Object Detection of Autonomous Vehicles in Adverse Weath | 2026 | 2602.12902 | O | 2026 최신: 합성 데이터 과다 학습 시 수확 체감 + 파국적 망각까지 보고 — 장수 확대의 하방 리스크 실증. |

**시사점**: 2023-2026 실증 문헌의 합의는 명확: 다양화 > 정제 > 장수. (1) 장수 확대는 수확 체감이 빠르고(2312.04567) 과하면 역효과(2602.12902). (2) mAP를 가장 올리는 축은 장면·시점·배경 다양화(2312.02253, 2509.15045) — 우리는 절차 생성이라 카메라 높이/화각/조명 시간대/자산 배치/생활감 밀도 파라미터를 늘리는 비용이 낮음, 이것이 최고 ROI. '생활감 밀도' 약점도 데이터 전략 관점에선 절차 생성 클러터 파라미터 다양화 문제로 환원됨. (3) 정제는 선별 메트릭으로: SDQM(2510.06596)처럼 우리 클래스별 sKVD를 프레임 단위 선별 지표로 돌려 하위 프레임을 버리는 파이프라인이 난이도 하로 즉시 구축 가능하고, 그 자체가 논문 기여(클래스별 sKVD 기반 큐레이션)가 됨. 권장 실험: 동일 총 장수에서 {장수2배 vs 장면다양화2배 vs sKVD상위50%정제} 3군 mAP 비교 — 문헌상 예측은 다양화 승.

### 이 축의 권고

1. 1순위(난이도 하, 즉효): 번호판·간판은 UE에서 실제 폰트 데칼로 원천 해결 — strength 0.3 img2img는 구조를 보존하므로 엔진에서 진짜 텍스트를 렌더하면 의사문자가 생기지 않음. 디퓨전 후처리보다 확실하고 싸다. 남는 손상만 OCR 검출→글리프 조건 인페인팅(AnyText2 2411.15245 코드·가중치 공개=중, FLUX-Text 2505.03329 SOTA=중상)으로 마감. 문헌 합의: 순수 영역 인페인팅보다 글리프 조건이 일관 우세.
2. 2순위(난이도 하, 인도 0.61 직격): xinsir/controlnet-union-sdxl-1.0(ProMax)로 depth+seg 동시 조건 전환 — UE에서 GT seg가 공짜이고 diffusers에서 모델 교체 수준. depth 단독은 평평한 인도에서 정보가 없어 텍스처 사전을 못 부름; seg가 'sidewalk' 클래스 정체성을 명시해 sKVD 최약점을 직접 공략. 대안: abovzv/sdxl_segmentation_controlnet_ade20k 스택.
3. 3순위(난이도 하): 백색 발광면은 엔진 쪽 해결 — emissive에 물리 단위(nit)+수동 노출(EV 고정)+미세 roughness/dirt 텍스처. 순백 무텍스처 면은 img2img가 복원할 정보 자체가 없으므로 후처리로는 원리적으로 안 됨(물리 기반 정합의 gap 감소 실증: 2407.12449).
4. 4순위(난이도 하-중, 논문 기여 겸용): 데이터 전략은 '장수 확대' 대신 절차 생성 파라미터 다양화(시점·조명·배치·클러터) + 클래스별 sKVD 기반 프레임 선별 — 문헌 합의(2312.02253, 2509.15045)가 다양화>정제>장수이며, sKVD 큐레이션은 SDQM(2510.06596)과 동형이라 그 자체로 기여가 됨. 검증 실험: 동일 예산 3군(장수2배/다양화2배/정제) mAP 비교.
5. 장기 연구 방향: UE G-buffer 전체(albedo/normal/roughness/irradiance)를 조건으로 쓰는 G-buffer 생성 렌더링(RGB↔X 2405.00666 → RGBX-Next 2608.13929)과 비디오 디퓨전 기반 DiffusionRenderer(2501.18590, 코드 공개)가 우리 파이프라인의 자연스러운 차기 단계 — 후자는 프레임 단위 처리의 시간 일관성 부재까지 동시에 해결하는 경로.

## syn2real 검출 맥락 — 갭 크기·축소 전략

### 1. 합성→실사 검출 갭의 보고된 크기 — 우리 위치 비교

| 논문 | 연도 | ID | 검증 | 관련성·차별점 |
|---|---|---|---|---|
| Differential Alignment for Domain Adaptive Object Detection (AAAI 2025 | 2024 | arXiv:2412.12830 | O | Sim10k→Cityscapes car AP50 표준 벤치마크 최신 수치: source-only 39.4 → DA 적용 69.7 (oracle급). raw 갭 ~26-30pp가 2025년 기준 표준. Faster R-CNN R50 기준. |
| Simplifying Source-Free Domain Adaptation for Object Detection (ECCV 2 | 2024 | arXiv:2407.07586 | O | Sim10k→Cityscapes VGG16-BN: source-only 31.5 / SF-UT(자기학습) 55.4 / oracle 58.5. raw 갭 27pp 중 자기학습만으로 89% 해소. source-only/oracle 비율 54%. |
| Synth It Like KITTI: Synthetic Data Generation for Object Detection in | 2025 | arXiv:2502.15076 | O | CARLA→KITTI (LiDAR 3D, Voxel-RCNN): 합성만 64.3 vs 실사만 82.9 (moderate) → raw 갭 18.6pp. 실사 400프레임 파인튜닝으로 81.6까지 회복(갭의 93% 해소). |
| Driving in the Matrix: Can Virtual Worlds Replace Human-Generated Anno | 2016 | arXiv:1610.01983 | O | Sim10k/50k/200k의 원전. GTA 합성 200k장 학습이 실사(Cityscapes) 학습을 KITTI 평가에서 능가 — 합성 장수 스케일이 갭을 상당 부분 상쇄한 고전적 증거. |
| Generalization Under Scrutiny: Cross-Domain Detection Progresses, Pitf | 2026 | arXiv:2604.08230 | O | 2026 크로스도메인 검출 서베이. 지리적/도시간 이동은 여전히 미해결 축이며 대부분 벤치마크가 단일 도시라는 한계 지적 — 우리 '도심 교차로→마운틴뷰 간선' 이동이 문헌상 가장 어려운 축임을 뒷받침. |

**시사점**: 우리 raw 46.5 vs 실사상한 89.7은 갭 43.2pp, 비율로 source/oracle=52%. Sim10k→CS의 source-only/oracle 비율(54-60%)과 거의 같은 수준 — 즉 우리 raw 갭은 문헌 정상 범위이며, 특이하게 큰 것이 아니다. 차이는 (1) 합성 360장은 Sim10k(10,000장)의 1/28로 극소량, (2) 평가가 지리+장면구성까지 어긋난 이중 이동이라는 점. 정제 후 53.7(비율 60%)도 'DA 미적용 + 외형 정제만' 상태의 문헌 기대치와 정합. 문헌은 이 상태에서 자기학습/소량 실사로 갭의 80-90%가 추가로 닫힘을 보고하므로 36pp 잔여 갭은 '아직 검증된 도구를 안 쓴 상태'로 해석해 논문에 서술하는 것이 정확하다.

### 2. 갭 축소 개입의 검증된 순서: 스케일링 / few-shot 실사 / 자기학습 / DA

| 논문 | 연도 | ID | 검증 | 관련성·차별점 |
|---|---|---|---|---|
| Reducing the Amount of Real World Data for Object Detector Training wi | 2022 | arXiv:2202.00632 | O | (b) 혼합 최적점: 실사 5-20%(최적 10%, 778장)에서 실사 100%(2,727장) 기준선을 동률-상회 (mAP50 0.384 vs 0.371, YOLOv3+Synscapes). 실사 필요량 70% 절감. |
| How much real data do we actually need: Analyzing object detection per | 2019 | arXiv:1907.07061 | O | (b) 전략 비교: 합성 사전학습 후 소량 실사 '파인튜닝'이 같은 양의 실사를 '혼합'하는 것보다 우수. 포토리얼리즘보다 합성 데이터 다양성이 중요하다는 결론. |
| The Impact of Synthetic Data on Object Detection Model Performance: A  | 2025 | arXiv:2510.12208 | O | (a)+(b) 최신 재검증: 어떤 합성이든 실사 10%와 결합 시 최대 이득; 합성→실사 bridged transfer(순차 파인튜닝)가 저실사 구간에서 혼합보다 우수; 합성 단독은 ID 성능에서 항상 실사 단독에 크게 뒤짐. |
| Simplifying Source-Free Domain Adaptation for Object Detection (SF-UT  | 2024 | arXiv:2407.07586 | O | (c) 라벨 없는 타깃 이미지만으로: source-only 31.5 → 55.4 (+23.9pp, oracle 58.5의 95%). 핵심 레시피는 단순함: BN 적응(AdaBN) + '고정' 의사라벨 FixMatch만으로 53.3 (+21.8pp) — 교사-학생 상호학습의 붕괴 위험 회피. |
| ConfMix: Unsupervised Domain Adaptation for Object Detection via Confi | 2022 | arXiv:2210.11539 | O | (c/d) YOLO 계열(YOLOv5)에 직접 적용된 UDA: Sim10k→Cityscapes +1.7 mAP, KITTI→CS +3.7. YOLO에서는 Faster R-CNN 계열 DA만큼 큰 이득이 아직 재현 안 됨을 보여주는 현실적 기준점. |
| Source-Free Domain Adaptation for YOLO Object Detection (SF-YOLO, ECCV | 2024 | arXiv:2409.16538 | O | (c) YOLO 전용 source-free 자기학습(교사-학생+타깃 도메인 증강). 소스 데이터 접근 없이 소스 사용 DA와 경쟁적 — YOLOv8n 파이프라인에 이식 가능한 가장 가까운 코드베이스. |
| Differential Alignment for Domain Adaptive Object Detection | 2024 | arXiv:2412.12830 | O | (d) DA-Faster 계열 최신 SOTA: source-only 39.4 → 69.7 (+30.3pp). 단, Faster R-CNN+FPN 전용 설계로 YOLOv8n 이식 난도 높음. |

**시사점**: 문헌이 지지하는 기대 이득/난이도 순서: (1) few-shot 실사 파인튜닝 — 실사 50-400장으로 갭의 80-93% 해소가 반복 보고(2502.15076: 400장으로 18.6pp→1.3pp; 2202.00632: 실사 10%로 100% 기준선 동률). 난이도 최하(라벨링 수 시간). 혼합보다 '합성 사전학습→실사 파인튜닝' 순차가 우수. (2) 자기학습 — 라벨 없는 타깃 프레임만으로 +20pp급(SF-UT), 레시피 단순(BN 적응+고정 의사라벨). 단 YOLO 계열 보고치는 더 보수적(+2-4pp, ConfMix)이므로 SF-YOLO 레시피 권장. 주의: 평가용 532프레임에 의사라벨을 돌리면 누수 — 반드시 별도 무라벨 Udacity 분할 사용. (3) 합성 스케일링 — 360장은 문헌 최소 규모의 1/30; 10k급까지 단조 증가가 표준(1610.01983은 200k에서 실사 추월). 렌더 파이프라인 보유 시 난이도 낮음. (4) 적대적 DA — 이득 최대치(+30pp)는 Faster R-CNN 전용이며 YOLOv8n 이식 비용 대비 (1)-(3)이 우선.

### 3. 사실화(외형 정제)의 다운스트림 효과 실증 — 우리 +7.2pp의 정합성

| 논문 | 연도 | ID | 검증 | 관련성·차별점 |
|---|---|---|---|---|
| Enhancing Photorealism Enhancement (EPE, Intel Labs) | 2021 | arXiv:2105.04619 | O | G-buffer 조건 사실화의 원전. GTA→Cityscapes 스타일 변환으로 사실감 지표(sKVD, 인간 평가) 대폭 개선. 다운스트림 검출 수치는 본 논문엔 없고 후속(CARLA2Real)에서 정량화. |
| CARLA2Real: a tool for reducing the sim2real appearance gap in CARLA s | 2024 | arXiv:2410.18238 | O | EPE를 CARLA에 적용한 다운스트림 실증: raw CARLA 학습 세그멘테이션 mIoU 0.065-0.072 → 정제 후 0.167-0.197 (2-3배)로 개선되나, 실사 학습 0.414에는 여전히 크게 미달. 외형 정제는 갭의 일부만 닫는다는 정량 증거. |
| Diffusion Dataset Generation: Towards Closing the Sim2Real Gap for Ped | 2023 | arXiv:2305.09401 | O | 디퓨전 생성/정제 데이터를 시뮬 데이터에 결합 → 순수 시뮬 학습 대비 실사 보행자 검출 AP 최대 +27.3%(상대). 디퓨전 정제 계열의 대표 실증. |
| A Hybrid Approach for Closing the Sim2real Appearance Gap in Game Engi | 2026 | arXiv:2605.02291 | O | 2026년 최신 디퓨전 하이브리드 정제: GTA-V 검출 mAP50 48.2→49.1 (+0.9pp), VKITTI2 세그 mIoU 52.2→55.9 (+3.8pp). 외형 정제 단독의 다운스트림 이득은 한 자릿수 pp가 전형이며, '분포 매칭'이 기하 변경보다 중요하다고 결론. |
| Meta-Sim: Learning to Generate Synthetic Datasets (MUNIT 대조 실험) | 2019 | arXiv:1904.11621 | O | 외형 변환(MUNIT)만 적용해도 콘텐츠(장면 구성) 정렬 없이는 갭이 남음을 명시적으로 실증 — '외형 갭 vs 콘텐츠 갭' 분리의 근거 논문. |

**시사점**: 우리 결과와 강하게 정합. (1) 우리 디퓨전 정제 +7.2pp(46.5→53.7)는 문헌 스펙트럼(+0.9pp[2605.02291] ~ +27%상대[2305.09401], CARLA2Real은 극저 기준선에서 2-3배)의 상단에 위치 — 정제 효과 자체는 문헌 대비 잘 나온 편으로 주장 가능. (2) 센서시뮬만(45.2, -1.3pp)이 무효과인 것도 정합: 외형 갭 중 저수준 센서 노이즈는 부차적이고 텍스처/재질/분포 수준 정합이 핵심이라는 EPE/REGEN 계열 결론과 일치. (3) 정제 후에도 36pp가 남는 것 역시 모든 외형 정제 논문의 공통 패턴(CARLA2Real도 정제 후 oracle의 40-48% 수준) — 잔여 갭은 외형이 아니라 콘텐츠/장면/데이터량 문제라는 Meta-Sim 논지로 설명하라. 논문 서술: '외형 정제는 갭의 ~17%를 닫았고 이는 문헌 보고 범위의 상단; 잔여 갭은 콘텐츠 갭과 데이터 규모로 귀속'이 문헌과 정확히 맞는 프레임.

### 4. 평가 도메인 정합(장면 수준 DA)의 효과

| 논문 | 연도 | ID | 검증 | 관련성·차별점 |
|---|---|---|---|---|
| Meta-Sim: Learning to Generate Synthetic Datasets (ICCV 2019) | 2019 | arXiv:1904.11621 | O | 장면 그래프 파라미터 분포를 타깃 실사 분포에 맞추도록 학습 → KITTI car AP@0.5 ~66.7/66.3/66.2(easy/mod/hard)로 고정 문법 기준선 대비 +2~3pp. 외형 변환만으로는 이 이득을 대체 못함(콘텐츠 갭 실증). |
| Structured Domain Randomization: Bridging the Reality Gap by Context-A | 2018 | arXiv:1810.10093 | O | 문맥 인식 배치(도로 위 차량, 현실적 맥락)가 균일 랜덤화·VKITTI·Sim200k·타도메인 실사(BDD100K)를 모두 능가 — 장면 구조가 검출 전이의 1차 변수. |
| Learning to Simulate | 2018 | arXiv:1810.02513 | O | 다운스트림 검출 성능을 보상으로 시뮬레이션 파라미터(교통 장면 구성)를 직접 최적화하는 프레임워크 — '평가 도메인에 맞춘 장면 생성'의 방법론적 원형. |
| Scene-Aware Location Modeling for Data Augmentation in Automotive Obje | 2025 | arXiv:2504.17076 | O | 2025년판 장면 인식 객체 배치: 현실적 위치 모델링이 비현실적 배치 대비 자동차 검출 증강 효과를 유의미하게 개선 — 장면 수준 정합의 최신 재확인. |
| Synthetic Datasets for Autonomous Driving: A Survey | 2023 | arXiv:2304.12205 | O | 외형 갭(픽셀/재질) vs 콘텐츠 갭(객체 수·배치·레이아웃·라벨 분포)의 표준 분류 제공 — 우리 논문의 갭 분해 서술에 인용할 정의 출처. |

**시사점**: 우리 이중 불일치(학습: 도심 교차로 / 평가: 마운틴뷰 간선)는 문헌이 말하는 전형적 콘텐츠 갭이다. Meta-Sim·SDR 계열은 장면 구성 정합만으로 +2~5pp급, 그리고 잘못된 장면 문법에서는 외형 정제가 무력함을 보인다. UE에서 즉시 가능한 정합 항목: (1) 도로 유형을 간선도로(다차선 직선, 중앙분리, 낮은 교차 밀도)로 교체, (2) Udacity 카메라 리그의 높이·피치·FOV 복제, (3) 차량 밀도/스케일 분포를 532프레임에서 추정해 매칭(원거리 소형 박스 비율), (4) 배경을 상가·가로수 등 교외 간선 요소로. 비용은 렌더 설정 수준으로 낮고, 문헌상 수 pp의 이득과 디퓨전 정제와의 상보성(콘텐츠+외형 동시 정합)이 기대된다.

### 이 축의 권고

1. [실험 1 — 최우선] 합성 사전학습 → 소량 실사 파인튜닝: Udacity 평가셋과 겹치지 않는 실사 25/50/100장을 라벨링해 '혼합'이 아닌 '순차 파인튜닝'으로 투입 (1907.07061, 2202.00632, 2510.12208 근거). 문헌은 실사 수백 장으로 잔여 갭의 80-93% 해소를 보고(2502.15076: 400장으로 18.6pp→1.3pp) — 53.7에서 75-85 mAP50 도달 가능성이 가장 높고 비용이 가장 낮다. 25/50/100 커브 자체가 논문의 그림이 된다.
2. [실험 2] 합성 스케일링 곡선: 360장은 문헌 최소 규모(10k)의 1/30. 장면 구성을 평가 도메인(간선도로 문법, Udacity 카메라 리그, 차량 밀도/스케일 분포)에 맞춰 360→1.5k→5k→10k 렌더 후 raw/정제 각각 학습 (1610.01983 스케일링 + 1810.10093/1904.11621 장면 정합 결합). 이 한 실험으로 조사질문 2(a)와 4를 동시에 답한다.
3. [실험 3] 라벨 없는 자기학습: 평가 532프레임과 분리된 무라벨 Udacity 프레임에 SF-UT 레시피(BN 적응 + '고정' 의사라벨 FixMatch, 2407.07586) 또는 YOLO 전용 SF-YOLO(2409.16538)를 적용. Faster R-CNN 문헌은 +20pp급, YOLO 문헌은 +2-4pp(ConfMix)로 보수적이므로 기대치는 +5-15pp로 설정. 주의: 평가셋에 의사라벨을 돌리면 데이터 누수 — 반드시 분할 분리.
4. [논문 서술] 우리 수치의 문헌 포지셔닝: raw 갭 43.2pp는 source/oracle 비율 52%로 Sim10k→Cityscapes의 54-60%와 동일 범위(정상), 디퓨전 정제 +7.2pp는 외형 정제 문헌 스펙트럼(+0.9~+10pp급)의 상단, 잔여 36pp는 '외형이 아닌 콘텐츠 갭+데이터 규모' 문제로 귀속(1904.11621의 MUNIT 대조실험, 2304.12205의 갭 분류 인용). 센서시뮬 무효과(-1.3pp)도 분포 매칭 우위 결론(2605.02291)과 정합.
5. [우선순위 배제] 적대적 DA-Faster 계열(2412.12830, +30pp)은 Faster R-CNN 전용 설계로 YOLOv8n 이식 난도가 높고, YOLO 계열 재현치는 +1.7~3.7pp(ConfMix)에 그침 — 실험 1-3 이후로 미룰 것.
