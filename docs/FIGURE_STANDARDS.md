# 논문 그림 표준 조사 (2026-08-27)

## 1. rliable 표준 그림 문법 — 무엇을 언제 쓰나

Agarwal et al. (NeurIPS 2021 Outstanding Paper, 'Deep RL at the Edge of the Statistical Precipice')의 rliable이 제공하는 4종 그림과 용도:

| 그림 | 보여주는 것 | 언제 쓰나 |
|---|---|---|
| **IQM 표본효율 곡선 + 층화 부트스트랩 95% CI 밴드** | 학습 진행에 따른 중앙 50% 런의 평균 성능 | 학습곡선의 표준 대체물. mean±std 곡선 대신 사용 — mean은 이상치 시드에 지배되고 median은 통계적으로 비효율적('statistically inefficient'). **fig_learning_curves에 직접 적용 대상** |
| **집계 지표 점추정 + 95% CI 구간 플롯** (IQM/median/mean/optimality gap 병렬) | 최종 성능의 점+불확실성 | 최종 비교. 막대그래프보다 구간 플롯이 rliable 표준 — **4-arm 막대의 대안 또는 보강**(막대 유지 시 95% CI 수염 필수) |
| **Performance profile** | 임계값 x 이상을 달성한 런의 비율 곡선(꼬리 분포) | 런 간 변동성·분포 전체를 보일 때. 곡선이 교차하지 않으면 확률적 지배(stochastic dominance)로 읽혀 순위 주장이 강해짐. 다과제 벤치마크에서 가장 유효 — 단일 환경 5시드에는 선택 사항 |
| **Probability of improvement** (Mann–Whitney U 기반) | 'A가 B를 이길 확률'(효과 크기와 무관) | 쌍별 우위 주장을 할 때의 검증 패널. 0.5 근처면 동급. 4-arm 비교에서 '어느 팔이 어느 팔을 이기는가'를 한 패널로 요약 가능 |

공통 원칙: 점추정만 보고하지 말 것, CI는 **층화 부트스트랩**(시드×과제 버킷에서 복원추출)으로, '소수 시드(a handful of runs)'에서도 유효하도록 설계됨.

