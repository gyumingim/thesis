# DPC 신규성 적대 감사 (2026-08-27)

## 평결: 직접 반증 실패 — 단, 주장은 현재 문구 그대로는 위험하며 좁혀야 생존

11개 검색 쿼리와 10건의 원문 정밀 검증(full-text fetch)을 수행한 결과, **"경량/sim 점수와 고충실도/real 전이 점수의 순위상관(τ)을 학습 체크포인트 시계열 위에서 위상별(phase-wise)로 추적하여, 예측력이 전반 유의(τ≈+0.57)에서 후반 무정보(τ≈0)로 붕괴함을 보인" 논문은 발견하지 못했다.** 용어 "Diagnostic Predictivity Curve"도 선점되지 않았다 (검색 결과 임상통계의 PROC curve, predictiveness curve 등 무관한 용례만 존재). 따라서 **반증 실패**를 명시한다. 단, 비검색의 증명은 불가능하며, 아래와 같이 주장의 구성 요소 각각에는 강한 인접 선행이 존재하므로, 주장을 현재 문구('선행이 없다')대로 두면 심사에서 격추될 소지가 크다.

## 최근접 위협 1: Khor & Weng 2025 — '후반 무정보'의 절반은 이미 정량화됨

**[Post-Convergence Sim-to-Real Policy Transfer: A Principled Alternative to Cherry-Picking](https://arxiv.org/abs/2504.15414)** (arXiv:2504.15414, Khor & Weng, 2025-04-21, export.arxiv.org로 ID·제목·저자 검증 완료). 수렴 후(post-convergence) 체크포인트 집합에 한정해 Spearman 순위상관(SCC)을 계산: **직접 sim 성능으로 real 성능을 순위매기면 SCC ≈ −0.3** (무정보~역상관), 저자들의 worst-case 추정기로는 최대 0.55. 즉 "학습 후반 체크포인트들 사이에서 sim 점수가 real 전이를 순위매기지 못한다"는 **발견 자체는 이 논문이 선행**한다. **차이**: (a) 학습 전 구간에 걸친 시계열/곡선이 없음 — 후반 국면만 정적으로 분석, (b) 전반 유의→후반 붕괴라는 **전이(transition)의 관측·정량화 없음**, (c) 목적이 진단 곡선이 아니라 더 나은 선택 추정기 제안. DPC 주장에서 '후반 τ≈0' 단독을 신규성으로 내세우면 이 논문에 격추된다.

## 최근접 위협 2: 체크포인트를 상관 모집단으로 쓰는 것 자체는 기존 관행

두 편이 확인됨. (1) **[SIMPLER — Evaluating Real-World Robot Manipulation Policies in Simulation](https://arxiv.org/abs/2405.05941)** (arXiv:2405.05941, Li et al., 2024): 상관 계산용 정책 집합에 **RT-1 (Begin) / RT-1 (15%) / RT-1 (Converged)** — 즉 동일 정책의 학습 단계별 체크포인트 — 를 포함하고 MMRV·Pearson을 계산. 단 **풀링된 정적 상관**이며, 상관 자체를 학습 진행의 함수로 분석하지 않음(원문에서 직접 확인: "does not provide systematic analysis of how sim-real correlation itself varies as a function of training progress"). (2) **[Interactive World Simulator for Robot Policy Training and Evaluation](https://arxiv.org/abs/2603.08546)** (arXiv:2603.08546, RSS 2026): "final and intermediate checkpoints"를 각 데이터 점으로 하여 sim-real 산점도·강한 양의 상관을 보고. 역시 **단일 풀링 상관, 수치 계수 미보고, 위상별 분석 없음, 붕괴 발견 없음** (Figure 7 원문 확인). 결론: **"체크포인트에 대해 sim-real 상관을 계산했다"는 것은 신규성이 될 수 없고**, '시계열로 분해해 추적했다 + 붕괴를 발견했다'만 남는다. 기반 선행으로 **[Sim2Real Predictivity (SRCC)](https://arxiv.org/abs/1912.06321)** (arXiv:1912.06321, Kadian et al., 2019, ID 검증 완료)는 9개 모델 간 정적 상관 — 체크포인트·시간축 없음.

## 최근접 위협 3: 보상 과최적화/Goodhart — '현상' 수준의 신규성은 없음

**[Scaling Laws for Reward Model Overoptimization](https://arxiv.org/abs/2210.10760)** (Gao et al., 2022)과 후속 **[직접정렬판 스케일링 법칙](https://arxiv.org/abs/2406.02900)** (arXiv:2406.02900), **[Goodhart's Law in RL](https://arxiv.org/abs/2310.09144)** (arXiv:2310.09144, ICLR 2024), **[Constrained RLHF](https://arxiv.org/abs/2310.04373)**, **[RM Ensembles](https://arxiv.org/abs/2310.02743)**, 서베이 **[Reward Hacking in the Era of Large Models](https://arxiv.org/abs/2604.13602)** 를 검토. 서베이는 "Early in training, high proxy reward correlates with genuine quality... In these out-of-distribution regions, the proxy breaks down"이라고 **현상을 산문으로 명시**한다. 그러나 이 계열의 플롯은 전부 **proxy·gold 점수 자체를 KL/스텝 축에 그린 것**(hump-shaped gold curve)이고, **체크포인트 모집단 위의 순위상관 계수를 시간축 위에 그린 후속은 2024–2026 범위에서 발견하지 못했다.** 따라서 DPC의 신규성은 '현상'이 아니라 '측정 도구(순위상관 시계열)'에만 걸 수 있다.

## 경로 3 결과: OPE·NAS — 방법론적 형태의 부분 선행

**OPE**: [DOPE 벤치마크](https://openreview.net/pdf?id=kWSeGEeHvF8) (arXiv:2103.16596)는 학습 체크포인트에서 유도한 정책 집합에 대해 OPE 추정치 vs 실측의 Spearman 상관을 쓰지만 **집계치**다; OPE 정확도를 대상 정책의 학습 진행 함수로 추적한 연구는 검색에서 나오지 않았다. [When Offline Evaluation Misleads: A Diagnostic Protocol](https://arxiv.org/abs/2608.11560) (arXiv:2608.11560, 2026)은 제목이 위협적이었으나 원문 검증 결과 **1회성 정적 추정 + 별도 replay**로, 체크포인트 시계열 상관은 없음 — 탈락. **NAS**: [축약 학습의 효과](https://link.springer.com/article/10.1007/s00521-020-04915-6), [ProxyBO](https://arxiv.org/abs/2110.10423) 등에서 **Kendall τ를 학습 epoch 예산의 함수로 보는 형태 자체는 표준 관행**이다. 단 (a) 모집단이 체크포인트가 아니라 아키텍처, (b) proxy가 '동일 지표의 조기 절단', (c) **방향이 반대** — 학습이 진행될수록 τ가 상승·안정화(수렴)하지, 붕괴하지 않는다. 즉 'τ(t) 곡선'이라는 형태의 선행은 있으나 의미론과 발견이 다르다. 추가로 [Forecasting Downstream Performance of LLMs With Proxy Metrics](https://arxiv.org/abs/2605.18607) (arXiv:2605.18607)도 원문 검증: 체크포인트별 상관 곡선이 아니라 power-law 외삽 + 사후 집계 상관(ρ=0.84)이며 안정성을 보고 — 탈락. [VLA 평가 sim-real 상관 레시피](https://arxiv.org/abs/2606.10366) (arXiv:2606.10366)는 상관을 **시뮬레이터 미세조정 데이터량**의 함수로 봄 — 정책 학습 시간축 아님, 탈락. [Sim-and-Real Co-Training 기전 분석](https://arxiv.org/abs/2604.13645) (arXiv:2604.13645)도 체크포인트별 평가만 있고 예측력 동역학 분석 없음 — 탈락.

## 검색 커버리지 기록 (비검색의 증명 불가에 대한 대체)

실행한 검색 쿼리 11건: (1) rank correlation between proxy metric and true performance across training checkpoints collapse; (2) "sim-to-real" correlation simulation performance real robot performance "over training" checkpoints predictive; (3) reward model overoptimization proxy gold reward correlation "over training" degrades RLHF 2024 2025; (4) off-policy evaluation rank correlation policy checkpoints "during training" tracking accuracy; (5) NAS Kendall tau ranking correlation "as a function of" training epochs early stopping proxy; (6) "Diagnostic Predictivity Curve" OR "predictivity curve" training checkpoints correlation; (7) Goodhart's law "correlation between proxy and true" reward breaks down/collapses "as training"; (8) "reward model" accuracy degrades "distribution shift" policy drift during RLHF training steps; (9) sim-to-real transfer correlation decreases later in training policy overfits simulator locomotion checkpoint selection; (10) OPE quality "training stages"/"over the course of training" spearman checkpoints degrade; (11) CoRL RSS 2025 2026 simulation evaluation "predictive" real-world "training progress" checkpoints correlation. 원문 정밀 검증(fetch) 10건: 2608.11560(×2), 2405.05941, 2504.15414(×2), 2606.10366(×2), 2604.13645, 2603.08546, 2605.18607, 1912.06321, 1902.09635. ID를 export.arxiv.org로 직접 검증한 것: 2504.15414, 1912.06321, 1902.09635. 나머지는 arxiv.org 원문 fetch로 존재 확인. 잔여 사각지대: 비영어 문헌, 워크숍 논문, OpenReview 미게재 심사본, 그리고 'restriction of range'(후반 분산 축소로 인한 상관 붕괴)를 통계적 관점에서 다룬 심리측정 문헌의 ML 응용.

## 결론: 생존 조건

주장은 **다음과 같이 좁힐 때만 생존한다**: "sim/proxy 점수와 real/gold 전이 점수의 순위상관을 **단일 학습 궤적의 체크포인트 시계열 위에서 위상별(또는 슬라이딩 윈도)로 분해해 추적하는 진단 도구(DPC)를 제안하고**, 이를 통해 예측력이 전반 유의(τ=+0.57)에서 후반 무정보(τ≈0)로 **전이하는 시점을 정량화**한 것은 선행이 없다." 반면 다음 세 가지를 신규성으로 주장하면 반증된다: (a) '체크포인트에 대한 sim-real 상관 계산' 자체 (SIMPLER, RSS 2026 월드시뮬레이터가 풀링 형태로 선행), (b) '후반/수렴 후 체크포인트에서 sim 점수가 real을 순위매기지 못함'이라는 발견 단독 (2504.15414의 SCC −0.3이 선행), (c) 'proxy가 초반 유의하다 후반 붕괴한다'는 현상 수준 주장 (Goodhart/과최적화 문헌이 산문·점수곡선으로 선행). DPC의 방어 가능한 핵심은 **시간분해(time-resolved) 순위상관이라는 측정 형식 + 유의→무정보 전이점의 검출 + 경량 평가의 신뢰 구간(trust horizon) 진단이라는 용도**의 결합이다.

## 권고

1. 논문에서 '선행이 없다'는 문구를 '체크포인트 시계열 위에서 시간분해된 순위상관 곡선으로 예측력 붕괴 시점을 정량화한 선행이 없다'로 좁혀라 — 풀링 상관(SIMPLER, 2603.08546), 후반 국면 정적 상관(2504.15414), 현상 서술(Goodhart 문헌)은 모두 존재한다.
2. Khor & Weng (arXiv:2504.15414)을 반드시 인용하고 명시적으로 차별화하라: 그들의 SCC −0.3은 DPC의 '후반 τ≈0'과 같은 국면의 발견이므로, DPC의 기여는 전반-후반 대비와 전이점 검출임을 본문에서 직접 대조해야 한다.
3. SIMPLER(2405.05941)의 RT-1 Begin/15%/Converged 체크포인트 사용과 RSS 2026 월드시뮬레이터(2603.08546)의 intermediate checkpoint 산점도를 '풀링 상관은 위상별 붕괴를 가린다(Simpson's paradox 유사)'는 논거의 대조군으로 활용하면 신규성이 오히려 강화된다.
4. Gao et al. (2210.10760)과 Goodhart in RL (2310.09144)을 현상적 선행으로 인용하되, DPC는 점수 곡선이 아닌 상관 계수의 시계열이라는 측정론적 차이를 명시하라.
5. 후반 τ≈0이 '진짜 예측력 상실'인지 '후반 체크포인트 간 분산 축소로 인한 range restriction 아티팩트'인지 통계적으로 방어할 준비를 하라 — 심사자가 가장 먼저 제기할 공격이며, 본 조사에서 이를 다룬 ML 선행은 못 찾았으나 심리측정 문헌에는 표준 논제다.
6. NAS의 τ-vs-epoch 문헌(예: ProxyBO 2110.10423, reduced-training 연구)을 '형태는 같으나 방향이 반대(수렴 vs 붕괴)'인 인접 선행으로 각주 처리하라.
7. 잔여 위험: 비영어·워크숍·OpenReview 심사본은 커버하지 못했다. 투고 직전 'predictivity over training', 'checkpoint-wise correlation', 'sim-real correlation drift' 키워드로 1회 재검색을 권한다.