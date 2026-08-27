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

---

# 심화 사이클 2 (2026-08-27)

## 진단 지표 정식화 (SRCC 계보 심층)

### 0. 지정 arXiv ID 4건 검증 결과

모두 실재하며 주제 적합성이 확인됨 (2026-08 웹 검증):

| arXiv ID | 논문 | 검증 | 우리 실험과의 관련성 |
|---|---|---|---|
| **1907.07061** ✅ | Nowruzi et al., *How much real data do we actually need?* (ICML 2019 W. AI for Autonomous Driving) | 확인 | 합성 사전학습 → 소량 실사(13K의 2.5%/5%/10%) 파인튜닝이 **혼합(mixed) 학습보다 우수하고 분산도 작음**을 실증. "포토리얼리즘보다 다양성이 중요" 결론 |
| **2202.00632** ✅ | Burdorf et al., *Reducing the Amount of Real World Data…* (IEEE IV 2022) | 확인 | 데이터량-성능을 **멱법칙(power law)** 으로 모델링. 혼합셋에서 실사 비율 5–20%일 때 실사 필요량 최대 **70% 절감**. 라벨 예산 곡선 설계의 근거 |
| **2510.12208** ✅ | Bay et al., *The Impact of Synthetic Data on Object Detection…* (2025-10, 창고 팔레트 검출) | 확인 | Faster R-CNN으로 synthetic-only / mixed / **bridged transfer(합성 사전학습→실사 파인튜닝)** 3전략 비교. 실사 160장 기준 10/50/100% 비율 스윕, **±std 병기 보고**. 저데이터 구간에서 half-realistic 합성이 최대 이득 |
| **2502.15076** ✅ | Marcus et al., *Synth It Like KITTI* (ROBOVIS 2025, CARLA→KITTI LiDAR 3D) | 확인 | 합성 사전학습 후 **소량 실사 파인튜닝만으로 실사-전체 베이스라인에 근접**, 전체 실사 파인튜닝 시 상회. 모달리티는 다르지만(LiDAR) 로드맵 가설을 직접 지지 |

추가 발굴한 핵심 문헌: 2003.06957(TFA), 2211.16066(Vanherle, BMVC 2022), 2505.01016(YOLOv8 forgetting), 2202.10054(LP-FT), 1710.10710(Hinterstoisser 백본 동결), 2603.04964(replay), 2511.13944(cluster split), 2304.04653(near-duplicate 오염) — 아래 각 절에서 상술.

### 1. Few-shot 실사 파인튜닝의 설계 표준

### (a) 전층 vs 헤드만 vs 점진 해동 — 문헌의 합의점

- **TFA (2003.06957, ICML 2020)**: base 학습 후 **마지막 예측 레이어만** 파인튜닝(백본+FPN 동결)이 극저샷(1–10 shot)에서 전층 파인튜닝(ft-full)을 2–20pt 능가. 단, 이는 *클래스가 새로 추가되는* FSOD 설정. 우리처럼 **클래스 동일 + 도메인만 이동**하는 경우엔 더 깊은 해동이 유리하다는 게 후속 증거.
- **2505.01016 (YOLOv8n, 2025)**: freeze 깊이를 하이퍼파라미터로 스윕 — head-only(freeze=22) 67.5 → freeze=15 75.2 → **freeze=10(백본 동결, neck+head 학습) 77.3 mAP50**. 깊게 풀수록 타깃 성능 +10pt, 그런데도 COCO 성능은 36.7로 **전혀 하락 없음**. "forgetting 공포로 과도하게 동결하는 관행은 재고해야"가 결론.
- **Hinterstoisser (1710.10710, ECCVW 2018)**: 방향이 반대인 고전 — *합성으로 학습할 때* 실사-사전학습 백본을 동결하면 합성 low-level feature 오염을 막아 실사 성능의 95%까지 도달. 시사점: **저수준 feature는 실사 통계에 맞아야 한다** → 실사로 파인튜닝하는 우리 단계에서는 백본을 풀어주는 것이 이 원리와 정합.
- **LP-FT (2202.10054, ICLR 2022 oral)**: 무작위 초기화된 head와 함께 전층을 즉시 풀면 초기 큰 gradient가 사전학습 feature를 왜곡 → **선(先) head-only 수렴, 후(後) 전층 해동**(2단계)이 ID +1%, OOD +10%. 우리는 head가 이미 학습돼 있어(합성 사전학습) 왜곡 위험이 작지만, 극소량(25장)에서는 LP-FT식 2단계가 안전판.
- **점진 해동(gradual unfreezing)** 자체를 검출에서 체계 비교한 실증은 드물며, 사실상 LP-FT(2단계)가 그 실무 표준 근사.

**종합**: 25장 = head-only 또는 LP-FT 2단계, 50–100장 = freeze=10(백본 동결) ~ 전층(저LR)이 경합 구간. freeze 깊이는 반드시 어블레이션 대상.

### (b) 학습률·에폭 스케일

- 공통 패턴: **파인튜닝 LR = 원 학습 LR의 1/10 ~ 1/20**. TFA 0.02→0.001 (1/20), Vanherle(2211.16066) 0.001→0.0001 (1/10), 1907.07061은 동일 optimizer에 decay 스케줄만 단축(30K→5K step).
- Ultralytics 실무: `optimizer=auto`가 총 iteration ≤10K이면 AdamW + 자동 저LR 선택. 수동이면 SGD lr0=0.01의 1/10인 **lr0≈0.001**이 통용.
- 에폭: 소데이터 파인튜닝 문헌은 대체로 **고정 iteration/epoch 예산 + (가능하면) early stopping**. 2510.12208은 max 100 epoch + patience 15, 2505.01016·2211.16066은 고정 100 epoch. 주의: N=25에서 '에폭'은 iteration이 극소(25장/epoch)이므로 **에폭 수가 아니라 총 iteration을 기준으로 예산을 정하는 것**이 올바른 스케일링 (TFA도 shot 수에 따라 iteration을 조정).