Sources: [rliable GitHub](https://github.com/google-research/rliable), [Google Research 블로그](https://research.google/blog/rliable-towards-reliable-evaluation-reporting-in-reinforcement-learning/), [Raffin의 시각적 해설](https://araffin.github.io/post/rliable/), [AIhub 정리](https://aihub.org/2022/01/19/rliable-towards-reliable-evaluation-and-reporting-in-reinforcement-learning/)

## 2. 주행 RL / sim2real 전이 결과 시각화 모범

전이 시각화의 확립된 3가지 형식:

**(a) sim vs real 산점도 + 순위상관 주석** — 원형은 [Kadian et al., Sim2Real Predictivity (arXiv:1912.06321)](https://arxiv.org/abs/1912.06321): x=sim 성능, y=real 성능, 각 점=모델(또는 체크포인트), 항등선(y=x) 또는 회귀선과 SRCC 값을 그림 안에 주석. [SIMPLER (arXiv:2405.05941)](https://arxiv.org/abs/2405.05941)는 같은 정책의 학습 단계별 체크포인트(RT-1 Begin/15%/Converged)를 점으로 넣은 산점도 + MMRV·Pearson을 사용. RSS 2026 world simulator ([arXiv:2603.08546](https://arxiv.org/abs/2603.08546)) Fig.7도 intermediate+final 체크포인트 산점도. **본 논문에서는 경량 점수 L vs MetaDrive 점수 M 산점도에 체크포인트 시각을 색(viridis 연속 팔레트)으로 입히면, '풀링 상관이 위상별 붕괴를 가린다'는 DPC의 대조 논거(docs/DPC_NOVELTY_AUDIT.md 권고 3)를 한 장으로 보여줌.**

**(b) 시간축 전이 곡선** — 체크포인트 시점마다 전이 평가를 걸어 wall-clock/step 축 위에 전이 성능 곡선을 그리는 형식(현재 figs/fig_main_transfer_curve.png가 이 형식). 모범은 경량 학습 곡선과 전이 곡선의 **괴리 시점을 수직선·음영으로 명시**하는 것 — OpenAI ADR 논문([arXiv:1910.07113](https://arxiv.org/abs/1910.07113))의 '파라미터/성능 vs 학습 시간 + 국면 표시' 곡선이 선례.

**(c) 시드별 짝지은 선(slopegraph)** — sim 점수→real 점수를 시드마다 선으로 연결한 두 열 플롯. 막대(fig_transfer)가 평균 낙폭만 보여주는 것과 달리 시드별 이질성(어떤 시드는 전이 성공, 어떤 시드는 붕괴)을 드러냄. 전이 막대의 보조 패널로 권장.

주의: 후반 체크포인트만의 정적 상관은 [Khor & Weng (arXiv:2504.15414)](https://arxiv.org/abs/2504.15414)가 SCC≈−0.3으로 선행하므로, 전이 그림에서도 '풀링/정적' 표현과 '시간분해' 표현을 시각적으로 구분해 배치하는 것이 신규성 방어에 유리.

## 3. 학위논문 그림 형식 규범

**캡션 자기완결성**: 그림+캡션만으로 독립 판독 가능해야 함 — 무엇을, 어떤 대상에서, 패널·기호·약어·오차막대·축 전부 정의 ([Editage 가이드](https://www.editage.com/blog/figures-research-paper/)). RL 그림에서는 특히 **오차 표현의 의미(SD vs SE vs 95% CI)와 시드 수를 캡션에 명기** — Wilke [Fundamentals of Data Visualization 16장](https://clauswilke.com/dataviz/visualizing-uncertainty.html)이 SD/SE/CI 혼동을 대표적 오독 원인으로 지적. 예: "음영은 5시드 층화 부트스트랩 95% CI".

**색맹 안전 팔레트**: 범주형은 **Okabe–Ito 8색**(#E69F00, #56B4E9, #009E73, #F0E442, #0072B2, #D55E00, #CC79A7, #000000)이 사실상 표준 — Wong (Nature Methods 2011)이 대중화, R 4.0+ 기본 ([해설·헥스코드](https://vizcept.com/blog/okabe-ito-palette-guide)). 4-arm 비교에 딱 맞음(4색 이내). 범주가 8개를 넘으면 Paul Tol 팔레트, 연속값(체크포인트 시각 등)은 viridis ([과학 팔레트 정리](https://conceptviz.app/blog/scientific-color-palette-for-research-papers-and-posters)). 흑백 인쇄 생존을 위해 색에만 의존하지 말고 **선 스타일·마커를 중복 부호화**.

**벡터 포맷**: 선 그림·플롯은 PDF/SVG/EPS 벡터로, 사진·렌더만 300–600dpi 래스터 ([matplotlib 저널 설정 가이드](https://www.graphhelix.ai/blog/publication-ready-figures-python-matplotlib)). matplotlib: `savefig('fig.pdf', bbox_inches='tight')` + `rcParams['pdf.fonttype']=42`(폰트 임베드), 최종 축소 크기 기준 산세리프 6–12pt, 선 두께 ≥0.5pt. **현재 figs/*.png는 전부 래스터 — LaTeX 조판용으로 PDF 재생성 필요** (bench/plot_curves.py에서 확장자만 바꾸면 됨).

## 4. DPC 곡선 최선 형식 제안 (데이터 구조 실측 기반)

tools/dpc_metric.py 확인 결과: 시드 5개 × 체크포인트 12개, 시드 내 쌍만 집계하는 층화 Kendall τ-b, 전반(5–30분)/후반(35–60분) 창, 순환이동(circular shift) 널분포 1000회. 이 구조에 맞는 제안:

**주 패널 — 창(window)별 τ 세그먼트 + 널 수용대역 + 위상 경계** (권장 기본형):
- 체크포인트 12개로는 매끈한 슬라이딩 곡선이 통계적으로 무리 — **각 창의 τ를 창 구간에 걸친 수평 선분(step)으로, 창 중심에 점 + CI**로 그리는 것이 정직함. CI는 시드 단위 층화 부트스트랩(5시드 복원추출) 또는 leave-one-seed-out 범위.
- τ=0 기준선 대신 **순환이동 널분포의 95% 수용구간을 회색 수평 밴드**로: '후반 τ가 밴드 안 = 무정보'가 시각적으로 즉독됨. 이미 계산하는 널분포를 그대로 재활용.
- **위상 경계는 수직 점선 + 배경 음영**(전반/후반을 옅은 배경색으로 구분, 'predictive phase' / 'non-informative phase' 라벨), Δτ와 p값을 그림 내 주석. ADR 논문([arXiv:1910.07113](https://arxiv.org/abs/1910.07113))의 국면 표시 시간축 곡선이 형식 선례.
- 슬라이딩 윈도 곡선(예: 폭 25분, 보폭 5분)을 쓰려면 창 폭 민감도 점검 후에만, 그리고 **LOESS 등 평활은 금지** — 12점에서 연속성을 날조함. 창 폭·창당 쌍 수는 캡션에 명기.

**보조 패널 — 위상 분할 산점도** ('show the data' 원칙, [Wilke 16장](https://clauswilke.com/dataviz/visualizing-uncertainty.html)):
- 왼쪽=전반 창의 (L, M) 산점(상관 구조 보임), 오른쪽=후반 창(구름), 시드별 마커 구분. 또는 풀링 산점 하나에 체크포인트 시각을 viridis로 색칠 + 위상별 회귀선 2본 — SIMPLER([arXiv:2405.05941](https://arxiv.org/abs/2405.05941))·[arXiv:2603.08546](https://arxiv.org/abs/2603.08546)의 풀링 산점도와 같은 형식을 쓰되 시간 색을 입혀 '풀링이 붕괴를 가림'을 직접 시연 — 신규성 서사(시간분해 vs 풀링)와 그림이 일치.

**피할 것**: (a) τ 시계열의 평활 곡선화, (b) L(t)·M(t)·τ(t)의 이중축 겹침(필요하면 상하 정렬 소패널로 분리), (c) 오차 표현 정의 없는 음영. **캡션 필수 기재**: τ 변형(τ-b, 시드 내 층화), 창 정의(분), 창당 쌍 수, 널 구성(순환이동 1000회), CI 종류, t_sat=5분으로 인한 포화 전 위상 미관측 사실.

## 권고

1. fig_learning_curves를 rliable 문법으로 재작성: mean±std 대신 IQM 곡선 + 5시드 층화 부트스트랩 95% CI 밴드, CI 의미를 캡션에 명기 (출처: rliable GitHub, Agarwal et al. NeurIPS 2021)
2. 4-arm 비교는 막대 + 95% CI 수염을 기본으로 하되, 쌍별 우위 주장(예: 'arm A > arm B')을 본문에서 하면 probability-of-improvement 보조 패널을 추가해 통계적으로 뒷받침
3. 전이 결과에 sim-vs-real 산점도 1장 추가: L vs M, 체크포인트 시각을 viridis 색으로, 위상별 회귀선 2본 — DPC의 '풀링 상관은 붕괴를 가린다' 논거를 시각화하며 SIMPLER·Kadian SRCC 형식과 접속됨
4. DPC 그림은 2패널 구성: (A) 창별 층화 τ 수평 세그먼트 + 시드 부트스트랩 CI + 순환이동 널 95% 수용대역(회색 밴드) + 위상 경계 수직선·배경 음영 + Δτ/p 주석, (B) 전반/후반 위상 분할 (L,M) 산점도. 12체크포인트에서 슬라이딩 평활 곡선은 피할 것
5. 모든 그림을 벡터 PDF로 재생성 (bench/plot_curves.py에 savefig('*.pdf', bbox_inches='tight') + rcParams['pdf.fonttype']=42), 팔레트는 Okabe-Ito 고정, 같은 arm은 모든 그림에서 같은 색 + 선스타일/마커 중복 부호화로 흑백 인쇄 대응
6. FT 라벨 예산 곡선은 fig_budget_ext와 동일 문법(로그 x축 예산, 예산점마다 IQM+CI)으로 통일해 그림 간 일관성 유지
7. 캡션 자기완결성 체크리스트를 전 그림에 적용: 시드 수, 오차 표현 종류(95% CI vs SD), 평가 프로토콜(30ep 성공률 등), 약어 정의를 캡션 안에서 완결