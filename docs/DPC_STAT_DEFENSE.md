# DPC 통계 방어 절차 (D1-D3) (2026-08-27)

## 1. 심리측정의 range restriction 보정 표준

**핵심 계보** — 이 분야의 표준은 인사선발/교육측정 문헌에 있고, 전부 Pearson r 기반이다.

- **Thorndike Case II (직접 선발 보정)**: 제한 표본 상관 r, 제한 SD s, 비제한 SD S로 모상관을 복원. 공식 `R = (r·S/s) / sqrt(1 - r² + r²·S²/s²)`. R의 `psych::rangeCorrection()`에 구현되어 있음 ([rdrr.io: psych range.correction](https://rdrr.io/cran/psych/man/range.correction.html), [personality-project 도움말](https://personality-project.org/r/psych/help/range.correction.html)). **가정: 전 구간 선형 회귀 + 등분산(homoscedasticity)** — 이 가정이 우리 방어의 급소이자 무기다(아래 3절).
- **Sackett & Yang (2000, J. Applied Psychology 85:112–118)**: range restriction 시나리오의 확장 분류체계(선발이 x/y/제3변수 z 중 어디에 걸리는지 × 비제한 분산을 아는지 × z가 측정되는지). 보정 공식 선택의 표준 참조 ([PubMed 10740961](https://pubmed.ncbi.nlm.nih.gov/10740961/), [Semantic Scholar](https://www.semanticscholar.org/paper/888692bc275306851a0f0986ff38fa4b8403404a)).
- **Hunter, Schmidt & Le (2006) — Case IV 간접 제한**: 실제 데이터 대부분은 간접 제한이며 Case II를 그대로 쓰면 과소보정됨을 보이고 u-ratio(u = 제한 SD / 비제한 SD) 기반 간접 보정 절차 제시 ([원문 PDF, U. Iowa](https://www.biz.uiowa.edu/faculty/fschmidt/meta-analysis/Hunter_Schmidt_Le_2006.pdf), [Le & Schmidt 2006 시뮬 검증](https://pubmed.ncbi.nlm.nih.gov/17154755/)).
- **Culpepper (2016, Psychometrika)**: 단조–이차 비선형성·이분산 하에서 표준 보정이 심하게 편향됨을 보이고 대안 제시 ([Cambridge Core PDF](https://www.cambridge.org/core/services/aop-cambridge-core/content/view/FD3AEBB8318EE0E6239CCF59D53305E0/S0033312300020147a.pdf/an_improved_correction_for_range_restricted_correlations_under_extreme_monotonic_quadratic_nonlinearity_and_heteroscedasticity.pdf), [PubMed 25953477](https://www.ncbi.nlm.nih.gov/pubmed/25953477)). 또한 표준 공식 자체의 표집분포 왜곡을 지적한 검증 연구도 있음 ([PMC6293417](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC6293417/)).

**출처 검증 표기**: Sackett & Yang, Hunter/Schmidt/Le, Culpepper는 서지·초록 수준까지 확인(원문 PDF 링크 확보, 전문 정독은 안 함). psych 패키지 공식은 공식 문서에서 확인. 인용 전 원문 1회 열람 권장.

## 2. 순위상관(Kendall τ / Spearman ρ) 판 보정은 존재하는가 — 사실상 없음

**조사 결론: Thorndike/Lawley 계열의 '순위상관용 range restriction 보정 공식'은 표준 문헌에 존재하지 않는다.** 검색에서도 비모수 상관의 제한 보정을 직접 다룬 표준 절차는 나오지 않았고 ([UVA Library 상관 개관](https://library.virginia.edu/data/articles/correlation-pearson-spearman-and-kendalls-tau) 등 어느 자료도 언급 없음), 보정 문헌은 전부 Pearson r + 선형·등분산 가정 위에 서 있다.

이것이 방어에 유리한 이유:
1. **τ는 단조변환 불변이지만 절단(truncation/selection) 불변은 아니다.** 즉 '구간 선택이 τ를 깎을 수 있다'는 심사자 지적 자체는 원리적으로 가능하나, 그 크기를 공식으로 보정하라는 요구는 성립하지 않음 — 표준 도구가 없으므로 시뮬레이션 기반 감도분석(3절 D3)이 방법론적으로 정당한 유일한 대응이다.
2. **동률(ties) 문제는 range restriction이 아니라 측정 이산성(coarseness) 문제로 분리된다.** 이산 주변분포에서는 τ의 도달 가능 범위 자체가 ±1보다 좁아진다 — Genest & Nešlehová (2007, ASTIN Bulletin) "A Primer on Copulas for Count Data"가 표준 참조 ([WU Vienna 서지](https://research.wu.ac.at/en/publications/a-primer-on-copulas-for-count-data-2), [ResearchGate](https://www.researchgate.net/publication/264906598_A_Primer_on_Copulas_for_Count_Data)). M이 0~33% 범위의 소수 이산값이면 |τ|의 상한을 계산해 '관측 τ≈0을 상한 대비'로 제시할 수 있음.
3. 동률 처리된 **τ-b**가 표준이며 ([Statistics Solutions](https://www.statisticssolutions.com/free-resources/directory-of-statistical-analyses/kendalls-tau-and-spearmans-rank-correlation-coefficient/)), 동률이 많을 땐 Goodman–Kruskal γ, Somers' D 병기가 관례 ([StatPlus 문서](https://www.analystsoft.com/en/products/statplus/content/help/analysis_nonparametric_statistics_rank_correlations_spearman_r_kendall_tau.html)).

**출처 검증 표기**: '순위상관용 표준 보정 부재'는 부재 증명이므로 단정 대신 논문에는 "우리가 아는 한(to our knowledge) 비모수 상관의 폐형 제한 보정은 없다"로 기술하고 Sackett & Yang 분류체계가 Pearson 기반임을 근거로 인용할 것.

## 3. ML/RL에서의 선행 연구

- **BenchBench / Benchmark Agreement Testing (Gera 외, [arXiv:2407.13696](https://arxiv.org/abs/2407.13696))**: 벤치마크 간 순위상관이 **어떤 모델 부분집합을 쓰느냐에 민감**하며, 성능이 인접한(adjacent) 모델들만 뽑으면 무작위 표본보다 상관이 체계적으로 낮아짐을 명시 — 이것이 정확히 ML 판 range restriction이다. 이들의 처방은 '보정'이 아니라 **여러 granularity에서 상관을 병기**하는 것. 우리 논문이 전반/후반 τ를 나눠 보고하는 것 자체가 이 권고와 정합적이라고 주장 가능.
- **Agarwal 외 2021, "Deep RL at the Edge of the Statistical Precipice" (NeurIPS 2021 Outstanding Paper)**: 소수 시드 체제에서의 신뢰 가능한 평가 표준 — 층화 부트스트랩 CI, IQM, 순위 기반 집계. 5시드 데이터의 불확실성 정량화에 그대로 인용 ([NeurIPS PDF](https://proceedings.neurips.cc/paper_files/paper/2021/file/f514cec81cb148559cf475e7426eed5e-Paper.pdf), [rliable 라이브러리](https://github.com/google-research/rliable)).
- **Gao, Schulman & Hilton, "Scaling Laws for Reward Model Overoptimization" ([arXiv:2210.10760](https://arxiv.org/abs/2210.10760), ICML 2023)**: 최적화가 진행될수록 proxy 점수는 계속 오르는데 gold 점수는 정점 후 하락 — **'후반 학습에서 경량 proxy와 실제 목표의 탈동조(decoupling)는 실재하는 현상'이라는 최강의 선례.** 우리 데이터의 후반 L 단조 상승 + M 하락 패턴과 구조가 동일함(Goodhart형 탈동조)을 지적하면 'τ≈0은 아티팩트'가 아니라 '기제 있는 현상'이라는 대안 설명이 선행으로 뒷받침됨.
- **RL 일반화 문헌**: 연속제어 DRL에서 훈련 수익과 시험(전이) 성능이 약하거나 음의 상관 ([Zhang 외, arXiv:1902.07015](https://arxiv.org/pdf/1902.07015)); Procgen에서도 환경별로 훈련–시험 상관이 크게 갈림 ([Cobbe 외 Procgen](https://cdn.openai.com/procgen.pdf), [탐험–일반화 arXiv:2306.05483](https://arxiv.org/pdf/2306.05483)). 훈련 신호가 전이를 예측하지 못하는 국면의 존재는 RL에서 반복 보고된 사실.

**출처 검증 표기**: 네 건 모두 실존 확인(공식 arXiv/NeurIPS/OpenAI 원문 링크). BenchBench의 'adjacent 모델 상관 하락' 서술은 논문 HTML판 스니펫에서 확인 — 인용 전 해당 절 정독 권장.

## 4. 우리 데이터로 가능한 방어 분석 3개 (절차 수준)

**D1. 구간별 분산·u-ratio 병기 + 비퇴화 증거 (아티팩트의 전제 자체를 반박)**
1. 체크포인트 시계열을 전반/후반 창으로 나누고, 창별로 L과 M 각각의 SD, IQR, 고유값 개수(#distinct), 동률 비율을 표로 병기.
2. u-ratio 계산: `u_L = SD_late(L)/SD_full(L)`, `u_M = SD_late(M)/SD_full(M)` (Hunter–Schmidt 관례).
3. 핵심 주장 구성: **L은 후반 5시드 중 4에서 단조 상승 → u_L ≈ 1 근방(분산 비축소)이면 'X측 직접 제한' 시나리오(Case II의 전제)가 데이터에서 기각됨.** 제한이 있다면 M쪽(바닥효과+이산성)인데, 그건 range restriction이 아니라 측정 해상도 문제로 재분류됨(→ D3에서 처리).
4. 시드별 후반 τ-b를 각각 제시하고 rliable식 층화 부트스트랩으로 CI 병기 — "평균 τ≈0이 시드 간 상쇄가 아니라 시드 내 일관된 소멸"임을 보임.

**D2. 보정 상관 감도분석 (심사자의 프레임 안에서 정면 반박)**
1. 후반 창에서 Pearson r_late(L, M) 계산(순위상관용 보정이 없으므로 Pearson으로 병행 분석임을 명시).
2. `psych::rangeCorrection()`으로 Thorndike Case II 보정: S = 전체 창 SD, s = 후반 창 SD. L 제한 가정과 M 제한 가정 두 방향 모두 계산.
3. 극한 감도분석: u를 관측값에서 0.5까지 격자 스윕하며 보정 r을 그려, **"어떤 그럴듯한 u에서도 보정 상관이 전반 수준(+0.57 상당)으로 복원되지 않는다"**를 그림 1장으로 제시.
4. 반드시 명기할 한계(선제 방어): Case II는 선형·등분산 가정이며 우리 데이터(단조 상승 L, 바닥의 M)는 이를 위반 → 보정값은 추정이 아니라 **상한 성격의 감도분석**으로만 제시 (Culpepper 2016, Sackett & Yang 2000 인용). 이 프레이밍이 되레 '공식 하나로 재보정하라'는 후속 요구를 차단함.

**D3. 시뮬레이션 기반 검정력 분석 (가장 강한 방어 — '탐지했어야 하는데 못 했는가'를 정량화)**
1. **H1 생성모형**: 전반 τ=+0.57에 해당하는 코풀라(예: Gaussian copula, ρ = sin(π·τ/2))로 잠재 의존구조를 고정.
2. **주변분포는 관측 그대로**: L은 후반 창의 관측값(시드별 단조 상승 궤적), M은 관측 이산 주변분포(0~33%, 시행 수 k의 이항 성공률로 모델링해 동률 구조 재현). 잠재 연속변수를 관측 이산 M으로 사상(quantile coupling).
3. 시드당 후반 체크포인트 수 n으로 5시드 × 10,000회 반복 생성 → 각 반복에서 τ-b 계산 → **"진짜 τ가 0.57이었다면 관측될 τ-b의 분포"** 획득.
4. 검정력 보고: `P(τ̂-b ≤ 관측 후반 τ-b | H1)` — 이 확률이 작으면(예: <0.05) "range restriction + 동률 + 소표본을 전부 반영해도 τ≈0은 진짜 상관 존속과 양립 불가"가 결론. 반대로 크면 그 자체가 정직한 한계 보고가 됨. (동일 시뮬레이터로 관측 동률 구조에서의 **도달 가능 최대 τ-b 상한**도 산출해 병기 — Genest & Nešlehová 2007 논거.)
5. 보조: 전반 vs 후반 τ 차이의 **순열검정** — 체크포인트의 창 라벨을 시드 내에서 순열해 Δτ 영분포 생성 (소표본에서 순열검정이 부트스트랩보다 우수 — [비교 문헌](https://arxiv.org/pdf/1602.03727), [randomization test](https://arxiv.org/pdf/1811.02105)). 시뮬레이션 검정력 절차의 상용 선례로 [NCSS PASS: Kendall's Tau-b Tests (Simulation)](https://www.ncss.com/wp-content/themes/ncss/pdf/Procedures/PASS/Kendalls_Tau-b_Correlation_Tests-Simulation.pdf) 인용 가능.

## 권고

1. 논문 본문 방어 순서는 D1(전제 반박: L 분산 비축소 + u-ratio 표) → D3(코풀라 시뮬 검정력) → D2(Case II 감도분석)로 배치하고, D2는 '가정 위반을 명기한 감도분석'으로만 프레이밍할 것 — 보정값을 추정치로 내세우면 역공당함
2. 후반 τ는 반드시 τ-b(동률 보정)로 보고하고 Goodman–Kruskal γ를 병기, M의 동률 구조에서 도달 가능한 최대 |τ-b| 상한을 함께 제시해 '0 대 상한' 비교로 읽히게 할 것
3. 가능하다면 M을 이진 성공률 대신 연속 전이 수익(또는 성공까지 스텝 수)으로 재정의한 보조 분석을 추가 — 바닥효과·동률 논점을 데이터 수준에서 제거하는 가장 깨끗한 방어
4. 대안 설명의 선례로 Gao et al. (arXiv:2210.10760)의 proxy–gold 탈동조와 BenchBench(arXiv:2407.13696)의 adjacent-subset 상관 하락을 함께 인용: 전자는 'τ≈0이 실재 현상'임을, 후자는 '구간별 병기 보고가 표준 관행'임을 뒷받침
5. 5시드 불확실성은 Agarwal et al. 2021 (rliable)의 층화 부트스트랩 CI로 정량화하고, 전반/후반 τ 차이는 시드 내 순열검정으로 p값 제시
6. 인용 전 원문 정독 필요 목록: Sackett & Yang 2000(분류체계 세부), Hunter/Schmidt/Le 2006(u-ratio 정의), Culpepper 2016(비선형 편향 크기), Genest & Nešlehová 2007(이산 주변분포 τ 상한 도출식), BenchBench 해당 절 — 본 조사는 서지·초록·스니펫 수준 검증까지만 수행함