### (c) 합성 리허설(replay) 혼합

- **핵심 대립**: 1907.07061과 2211.16066 모두 "**순차 파인튜닝 > 배치 혼합(mixing)**" (82.05 vs 80.13 AP 등). 반면 2211.16066은 파인튜닝 단계 *내부*에서 실사:합성 1:1 혼합 시 83.7 AP로 추가 상승 — 즉 **'사전학습→파인튜닝' 골격을 유지하되, 파인튜닝 배치에 합성을 리허설로 섞는 것**이 최고 성적.
- 혼합 비율: Burdorf(2202.00632)는 혼합셋 실사 비율 5–20%가 최적 절감점, 2211.16066은 파인튜닝 내 1:1까지 이득. LLM 쪽 최신 대규모 실증(2603.04964, *Replaying pre-training data improves fine-tuning*)은 replay 비율 ρ의 **유효 구간이 넓어 튜닝이 쉽고**, 타깃과 사전학습 분포가 **다를수록 replay 이득이 큼**을 보임 — 합성↔실사처럼 갭이 큰 우리 설정에 유리한 신호.
- 실무 규칙: 리허설 비율은 {0, 1:1, 3:1(합성:실사)} 정도의 거친 그리드면 충분하며, replay 시 **총 스텝을 1/(1−ρ)배로 늘려** 실사 노출량을 보존해야 공정 비교.

### 2. 라벨 예산 곡선의 보고 관행 (시드 수 · CI · 대조군)

### 시드 반복과 CI — FSOD 커뮤니티 표준

- **TFA/FsDet 프로토콜 (2003.06957)** 이 사실상의 표준: few-shot 샘플 자체를 여러 번 재추출하여 **PASCAL VOC 30회, COCO 10회 반복** 후 **평균 + 95% CI** 보고. 근거: 단일 샘플 결과는 극단적으로 불안정 — 예컨대 DeFRCN 1-shot이 single-run 53.6 AP vs multi-run 평균 40.2 AP (13pt 이상 부풀려짐, 2203.14205 survey).
- 저샷일수록 분산이 커지므로 **shot이 작을수록 시드를 늘리는** 게 관행 (VOC 30 > COCO 10). 최근 소규모 파인튜닝 연구(2410.00085 등)도 10 seed가 통상.
- 2510.12208처럼 각 점에 ±(std 또는 CI)를 병기하고 "차이가 CI 안이면 이득 주장 안 함"이 성실한 보고.
- **중요한 세부**: 시드는 (i) 학습 난수뿐 아니라 (ii) **N장 서브셋 추출 자체**를 다시 뽑는 것을 의미. 두 분산원을 함께 포괄해야 함.

### 곡선의 점 배치

- Burdorf(2202.00632)의 멱법칙 적합 관점에서 예산 점은 **로그 등간격**이 이상적: 25/50/100/200(+1000 상한 앵커)은 정확히 log2 등간격이라 그대로 멱법칙 적합·외삽에 사용 가능.

### 대조군 구성 관행

문헌 공통의 최소 대조군 3종 + 권장 2종:
1. **Real-only-N** (합성 없이, COCO 가중치에서 실사 N장 파인튜닝) — 합성 사전학습의 한계 이득을 분리하는 필수 대조군 (1907.07061, 2211.16066, 2510.12208 모두 포함).
2. **Synthetic-only** (0-shot) — 이미 보유 (53.7).
3. **Real-1000 상한 앵커** — 이미 보유 (89.7).
4. (권장) **Mixed-N**: 합성 360 + 실사 N을 처음부터 혼합 학습 — "파인튜닝 > 혼합" 재검증용.
5. (권장) **S→N + replay**: 파인튜닝 배치에 합성 리허설 혼합.

### 짝지은(paired) 비교

시드 s에서 추출한 **동일한 N장 서브셋을 모든 군이 공유**해야 seed-paired 비교(대응표본)가 성립 — 군간 차이의 CI가 크게 줄어듦. FsDet이 seed별 고정 split 파일을 배포하는 이유가 이것.

### 3. 평가 오염 방지 — Udacity 2Hz 연속 프레임

### 문헌이 확인한 위험

- **2511.13944** (*Find the Leak, Fix the Split*, 2026): 비디오 유래 데이터셋의 무작위 프레임 분할은 고상관 프레임을 train/test에 흩뿌려 누수 발생. 해법: 프레임을 임베딩(CLIP/DINO-v3 등) → PaCMAP 축소 → **HDBSCAN 클러스터링 후 클러스터 단위로 분할** (유사 프레임은 같은 split에).
- 스트라이프 분할(1-in-10 프레임을 test로) 관행조차 인접 프레임 유사성 때문에 누수라는 지적 (spatiotemporal correlation 클러스터 분석 연구, Bosquet et al. 계열). 시간적 과제에서 무작위 분할은 성능을 **5–15% 과대평가**한다는 보고.
- **2304.04653** (*Do We Train on Test Data?*): near-duplicate 제거 후 재평가 시 인식률이 실질 하락하고 **모델 간 순위까지 뒤바뀜** — 오염은 절대치뿐 아니라 방법 비교 결론 자체를 왜곡.
- 대규모 주행 벤치마크의 표준 관행도 동일 원리: nuScenes/BDD100k는 **scene/video 단위**로 split (프레임 단위 아님).

### 최소 시간 간격에 대한 문헌 상태

"몇 초 이상 떨어뜨려라"라는 **정량 표준은 문헌에 없음** (2511.13944도 명시적 간격 미제시). 관행은 (i) 시퀀스/주행 단위 블록 분할이 1차 방어, (ii) 임베딩·해시 기반 near-dup 스캔이 2차 방어. Udacity(2Hz, 고속 주행 위주)에서는 인접 프레임 간 0.5s ≈ 10–15m 이동이므로, **블록 경계에 수십 초 버퍼**를 두면 등속 주행 기준 수백 m 분리가 확보됨 — 신호 대기 등 정지 구간이 최악 사례이므로 버퍼는 정지 구간을 덮을 만큼(≥30s) 잡는 것이 안전.

### 실무 절차 (문헌 종합)

1. 프레임 타임스탬프/파일명 순서로 타임라인 복원 → **연속 블록(chunk) 단위로만** fine-tune-pool / val / test 할당 (test는 기존 53.7/89.7 평가에 쓴 셋을 동결 유지).
2. 블록 경계 양쪽 **버퍼 프레임 폐기** (2Hz 기준 60프레임=30s 권장).
3. 교차-split near-dup 스캔: 64-bit pHash Hamming ≤10 **또는** CLIP/DINO 임베딩 cos ≥0.95 를 플래그 → train 측과 걸린 test 프레임은 test에서 제외하고 제외 수를 보고.
4. 파인튜닝용 N장은 한 블록에서 연속으로 뽑지 말 것 — 25장이 12.5초짜리 한 장면이면 사실상 1장의 정보량. **블록 전체에 층화(stratified) 추출** (1907.07061: "다양성 > 포토리얼리즘").
5. 사용한 split 정의(블록 경계, 제외 목록, seed별 서브셋 파일)를 아티팩트로 공개.

### 4. 실패 사례 — few-shot 파인튜닝이 합성 사전학습 이득을 파괴하는 조건과 방지책

### 파괴 조건 (문헌 정리)

1. **큰 분포 이동 + 극소 라벨 + 전층 해동 + 높은 LR** 의 조합 (LP-FT, 2202.10054): 무작위/부정합 head의 초기 gradient가 하위층 feature를 왜곡 → ID는 오르지만 OOD가 최대 7% 하락. 우리 상황 번역: 25장의 특정 조명/도로에 과적합해 **합성 사전학습이 준 일반화(다양한 장면 대응력)를 잃고**, 89.7 상한은커녕 53.7 부근을 밑도는 지점이 생길 수 있음 — 특히 N=25에서.
2. **소표본 분산**: TFA 계열 증거대로 1–25 shot 구간은 어떤 서브셋이 뽑히느냐로 10pt 이상 요동. 단일 시드로 "파인튜닝이 이득을 파괴했다/살렸다"를 판정하면 오판.
3. **리허설 없는 장기 파인튜닝**: 2603.04964 — stage-2 데이터가 사전학습 분포와 다를수록 forgetting이 크고 replay 이득이 큼. 합성→실사는 정확히 이 고갭 케이스.
4. **반례도 기록할 것**: 2505.01016은 YOLOv8n의 과일 도메인 적응에서 freeze 깊이와 무관하게 COCO 성능이 전혀 안 떨어짐을 보고 — forgetting은 보편 법칙이 아니라 **갭 크기·데이터량·스케줄의 함수**. 우리 실험이 이 경계 조건을 측정할 수 있음.

### 방지책 도구상자 (비용 낮은 순)

- **저LR (1/10–1/20) + 짧은 warmup**: 전 문헌 공통 1차 방어.
- **freeze=10 (백본 동결)**: Ultralytics 한 줄 옵션. 2505.01016 기준 head-only보다 훨씬 낫고 왜곡 위험은 전층보다 작음.
- **LP-FT 2단계**: head-only 수렴 후 전층 저LR 해동 (극소 N 전용).
- **합성 리허설**: 파인튜닝 배치에 합성 프레임 혼입 (1:1~3:1), 2211.16066에서 검출 도메인 실증 (+1.7 AP).
- **WiSE-FT식 가중치 보간 (2109.01903)**: θ = (1−α)·θ_synth + α·θ_finetuned, α 스윕 — 학습 불필요한 사후 안전판. 분류 도메인 증거이나 검출에도 적용 사례 증가.
- **진단 지표**: 파인튜닝 후 모델을 **합성 val 셋에도** 평가해 forgetting 폭을 수치화(합성 mAP 하락량) — 이득 파괴의 조기 경보로 사용.

### 5. 근거 출처 목록

- [1907.07061 — How much real data do we actually need](https://arxiv.org/abs/1907.07061)
- [2202.00632 — Reducing the Amount of Real World Data (IV 2022)](https://arxiv.org/abs/2202.00632)
- [2510.12208 — Impact of Synthetic Data on Object Detection](https://arxiv.org/html/2510.12208v1)
- [2502.15076 — Synth It Like KITTI](https://arxiv.org/abs/2502.15076)
- [2003.06957 — Frustratingly Simple Few-Shot Object Detection (TFA)](https://arxiv.org/abs/2003.06957) · [FsDet repo (seed 프로토콜)](https://github.com/ucbdrive/few-shot-object-detection)
- [2211.16066 — Analysis of Training Object Detection Models with Synthetic Data (BMVC 2022)](https://ar5iv.labs.arxiv.org/html/2211.16066)
- [2505.01016 — Fine-Tuning Without Forgetting: YOLOv8](https://arxiv.org/html/2505.01016)
- [2202.10054 — LP-FT: Fine-Tuning can Distort Pretrained Features (ICLR 2022)](https://arxiv.org/abs/2202.10054)
- [1710.10710 — Hinterstoisser, Pre-Trained Features and Synthetic Images](https://arxiv.org/abs/1710.10710)
- [2603.04964 — Replaying pre-training data improves fine-tuning](https://arxiv.org/html/2603.04964v1)
- [2511.13944 — Find the Leak, Fix the Split](https://arxiv.org/html/2511.13944)
- [2304.04653 — Do We Train on Test Data? Near-Duplicates](https://arxiv.org/abs/2304.04653)
- [2203.14205 — FSOD Survey (multi-run vs single-run 격차)](https://arxiv.org/pdf/2203.14205)
- [Ultralytics fine-tuning guide (freeze/lr0/auto-optimizer)](https://docs.ultralytics.com/guides/finetuning-guide) · [freeze 논의](https://github.com/orgs/ultralytics/discussions/3862)
- [Roboflow Udacity Self-Driving 데이터셋 (2Hz, 라벨 품질 이슈)](https://public.roboflow.com/object-detection/self-driving-car)

### 권고

1. 【군 구성】 5개 군 × 예산 4점. | 군 | 초기 가중치 | 학습 데이터 | 목적 | |---|---|---|---| | A. S-only | COCO→합성360 (기존) | — | 0-shot 하한 앵커 (53.7, 재학습 불필요) | | B. R-only-N | COCO | 실사 N장 | "합성 없이" 대조군 (필수) | | C. S→FT-N (주력) | COCO→합성360 | 실사 N장 | 로드맵 가설 본검증 | | D. S→FT-N+replay | COCO→합성360 | 실사 N + 합성 리허설 1:1 | forgetting 방지 검증 (N=25,100만) | | E. R-1000 | COCO | 실사 1000 (기존) | 상한 앵커 (89.7, 재학습 불필요) | 예산 N ∈ {25, 50, 100, 200} — log2 등간격이라 Burdorf식 멱법칙 적합·외삽 가능.
2. 【시드·통계】 각 (군×N) 점당 시드 5개 (N=25는 8–10개로 증원: 저샷일수록 서브셋 분산 최대 — TFA/FsDet 관행). 시드 = 실사 N장 서브셋 재추출 + 학습 난수 둘 다 갱신. 같은 시드의 동일 서브셋 파일을 B/C/D가 공유(seed-paired 비교, FsDet 방식)하고 서브셋 파일을 저장소에 커밋. 보고는 평균 ± 95% CI (t-분포, df=시드수-1); 군간 차이는 paired 차이의 CI로 판정하고 CI가 0을 포함하면 이득 주장 금지. 총 학습 런 수 ≈ (B+C: 2군×4점 + D: 2점) × 5~10시드 ≈ 60런 내외 — YOLOv8n 소량 데이터라 1런 수 분이면 노트북/데스크톱 분담으로 감당 가능.
3. 【파인튜닝 레시피 (주력 C군)】 전층 파인튜닝 + lr0 = 0.001 (Ultralytics SGD 기본 0.01의 1/10 — TFA 1/20, Vanherle 1/10 관행의 중앙값), warmup 3 epoch, cos LR decay. 에폭은 총 iteration 기준으로 통일: 목표 ≈ 2,000 iteration (batch 16 기준 N=25→약 1,280 epoch은 과도하므로 N=25/50은 batch 8로 낮추고 max 300 epoch + patience 30, N=100/200은 max 150/100 epoch + patience 30). early stop 판정용 val은 test 블록과 분리된 고정 실사 val 블록(전 군 공유, 라벨 예산 외 항목임을 논문에 명시) 사용. mosaic는 마지막 20 epoch off (close_mosaic).
4. 【freeze 어블레이션 (본 스윕 전 선행)】 N=100, 시드 3개로 {freeze=None(전층), freeze=10(백본 동결), freeze=22(head-only), LP-FT(head-only 50ep→전층 저LR)} 4레시피 비교 → 승자를 전 예산 스윕에 채택. 예상: 2505.01016 근거로 freeze=10 또는 전층 우세, N=25에서만 LP-FT/head-only가 역전할 가능성 — 역전이 보이면 N=25만 레시피를 달리하고 명시. 동결 시 BN은 eval 모드 유지 (Ultralytics 기본 동작 확인).
5. 【리허설(D군) 설정】 파인튜닝 데이터로더에서 실사:합성 = 1:1 (epoch마다 합성 360장 풀에서 N장 무작위 재추출 = fresh sampling, 2603.04964 권고). 총 iteration은 C군의 2배로 늘려 실사 노출량 동일화(ρ=0.5 → 1/(1−ρ)=2배). N=25와 100 두 점에서만 실행해 이득 유무 확인 후 확대 결정. 판정 기준: C군 대비 paired 차이 + 합성 val mAP 하락폭(forgetting 진단) 동시 보고.
6. 【평가 오염 방지 절차 (스윕 시작 전 1회)】 (1) Udacity 프레임을 타임스탬프 순 정렬 → 연속 블록 단위로 fine-tune-pool / val / test 할당, 기존 53.7·89.7 측정에 쓴 test 프레임은 그대로 동결(숫자 비교 연속성 유지). (2) 블록 경계 양쪽 60프레임(2Hz×30s) 버퍼 폐기 — 정지 구간(신호 대기)까지 커버. (3) pHash(64bit, Hamming≤10) + CLIP/DINO cos≥0.95 이중 스캔으로 train측 near-dup인 test 프레임 제외, 제외 건수 보고 (2304.04653: 미제거 시 순위까지 왜곡). (4) N장 서브셋은 한 블록 연속 추출 금지, 블록 전체 층화 무작위 추출. (5) 블록 경계·제외 목록·시드별 서브셋을 JSON으로 버전 관리 — 데스크톱(UE)·노트북(RL) 간 코드-데이터 일관성 함정 예방.
7. 【평가·보고 절차】 각 런: 동결된 실사 test 블록에서 mAP50 + mAP50-95 + 클래스별 AP, 추가로 합성 val mAP50(forgetting 지표). 곡선 그림: x=log(N), y=mAP50, 점마다 95% CI 오차막대, A(53.7)·E(89.7) 수평 앵커선, B vs C 두 곡선 — "합성 사전학습이 실사 라벨 몇 장어치인가"를 수평 거리로 읽는 표준 제시법. 여력이 되면 25/50/100/200 4점에 멱법칙 적합해 89.7 도달에 필요한 N을 외삽(2202.00632 방식). 성공 판정 사전 등록: 주장 1 = C(N=100) ≥ B(N=100) + paired CI 초과, 주장 2 = C(N=100)이 89.7의 90% 이상 회복.
8. 【리스크와 사전 대응】 (i) N=25에서 C군이 A군(53.7)보다 떨어지는 시드가 나오면 catastrophic 과적합 신호 → LP-FT 또는 D군(replay) 결과와 대조해 원인 분리. (ii) 차이가 전부 CI 이내로 나오면(2510.12208의 결과 패턴) 시드 증원 전에 test 셋 크기·클래스 불균형부터 점검. (iii) Udacity 라벨 품질 이슈(중복 박스, 100% 겹침 박스)가 알려져 있으므로 파인튜닝 서브셋에 뽑힌 프레임은 IoU 기반 중복 박스 필터 후 육안 검수 — 25장 체제에서는 라벨 노이즈 1–2장이 곡선을 흔든다.

## 실사 파인튜닝 실험 설계 세부

### 1. SRCC 원 논문 (Kadian et al., arXiv:1912.06321)의 정확한 정의·절차·표본 단위

**정의 (원문 확인, export.arxiv.org/abs/1912.06321 검증 + ar5iv 전문 확인):** SRCC(Sim-vs-Real Correlation Coefficient)는 **표본 Pearson 상관계수(bivariate correlation)** 다. Spearman이 아니다 — 이름의 SRCC가 통계학의 'Spearman Rank Correlation Coefficient' 약어와 충돌하는 것은 유명한 혼동 지점이므로 논문에서 반드시 구분 표기해야 한다. 형식화는 시뮬 파라미터 θ에 대해 sim 성능 벡터 S_n(θ)={s_1(θ),…,s_n(θ)}와 실환경 성능 벡터 R_n의 상관을 최대화하는 `max_θ SRCC(S_n(θ), R_n)` 꼴이다. 즉 SRCC는 *시뮬레이터의 속성*(예측력)을 재는 지표이고, θ 튜닝의 목적함수로 쓰인다.

**표본 단위:** 데이터 점 1개 = **에이전트(모델·설정 조합) 1개**. 센서 양식(RGB / Depth / RGB→예측Depth) × 훈련 시뮬 설정을 바꾼 **n=9개 모델**이 점이 된다. 체크포인트도, 에피소드도 아니다 — '연구자가 시뮬에서 내리는 설계 결정(어느 모델이 나은가)'이 실세계에서도 같은 결론을 주는가가 원래 질문이다. x축=시뮬 성능(Success rate 또는 SPL), y축=동일 에피소드 세트의 실환경 성능. 각 점은 3개 코스 난이도 × 5 웨이포인트 × 3회 반복 = 총 810회의 sim/real 병렬 실행을 에피소드 평균으로 집계한 값이다.

**통계 처리의 부재:** 오차 막대(표준오차)만 제시하고 **유의성 검정·신뢰구간은 없다** (n=9의 Pearson r에 대한 p값 미보고). 이것이 후속 문헌에서도 이어지는 관행적 약점이다.

**핵심 결과:** CVPR19 챌린지 설정의 Habitat은 Success 기준 SRCC=0.18 — 원인은 에이전트가 **충돌 역학을 악용해 벽을 '미끄러지는'(sliding) 시뮬레이터 착취**를 학습했기 때문. 슬라이딩 금지 + 액추에이션 노이즈 정합 등 파라미터 튜닝 후 0.844로 상승. 명시된 한계: "SRCC가 낮으면 실환경 평균 성능이 높아도 그 시뮬레이터로는 의사결정을 할 수 없다 — 변경이 실환경에서 양의 효과일지 음의 효과일지 알 수 없기 때문." 이 문장이 당신의 '대체가 아니라 진단' 프레이밍의 정확한 원류다.

**당신 논문과의 관계:** SRCC를 체크포인트 단위로 옮기는 것은 원 정의의 '표본 단위 재정의'다. Kadian의 단위(설계 변형)는 당신의 **6라운드 정합 버전 쌍**에 정확히 대응하고, 체크포인트 시계열은 원 논문에 없는 새 축이다.

### 2. SRCC 이후: 후속·변형·비판 (2020–2026)

**(a) 저충실도 반론 — Truong et al., "Rethinking Sim2Real" (arXiv:2207.10821, CoRL'22; export 검증):** Habitat/iGibson × 3개 사족보행 로봇으로 대규모 sim-vs-real 평가. **충실도를 높이는 것이 오히려 전이를 해친다**(느린 시뮬 속도 + 시뮬 물리 부정확성에의 과적합). 실데이터 기반의 단순 운동 모델(kinematic)이 더 낫다는 결론. 당신의 '경량 시뮬의 가치' 주장과 방향이 같은 가장 강한 원군이며, 이들도 sim-real 성능 상관 산점도로 논증한다.

**(b) 순위 기반 재정식화 — SIMPLER, Li et al. (arXiv:2405.05941, CoRL'24; arxiv.org HTML 전문 확인):** 실로봇 조작 정책 평가를 시뮬로 대행. 지표 2개: Pearson r + **MMRV(Mean Maximum Rank Violation)**. 정의(원문): `RankViolation(i,j) = |R_i − R_j| · 1[(R_S,i < R_S,j) ≠ (R_i < R_j)]`, `MMRV = (1/N) Σ_i max_j RankViolation(i,j)` — 순위 위반을 **실환경 성능 마진으로 가중**한다. 표본 단위는 정책 6개(RT-1 **체크포인트 3개** + RT-1-X, RT-2-X, Octo — 체크포인트를 표본점으로 쓴 최초 사례 중 하나). 이들은 Spearman을 **명시적으로 기각**한다: "실값 간 마진을 무시하기 때문" — 소표본에서 근소한 차이의 순위 뒤집힘이 과대 처벌되는 문제의식이다.

**(c) 실환경 자동 평가 — AutoEval (arXiv:2503.24278, CoRL'25; 검색 확인) 및 Real-is-Sim (arXiv:2504.03597; arxiv.org HTML 확인):** Real-is-Sim은 단일 정책의 **체크포인트 4개**(10k/15k/25k/50k)를 sim/real 병렬 평가해 곡선 겹침을 보이지만, **상관계수 수치도, 훈련 시간에 따른 상관 변화 분석도 없다**. "나중 체크포인트가 항상 낫지는 않다"는 관찰만 있다.

**(d) SRCC의 직접 재사용 — EmbodiedSplat, Chhablani et al. (arXiv:2509.17430; export 검증):** 메시 재구성 기법 선택을 SRCC(0.87–0.97)로 검증 — SRCC가 '시뮬 자산 제작 파이프라인의 품질 지표'로 확장된 사례.

**(e) 2026 최신 종합 — "A Practical Recipe Towards Improving Sim-and-Real Correlation for VLA Evaluation" (arXiv:2606.10366; arxiv.org 확인):** VLA 정책 5개 × 9과제, 11,800 sim + 1,115 real 롤아웃으로 **Spearman ρ + Pearson r + MMRV 3종 병행 보고**가 사실상의 현행 표준임을 보여준다. SIMPLER 비판: 섭동 차원별로는 순위 보존 실패, 착취·적응 갭과 실능력의 혼동(zero-shot 평가의 혼입 변수).

**공통 비판 지점(당신 논문의 관련연구 절에 쓸 것):** (i) 유의성 검정 문화 부재(n=5~9의 Pearson r을 검정 없이 보고), (ii) 표본 단위의 비일관성(모델/체크포인트/자산이 뒤섞임), (iii) 시뮬 착취가 sim 점수를 인플레이션시켜 상관을 깨는 메커니즘은 반복 확인되지만 **착취의 시간 구조는 아무도 정량화하지 않음**.

### 3. 인접 분야의 정식화: OPE·NAS의 proxy 순위상관 표준

**Offline RL / OPE:** DOPE 벤치마크 (Fu et al., arXiv:2103.16596; export 검증)가 표준을 세웠다 — OPE 추정치와 실제 가치의 **Spearman 순위상관**, **Regret@k**(추정 상위 k개 중 최선과 전체 최선의 가치 차 — '지표로 고른 놈이 얼마나 손해인가'라는 의사결정 지향 지표), **절대 오차** 3종. 과제당 정책 10–96개. 그 전신인 Paine et al. "Hyperparameter Selection for Offline RL" (arXiv:2007.09055; export 검증)은 하이퍼파라미터가 다른 정책 집합의 순위 매김 신뢰도를 다룬다 — 당신의 '경량 시뮬 점수로 체크포인트/버전을 고를 수 있는가'는 구조적으로 이 offline policy selection 문제와 동형이다. Regret@1을 병기하는 관행을 가져올 가치가 크다.

**NAS zero-cost proxy:** Abdelfattah et al. (arXiv:2101.08134; export 검증)은 Spearman ρ를, White et al. "How Powerful are Performance Predictors" (arXiv:2104.01177; export 검증)은 상관·순위 기반 지표 다수(Kendall τ, sparse Kendall τ 포함)를 비교하며, NAS-Bench-Suite-Zero (arXiv:2210.03230; 검색 확인)가 대규모 표준화. weight-sharing 문헌(예: "An Analysis of Super-Net Heuristics", arXiv:2110.01154; 검색 확인)은 **proxy(수퍼넷) 순위와 진짜 순위의 Kendall τ 자체를 연구 대상**으로 삼았고, 동률·노이즈에 강건한 **sparse Kendall-Tau**(근소 차이를 동률로 뭉개고 계산) 변형을 만들었다 — 성공률 소수점 차이가 노이즈인 당신 데이터에 직접 이식 가능한 아이디어다.

**소표본(n=12~60) 통계 표준:** (i) **Kendall τ-b가 1순위** — 표집분포가 정규로 빨리 수렴하고, 쌍 계수에서 정확 p값 계산이 쉬우며, 동률 보정이 내장. (ii) SciPy 공식 문서도 소표본+동률에서는 **순열(permutation) 검정**을 권고. (iii) Spearman은 n<~30에서 정확 p 또는 순열 p 필수. (iv) Pearson을 쓸 경우(SRCC 충실 재현) n=12면 정확 순열검정이 계산 가능(12!은 못 하지만 10^4 무작위 순열로 충분), n=6이면 6!=720의 **완전 정확 검정**이 가능하다. (v) RL 실험 통계 일반론으로는 rliable (Agarwal et al., arXiv:2108.13264; export 검증)의 계층화(시드 단위) 부트스트랩 + 구간 추정 보고가 현행 규범.

### 4. 훈련 진행에 따른 상관의 동적 구조 — 선행 연구와 신규성 판정

**가장 가까운 이론적 원류 — Simulation Optimization Bias (Muratore et al., arXiv:1907.04685; export 검증):** "약간 결함 있는 시뮬레이터에서 정책을 최적화하면 SOB의 최대화로 쉽게 이어진다" — 옵티마이저가 모델링 오차를 착취할수록 sim 추정 성능과 실성능의 괴리(스칼라 편향)가 커진다는 정식화. SPOTA 알고리즘은 SOB 추정량을 **훈련 정지 기준**으로 쓴다. 즉 '훈련이 진행되며 proxy가 오염된다'는 발상은 있으나, SOB는 **편향(bias)이지 상관(correlation)이 아니고**, 버전·시드에 걸친 순위 예측력 개념이 없다.

**Goodhart 곡선 — Gao et al. "Scaling Laws for Reward Model Overoptimization" (arXiv:2210.10760; export 검증):** proxy 보상을 계속 올리면 gold 보상은 **올랐다가 꺾이는** 단봉 곡선 — 최적화 압력 축에서 proxy-gold의 국소 상관이 양→음으로 뒤집힌다는 당신 발견의 가장 유명한 구조적 유사물. Pan et al. (arXiv:2201.03544; export 검증)은 "능력 임계점에서 행동이 질적으로 전환되며 진짜 보상이 급락하는 **상전이(phase transition)**"를 보고. 단, 두 논문 모두 축이 '최적화량/능력'이고, **상관계수의 시계열**로는 표현하지 않는다.

**RL 과적합 문헌:** Zhang et al. (arXiv:1804.06893; export 검증), Cobbe et al. (arXiv:1812.02341; 검색 확인) — 훈련이 진행될수록 train-test 일반화 갭이 커짐. Lambert et al. "Objective Mismatch" (arXiv:2002.04523; export 검증) — 모델 정확도와 정책 수익의 **탈상관**을 MBRL에서 정식화. 2025-26의 sim2real 논문들(arXiv:2506.12735 — 섭동 하에서 정책이 sim 성능만 유지하고 real은 방치; arXiv:2504.15414 — 수렴 후 체크포인트 간 실성능 변동성과 cherry-picking 비판; 검색 확인)이 현상 자체는 지적한다.

**신규성 판정:** 조사 범위(2020–2026) 안에서 (i) 경량/고충실도(또는 sim/real) 점수 쌍을 **체크포인트 시계열 단위**로 놓고, (ii) **슬라이딩 윈도 순위상관 ρ(t) 또는 τ(t)의 시계열**을 계산해, (iii) **포화 후 부호 반전 시점을 착취 개시의 진단 통계**로 제시한 논문은 **찾지 못했다**. Real-is-Sim(체크포인트 4개, 계수 미보고, 시간 분석 없음)과 SIMPLER(체크포인트 3개를 정적 점으로만 사용)가 최근접 이웃이다. 따라서 "상관의 시간 구조(predictivity curve)로 포화 후 착취를 정량화"는 **좁게 주장하면 방어 가능한 신규성**이다. 단 관련연구에서 SOB(정지 기준으로서의 선례)와 Goodhart 곡선(부호 반전의 선례)을 반드시 인용하고, 주장을 '현상 발견'이 아니라 '**측정 가능한 진단 지표로의 정식화**'에 두어야 안전하다.

### 5. 지표의 함정: 천장/바닥 효과, 동률, 시드 혼합, 자기상관

**(a) 바닥/천장 효과 = 범위 제한(restriction of range):** MD 전이 성공률 0%가 다수인 구간에서는 분산이 붕괴해 **상관계수가 0 쪽으로 감쇠(attenuation)** 한다(심리측정학의 고전적 결과). 초기 구간(둘 다 바닥)과 포화 구간(경량이 천장)에서 상관이 '약해 보이는' 것은 진짜 무상관이 아니라 측정 한계일 수 있다 — **구간별 분산과 0%/100% 비율을 상관값 옆에 반드시 병기**해야 심사에서 방어된다. 경량 점수가 천장에 붙은 포화 구간은 역설적으로 '경량 점수의 미세 변동이 순수 노이즈'가 되므로, 그 구간의 음의 상관은 더 강한 증거 기준(순열 p)을 요구한다.

**(b) 동률 처리:** 성공률이 (성공수/에피소드수)의 이산값이라 동률이 구조적으로 발생하고, 0% 다수는 극단적 동률 덩어리를 만든다. 표준 해법: **Kendall τ-b**(동률 보정 내장, 소표본 정확 p) 사용; Spearman을 쓸 경우 average-rank + 순열 p. 동률이 전체 쌍의 절반을 넘는 창은 계수를 보고하지 말고 'τ 미정의'로 마스킹하는 것이 정직하다. NAS의 **sparse Kendall-Tau**(근소 차이를 의도적으로 동률 처리)는 반대로 노이즈성 순위 뒤집힘을 완화하는 도구로 차용 가능. 라플라스 평활 p̃=(k+1)/(n+2)로 0%들 사이에 순위를 살리는 것은 부차 분석으로만.

**(c) 시드 혼합 vs 시드별:** 12체크포인트 × 5시드 = 60점을 그냥 풀링하면 (i) 관측 독립성 위반, (ii) 시드 간 수준 차이와 시드 내 시간 구조가 섞여 **Simpson의 역설**적 부호 왜곡 가능. 표준 해법은 **rmcorr**(repeated measures correlation, Bakdash & Marusich 2017, Frontiers in Psychology; 검색 확인 — 시드별 절편을 허용하고 공통 기울기만 추정) 또는 **시드 내 쌍만 세는 층화 Kendall τ**. rliable(arXiv:2108.13264)의 시드 계층 부트스트랩과 결합할 것.

**(d) 체크포인트 자기상관:** 5분 간격 체크포인트는 강한 자기상관 시계열이므로 iid 가정의 p값은 과대 유의(anti-conservative)다. 자기상관 시계열 간 순위상관의 유의성 검정 문헌이 별도로 존재하며(예: PNAS-계열 방법론, PMC10557552), 실용 해법은 **시드 내 순환 이동(circular shift) 또는 블록 순열**로 널 분포를 만드는 것. 슬라이딩 윈도 다중검정은 max-통계 순열로 보정.

**(e) n=12의 검정력:** τ의 n=12 정확검정에서 유의(α=0.05, 양측)하려면 |τ|≳0.45 필요 — 시드별 곡선 하나로는 약하고, **5시드 결합(층화 τ 또는 Fisher 결합)이 검정력의 핵심**이다. 이는 '시드별 계산 후 결합'을 기본 설계로 강제하는 실용적 이유이기도 하다.

### 권고

1. [지표 1 — S2CC: 정합 버전 수준의 정적 Sim2Sim Correlation Coefficient (Kadian 직계 재현)] 표본 단위 = 정합 버전 v=1..6 (SRCC의 '설계 변형' 단위에 정확 대응). 각 (v, 시드 s)에서 실사용 선택 절차를 모사해 c*(v,s) = argmax_c L_{v,s,c} (경량 시뮬 점수 최고 체크포인트)를 고르고, x_v = (1/5)Σ_s L_{v,s,c*(v,s)}, y_v = (1/5)Σ_s M_{v,s,c*(v,s)} 로 집계. 정의: S2CC = Pearson r({(x_v, y_v)}_{v=1..6}) — Kadian과 동일하게 Pearson 유지하되, 원 논문에 없던 통계를 추가: (i) 완전 정확 순열검정 p_perm (6! = 720개 순열 전수, 양측), (ii) 시드 계층 부트스트랩 95% CI (시드 5개를 복원추출해 x,y 재집계 → r 분포), (iii) 동반 지표 MMRV = (1/6)Σ_i max_j |y_i − y_j|·1[(x_i<x_j) ≠ (y_i<y_j)] (SIMPLER 2405.05941 정의 그대로, '순위 실수의 실질 비용' 보고) 와 Regret@1 = max_v y_v − y_{argmax_v x_v} (DOPE 2103.16596 차용, '경량 시뮬로 버전을 골랐을 때의 손해'). 이 지표가 '경량 시뮬은 버전 간 설계 결정에 대해 진단적'이라는 주장의 정적 증거가 된다.
2. [지표 2 — DPC(t): Diagnostic Predictivity Curve, 체크포인트 시계열 위의 동적 순위상관 (신규성 핵심)] 각 시드 s와 슬라이딩 윈도 W_t = {t−w+1,…,t} (w=6 체크포인트 = 30분; 민감도 분석으로 w∈{4,6,8})에서 τ^(s)(t) = Kendall τ-b({(L_{s,c}, M_{s,c}) : c ∈ W_t}) 를 계산하되, 윈도 내 M 또는 L의 동률 쌍 비율 > 50%면 해당 (s,t)는 미정의로 마스킹. 정의: DPC(t) = (1/|S_t|) Σ_{s∈S_t} τ^(s)(t) (S_t = 미정의 아닌 시드 집합), 불확실성 대역은 시드 부트스트랩. 유의성: 자기상관 보존을 위해 각 시드의 M 시계열을 임의 오프셋으로 순환 이동(circular shift)하는 순열을 시드 독립적으로 10^4회 → 창별 p는 sup_t |DPC(t)| max-통계로 다중검정 보정. 핵심 보고 통계: 부호 전환 시점 t* = min{t > t_sat : DPC(t) < 0, 보정 p < 0.05} 를 '착취 개시점(exploitation onset)'으로 정의 — '초기 양의 상관 → 포화 후 음의 상관'을 하나의 검정 가능한 곡선과 하나의 시점 통계로 만든다. 이것이 SOB(1907.04685, 스칼라 편향)와 Goodhart 곡선(2210.10760, 상관 아님)이 하지 않은 정식화다.
3. [지표 3 — Δτ: 포화 전/후 위상 대비 층화 순위상관 (단일 수치 요약 + 함정 방어 내장)] 포화 시점을 시드별로 t_sat(s) = min{c : L_{s,c} ≥ 0.9 · max_{c'} L_{s,c'}} 로 정의(θ=0.9, 민감도 분석 θ∈{0.8,0.9,0.95}). 위상 P ∈ {pre: c < t_sat(s), post: c ≥ t_sat(s)} 각각에서 시드 내(within-seed) 쌍만 세는 층화 Kendall: τ_strat(P) = Σ_s (C_s^P − D_s^P) / Σ_s D_denom_s^P, 여기서 C_s/D_s = 시드 s 내 일치/불일치 쌍 수, D_denom_s = τ-b 동률 보정 분모 √((n₀−n₁)(n₀−n₂)) 의 시드별 값 — 시드 혼합의 Simpson 역설을 원천 차단(풀링 60점 상관은 절대 주지표로 쓰지 말 것; 부록에 rmcorr 병기). 주장 통계: Δτ = τ_strat(pre) − τ_strat(post), 유의성은 시드 내에서 위상 구조를 보존한 채 M의 체크포인트 라벨을 순환 이동하는 순열 10^4회로 Δτ 널 분포 생성, 양측 p 보고. 보고 의무 사항(바닥 효과 방어): 위상별 M=0 비율, 동률 쌍 비율, 위상 내 분산을 Δτ 옆에 표로 병기하고, M이 전부 0인 시드-위상은 제외 수와 함께 명시. Δτ > 0 유의 = '포화 후 경량 점수의 진단력 반전'의 논문 헤드라인 수치.
