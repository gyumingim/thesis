# 유사 선례·모범관행 조사 (2026-08-28, 부호 오류 발견 후속)

## 0. 조사 결론 요약 (먼저 읽을 것)

**핵심 판단: 이 버그는 "우리만의 실수"가 아니라 문헌에 이름이 붙은 실패 클래스다.** 좌표 프레임/부호 규약 불일치는 (a) 표준이 존재하고(ROS REP-103), (b) 전용 정적 분석 도구가 개발돼 있고(PHYSFRAME, Phys/PhrikyUnits), (c) 표준 엔지니어링 완화책이 확립돼 있고(경계 1곳의 명시적 어댑터 — CARLA ros-bridge의 `y → -y`), (d) **이 클래스 때문에 출판된 결과가 무효화된 선례가 여러 분야에 존재한다**(Science 5편 철회, MRI 공개 데이터셋 좌우 반전, arXiv RL 논문 철회).

따라서 논문의 올바른 대응은 "버그를 숨기고 재실험 결과만 싣는 것"도 "결과를 폐기하는 것"도 아니라, **§4(정합 라운드)에 R7을 추가하고 §7에 정정 노트를 신설하여, 우리 사례를 이 실패 클래스의 sim-to-sim RL 도메인 재현 사례로 승격시키는 것**이다. 특히 아래 두 가지가 새로운 기여로 남는다:

1. **거울상 관측이 남기는 지문이 "시뮬레이터 착취"의 지문과 거의 구별되지 않는다**는 발견. §6.3에서 우리는 "과제 포화 후 잔여 격차 착취"로 오진했다. 이건 문헌에 없는 유용한 negative result다.
2. **대조군 실험(MetaDrive 네이티브 정책에 같은 보정 → 55%→0%)이 그 자체로 정식 오라클**이다. 이는 소프트웨어공학의 metamorphic relation(대칭 변환)과 정확히 같은 구조이며, "규약 정합 검증 체크리스트"의 핵심 항목으로 일반화 가능하다.

검증 표기: ✅ = export.arxiv.org / Crossref / 직접 fetch 성공, ⚠️ = 검색 결과 기반(직접 접근 미확인 또는 403 차단).

## 0-1. 우리 전제의 1차 검증 (MetaDrive 소스 실측)

문헌 조사 전에 전제를 코드로 확정했다. **배경에 적힌 진단이 소스 수준에서 정확하다.**

`C:\Users\a3162\thesis\.venv\Lib\site-packages\metadrive\component\vehicle\base_vehicle.py:1027-1029`
```python
def convert_to_local_coordinates(self, vector, origin):
    ret = super(BaseVehicle, self).convert_to_local_coordinates(vector, origin)
    return np.array([ret[1], -ret[0]])
```

`C:\Users\a3162\thesis\.venv\Lib\site-packages\metadrive\base_class\base_object.py:491-505` 는 Panda3D 노드 상대 벡터 `(x, y)` 를 그대로 반환한다. Panda3D 의 바디 프레임은 **+X 우, +Y 전방, +Z 상(Z-up 오른손계)** 이므로, `[y, -x] = (전방, 좌+)` 이다. 같은 파일 1032-1033 행의 `heading_theta = super().heading_theta + π/2` 도 이 90° 오프셋과 정합한다.

→ **MetaDrive 차량 로컬 프레임 = (종방향 전방, 횡방향 좌+). 이는 ROS REP-103(x forward, y left, z up)과 동일 규약이다.** 우리 `bench/env_numba.py` 의 (전방, 우+)는 REP-103 위반이자 MetaDrive 규약의 거울상이다.

**논문에 쓸 문장(권장)**: 규약 불일치를 "우리 관측"이 아니라 **참조 구현의 코드 + 국제 표준** 두 개의 외부 근거로 못박을 수 있다. 이것이 R1 진단이 실패한 이유의 핵심이기도 하다 — R1 의 "동역학 배제 좌표 프로브"는 **자기참조적(self-referential)** 이었다. 우리 정의가 우리 정의와 일치하는지만 확인했고, 타깃의 정의를 외부 오라클로 삼지 않았다.

**부수 발견 (§4 표의 정정 지점)**: `PAPER.md` §4 표 R1 행의 수정란이 현재 `lateral 우+` 로 적혀 있다. 즉 **R1 은 증상(부호)은 맞게 진단했으나 잘못된 규약을 설치한 라운드**였다. 이 행 자체가 버그의 기원 기록이므로, 정정 시 이 행을 지우지 말고 "R1: 부호 축을 발견했으나 규약 방향을 반대로 확정"으로 남기는 것이 정직성과 서사 양쪽에 유리하다.

## Q1. 좌표계·부호 규약 오류가 실험 결론을 바꾼 공개 사례

### A. 가장 강력한 선례 — 부호 뒤집힘이 5편 철회로 이어진 사건 ✅
- **Chang, Roth, Reyes, Pornillos, Chen, Chen. "Retraction." *Science* 314(5807):1875, 2006.** DOI `10.1126/science.314.5807.1875b` (Crossref 검증)
- **Jeffrey, P.D. "Analysis of errors in the structure determination of MsbA." *Acta Cryst.* D65:193–199, 2009.** DOI `10.1107/S0907444909001292` (Crossref 검증)
- 요지: 자체 제작 데이터 축약 프로그램이 anomalous difference 의 **부호를 뒤집어** `(I+, I−)`를 `(F−, F+)`로 바꿨고, 그 결과 **손대칭(handedness)이 반전된 맵**에 정상 기하 모델을 끼워 맞췄다. 5년치 연구와 5편(Science 3, JMB 1, PNAS 1)이 철회됐다. 경쟁 그룹이 전혀 다른 구조를 내놓으면서 발견됐다. Jeffrey(2009)는 사후 분석에서 **어떤 표준 검사를 했으면 잡혔는지**를 정리한다.
- 우리 인용법: §7 정정 노트의 첫 문장. "단일 부호 오류가 결론을 바꾼 사례는 계산과학 전반에 존재하며, 가장 유명한 사례에서는 손대칭 반전이 5편 철회로 이어졌다." **우리 사례가 예외적 무능이 아니라 알려진 실패 모드임을 확립**하는 용도.

### B. 우리와 위상이 완전히 동일한 사례 — 공개 데이터셋의 좌우 거울상 ✅
- **Glen, Taylor, Buchsbaum, Cox, Reynolds. "Beware (Surprisingly Common) Left-Right Flips in Your MRI Data: An Efficient and Robust Method to Check MRI Dataset Consistency Using AFNI." *Frontiers in Neuroinformatics* 14:18, 2020.** DOI `10.3389/fninf.2020.00018` (직접 fetch 검증)
- 요지: **FCP, OpenFMRI, ABIDE 등 주요 공개 저장소에 체계적 좌우 반전이 존재**했고 각 컨소시엄이 확인·수정했다. 원인은 헤더 정보 오류/누락, DICOM 필드 해석, NIfTI 변환 단계. 핵심 문장: *"올바른 방향은 이 문제를 찾고 있을 때조차 시각적으로 자명하지 않은 경우가 많다."* 저자들은 **원본과 의도적으로 뒤집은 버전의 정합 비용을 비교하는 자동 탐지 프로토콜**을 제시하고 178명에서 100% 정확도를 보고했다.
- 우리 인용법: **이 논문 하나가 Q1 과 Q4 를 동시에 커버한다.** (a) 거울상 규약 오류는 흔하고 육안으로 안 보인다 → §7 정정 노트, (b) "의도적으로 뒤집은 대조군과 비교하라"는 탐지 프로토콜 → 우리 대조군 실험(MetaDrive 네이티브 55%→0%)과 **방법론적으로 동일**. 부록 A 체크리스트의 근거 문헌으로 삼을 것.

### C. RL 논문이 관측 전처리 버그로 실제 철회된 사례 ✅ (가장 직접적)
- **Malato & Hautamäki, "Search-Based Adversarial Estimates for Improving Sample Efficiency in Off-Policy Reinforcement Learning." arXiv:2502.01558 — 철회됨(withdrawn), 최종 2025-06-13.**
- 철회 코멘트 원문(export.arxiv.org 검증): *"Bug in code invalidates results: double normalization on input for baseline method decreases gradients and is responsible for sample inefficiency. Currently under investigation"*
- 요지: **베이스라인의 관측 입력 전처리 버그가 sample-efficiency 우위 주장을 통째로 무효화**했다. 우리 사례("경량 대량 샘플이 고충실도를 못 이긴다"는 주장이 관측 좌표 버그 위에 있었음)와 **구조가 같다** — 비교의 한쪽 팔에만 있는 입력 파이프라인 결함이 비교 결론을 만들어냈다.
- 우리 인용법: §7 정정 노트에서 **"RL 분야에서도 관측 파이프라인 버그로 결론이 무효화된 최근 선례"**로 직접 인용. arXiv 철회 코멘트를 그대로 인용하면 톤 설정에도 좋다(짧고, 원인 명시적이고, 방어적이지 않음).

### D. 시뮬레이터 경계에서의 규약 불일치 — 엔지니어링 문헌의 표준 사례
- **CARLA ros-bridge, `carla_common/transforms.py`** ✅ (raw GitHub 직접 fetch 검증)
  ```python
  ros_translation.y = -carla_location.y   # "Considers the conversion from left-handed
                                          #  system (unreal) to right-handed system (ROS)"
  yaw = -math.radians(carla_rotation.yaw)
  ```
  요지: UE(왼손계) ↔ ROS(오른손계) 변환이 **경계 1곳의 명시적·주석 달린 어댑터로 격리**돼 있다. CARLA 문서 자체의 yaw/roll/pitch 손대칭 기술이 비일관적이라 커뮤니티 이슈가 반복 제기됐다(ros-bridge issue #637, #307).
- **NVIDIA Isaac Gym → Isaac Lab 쿼터니언 규약(xyzw ↔ wxyz)** ⚠️(NVIDIA 공식 문서 기반, 검색 결과): Isaac Gym Preview는 `xyzw`, Isaac Lab/Isaac Sim은 `wxyz`. 마이그레이션 문서가 **"관측 버퍼의 모든 쿼터니언을 변환하지 않으면 정책이 조용히 실패한다"**고 명시. Isaac Lab 3.0에서 PhysX/Newton/Warp에 맞춰 다시 `xyzw`로 되돌림.
- 우리 인용법: §4 R7 및 부록 A. **"규약은 선언이 아니라 경계에 놓인 타입이다"**는 교훈의 산업 근거. 우리 실패는 경계 어댑터가 **없었기** 때문이고, CARLA/Isaac 은 그 어댑터를 명시적으로 두거나(전자) 두지 않아 반복적으로 실패했다(후자).

### E. 소프트웨어 버그가 15년치 문헌 해석을 뒤흔든 사례 ✅
- **Eklund, Nichols, Knutsson. "Cluster failure: Why fMRI inferences for spatial extent have inflated false-positive rates." *PNAS* 113(28):7900–7905, 2016.** DOI `10.1073/pnas.1602413113` (pnas.org 는 403 봇 차단 → Oxford ORA 레코드로 서지·초록 검증)
- 요지: SPM/FSL/AFNI 의 클러스터 단위 다중비교 보정이 명목 5% 대비 **최대 70% 위양성률**. 원인은 공간 자기상관함수의 비가우스성 + AFNI `3dClustSim` 의 오래된 버그. 3백만 회 그룹 분석으로 실측.
- 우리 인용법: §2.5 또는 §7. "검증되지 않은 채 관행이 된 파이프라인은 오래 버틴다"는 논지. 우리의 6라운드 정합이 **7번째 층(좌표 규약)을 못 잡은 이유**가 프로브 자체가 자기참조적이었기 때문이라는 서술과 짝을 이룬다.

### F. 보조 사례 ⚠️(검색 기반, 인용 전 재확인 권장)
- **Herndon, Ash, Pollin (2014), *Cambridge Journal of Economics*** — Reinhart-Rogoff 의 Excel 범위 선택 오류(20개국 중 15개국만 평균). 정정 시 **−0.1% → +2.2%** 로 헤드라인 결론이 반전. "단일 구현 오류가 정책적 결론을 뒤집은" 표준 예시.
- **NASA Mars Climate Orbiter Mishap Investigation Board Phase I Report (1999)** — 지상 항법 소프트웨어의 파운드/뉴턴 단위 미변환. 보고서의 진짜 결론은 "단위 오류"가 아니라 **"검증·확인 절차가 인터페이스 명세 준수를 확인하지 않았다"**. 미러: `https://www.dcs.gla.ac.uk/~johnson/Mars/MCO_report.pdf`

## Q2. 전이 실패가 알고리즘이 아니라 인터페이스·규약 불일치였다는 보고 (로보틱스·자율주행)

### A. 핵심 인용 — reality gap 의 원인 목록에 "좌표 표현"이 명시된 최신 리뷰 ✅
- **Aljalbout et al. "The Reality Gap in Robotics: Challenges, Solutions, and Best Practices." *Annual Review of Control, Robotics, and Autonomous Systems*, 2026. arXiv:2510.20808** (2025-10-23 제출, journal_ref 확인)
- 요지: reality gap 의 원인을 **dynamics / perception / actuation / system design** 네 축으로 구조화하고, gap 자체를 재는 지표와 전이 성능을 재는 지표를 명확히 구분한다.
- 우리 인용법: §2.2 의 최신 앵커. 특히 **"system design"** 축이 우리 R1–R7 계층(관측 규약 → 정규화 → 동역학 → 종료 규칙 → 판정 기하 → 경로 기하)을 문헌에 접속시키는 고리다. 우리 §4 는 이 축의 **경험적 세분화**로 포지셔닝할 수 있다.

- **Muratore, Ramos, Turk, Yu, Gienger, Peters. "Robot Learning from Randomized Simulations: A Review." *Frontiers in Robotics and AI*, 2022. arXiv:2111.00956** ✅
- 요지(직접 관련 문장): reality gap 의 전형적 원인으로 **"different coordinate representations, numerical solvers, friction and contact models"** 를 나란히 열거한다. **좌표 표현 차이가 마찰·접촉 모델과 동급의 gap 원인으로 리뷰에 명시돼 있다.**
- 우리 인용법: §4 R7 도입부에서 결정적. "좌표 표현 차이는 도메인 랜덤화 리뷰가 마찰 모델과 동급으로 열거하는 gap 원인이다" — 우리 버그를 사소한 코딩 실수가 아니라 **문헌이 예고한 실패 지점**으로 재프레이밍한다.

### B. 시뮬레이터끼리도 안 맞는다는 실측 ✅
- **Collins, Howard, Leitner. "Quantifying the Reality Gap in Robotic Manipulation Tasks." ICRA 2019. arXiv:1811.01484**
- 요지: 동일 로봇·동일 궤적을 V-REP / PyBullet / MuJoCo 에서 돌리고 모션캡처 ground truth 와 비교. 시뮬레이터 간 불일치 구간을 정량화.
- 우리 인용법: §2.2 및 §6. **"동일 과제 선언 ≠ 동일 과제"** 주장의 실측 근거. 우리 §4 교훈 문장("동일 과제는 선언이 아니라 계층별 검증 대상")에 붙일 것.

### C. sim-to-sim 을 sim-to-real 앞의 필수 검증 단계로 명시한 문헌
- **Rothert et al. "Sim-to-Real Transfer for a Robotics Task: Challenges and Lessons Learned." IEEE ETFA 2024** ⚠️(IEEE Xplore, 서지 검색 검증 / 전문 미열람)
- 요지: 세 가지 교훈 중 하나가 **"실로봇 통합 전에 sim-to-sim 전이로 도메인 전이를 철저히 평가하라"**.
- 우리 인용법: 우리 논문의 실험 설계(경량 → MetaDrive 전이 시험장)가 **이 문헌이 권고하는 프로토콜 그 자체**임을 밝히는 데 쓴다. 즉 우리는 권고를 따랐고, 그 권고를 따랐기 때문에 버그가 결국 드러났다 — 방법론 옹호 논거로 강력하다.

- **Huang, Zhang, Cao, Liu, Xu, Ding, Francis, Chen, Zhao. "What Went Wrong? Closing the Sim-to-Real Gap via Differentiable Causal Discovery." CoRL 2023. arXiv:2306.15864** ✅
- 요지: 환경 파라미터와 sim-to-real gap 사이의 **인과 그래프를 학습**해 어떤 파라미터가 실제로 gap 을 만드는지 식별(COMPASS). 파라미터 탐색 공간을 pruning 하고 해석가능성을 제공.
- 우리 인용법: §7 향후 연구. **"gap 의 원인을 사람이 라운드로 더듬는 대신 자동 귀속하는 방향"** — 우리 R1–R7 수작업 진단의 자동화 대안으로 제시.

### D. 배경 서베이 ✅
- **Höfer et al. "Perspectives on Sim2Real Transfer for Robotics: A Summary of the R:SS 2020 Workshop." arXiv:2012.03806** — 워크숍 합의 기반 권고 목록. §2.2 배경.
- **Zhao, Queralta, Westerlund. "Sim-to-Real Transfer in Deep RL for Robotics: a Survey." IEEE SSCI 2020, pp.737–744. arXiv:2009.13303** ✅ (journal_ref 확인)

### E. "알고리즘이 아니라 시스템·조작 오류였다"는 대규모 실증 ⚠️
- **Atkeson et al. "What Happened at the DARPA Robotics Challenge Finals."** (CMU PDF: `https://www.cs.cmu.edu/~cga/drc/jfr-what.pdf`)
- 요지: **상위 6개 팀 전부가 낙하·리셋·과제 실패로 이어진 중대한 조작자 오류를 겪었다.** 저자 결론: 로봇 성능 개선의 최고 비용효율 수단은 알고리즘이 아니라 **오류 검출·예방 소프트웨어 안전장치**. "드문 성공의 비디오가 아니라 일관된 실세계 결과"로의 패러다임 전환을 요구.
- 우리 인용법: §7. 우리 논문이 "알고리즘 비교"에서 "인터페이스 검증 방법론"으로 기여 축을 옮기는 것을 정당화하는 근거.

## Q3. ML 재현성·버그 문헌, 그리고 정직하게 다루는 모범 관행

### A. 결론이 알고리즘이 아니라 구현/프로토콜에 달려 있었던 유명 사례 ✅
- **Engstrom et al. "Implementation Matters in Deep Policy Gradients: A Case Study on PPO and TRPO." ICLR 2020. arXiv:2005.12729** (*이미 §2.3에 인용 중*) — 코드 레벨 최적화가 PPO 의 TRPO 대비 보상 우위 **대부분**을 설명. 알고리즘 차이가 아니었다.
- **Henderson et al. "Deep Reinforcement Learning that Matters." AAAI 2018. arXiv:1709.06560** (*이미 인용 중*) — 코드베이스·시드·하이퍼파라미터가 결론을 바꾼다.
- **Athalye, Carlini, Wagner. "Obfuscated Gradients Give a False Sense of Security." ICML 2018. arXiv:1802.00420** ✅ — ICLR 2018 방어 기법 **9편 중 7편이 gradient obfuscation 에 의존**했고 6편 완전·1편 부분 무력화. **평가 프로토콜 결함이 분야 전체의 결론을 만들어낸 사례.**
- **Ferrari Dacrema, Cremonesi, Jannach. "Are We Really Making Much Progress? A Worrying Analysis of Recent Neural Recommendation Approaches." RecSys 2019. arXiv:1907.06902** ✅ — 18편 중 재현 가능 39%, 재현된 7편 중 6편이 단순 근접이웃 휴리스틱에 패배. "phantom progress"라는 용어의 출처.
- **Kapoor & Narayanan. "Leakage and the Reproducibility Crisis in ML-based Science." *Patterns* 4(9):100804, 2023. arXiv:2207.07048** ✅ — **17개 분야 294편**에 누수 영향. 8종 누수 분류. **내전 예측 사례연구에서 누수를 보정하자 ML 의 우위가 사라졌다** — 우리 사례(보정하자 0%→90%)와 정확히 대칭인 서사.

> **우리 인용법(중요)**: 이 다섯 편은 §7 정정 노트가 아니라 **§1.3 기여 재정의**에 써야 한다. 논지: *"본 연구가 처음 얻은 결론(경량 대량 샘플의 열위)은 알고리즘적 사실이 아니라 인터페이스 규약의 산물이었다. 이는 ML 문헌에서 반복 확인된 패턴 — 결론이 알고리즘이 아니라 구현·프로토콜에 있었던 — 의 sim-to-sim RL 도메인 사례다."* 이렇게 쓰면 정정이 기여로 전환된다.

### B. "조용한 버그" — 왜 6라운드 프로브가 못 잡았는지의 이론적 근거 ✅
- **Tambon, Nikanjam, An, Khomh, Antoniol. "Silent Bugs in Deep Learning Frameworks: An Empirical Study of Keras and TensorFlow." *Empirical Software Engineering*, 2024. arXiv:2112.13314**
- 요지: **silent bug = 잘못된 동작을 하지만 크래시도, 행도, 에러 메시지도 없는 버그.** DL 시스템의 블랙박스·확률적 성격 때문에 특히 위험. Keras 이슈 1,168건 중 77건이 재현 가능한 silent bug.
- 우리 인용법: §4 R7 의 진단 실패 설명. **거울상 관측은 정의상 silent bug 다** — shape 도 맞고, 범위도 맞고, 정규화도 통과하고, in-domain 학습은 오히려 잘 된다. 관측 가능한 유일한 증상이 "전이 시 이탈"인데, 그건 우리가 이미 **다른 원인(착취)으로 설명해 버린** 증상이었다. 이것이 확증편향 지점이다.
- **Nikanjam, Morovati, Khomh, Ben Braiek. "Faults in Deep Reinforcement Learning Programs: A Taxonomy and A Detection Approach." arXiv:2101.00135** ✅ — Stack Overflow/GitHub 761건 분석, DRL 결함 분류 + DRLinter 검출 도구.
- **Morovati et al. "Common Challenges of Deep Reinforcement Learning Applications Development: An Empirical Study." arXiv:2310.09575** ✅

### C. 정직한 정정의 모범 관행 — 구체적 형식 근거
1. **arXiv 철회 코멘트 형식** ✅ — arXiv:2502.01558 (Q1-C). *"Bug in code invalidates results: [원인 한 문장]. Currently under investigation."* 짧고, 원인 명시적이고, 변명이 없다. **우리 §7 정정 노트 첫 문단의 문체 모델로 그대로 쓸 것.**
2. **저널 correction 형식** ⚠️ — ACS *"Correction to 'Reformulating Reactivity Design for Data-Efficient Machine Learning'"* (PMC11851427). 구조가 모범적이다: ① 버그 한 문장 기술("한 줄 누락으로 저수준 장벽이 함께 필터링되지 않음"), ② **정정 전/후 수치 병기**(R² 0.56→0.90, 0.65→0.88), ③ 재실행 결과와 변경된 표 위치 명시, ④ 결론이 어떻게 바뀌는지. **우리 정정 노트는 이 4단 구조를 그대로 따를 것.**
3. **보고 표준 문헌** ✅ — **Pineau et al. "Improving Reproducibility in Machine Learning Research (A Report from the NeurIPS 2019 Reproducibility Program)." *JMLR* 22(164):1–20, 2021. arXiv:2003.12206**
4. **Lipton & Steinhardt. "Troubling Trends in Machine Learning Scholarship." ICML 2018 Debates. arXiv:1807.03341** ✅ — 4대 병폐 중 두 가지가 우리에게 직접 적용된다: **(i) 설명과 추측의 미구분**(§6.3 "착취 메커니즘"은 실측 없이 붙인 설명이었다), **(ii) 경험적 이득의 출처 미규명**. §7 에서 자기비판의 언어를 이 논문에서 빌려오면 톤이 방어적이지 않게 잡힌다.
5. **Müller-Brockhausen, Plaat, Preuss. "Reliable validation of Reinforcement Learning Benchmarks." arXiv:2203.01075** ✅ — 결정론적 환경의 행동 시퀀스("minimal traces")를 저장해 **심사자가 대규모 계산 없이 재시뮬레이션으로 검증**하게 하는 방법. Atari Pong 기준 94GB→8MB(약 10⁴:1 압축). Gym 호환 오픈소스.
   - **우리에게 특히 유용**: 우리는 이미 300초 간격 체크포인트 타임라인(부록 A)을 갖고 있다. 여기에 **평가 에피소드의 행동·관측 트레이스**를 추가 저장하면, 이번 같은 규약 오류가 **사후에 원격 검증 가능**해진다. 부록 A 의 "프로토콜 보험" 항목을 이 문헌으로 보강할 것.

## Q4. 정합 검증 체크리스트 — 좌표계·단위·부호를 체계적으로 검증하는 프로토콜

### A. 표준 (규약의 외부 근거) ✅
- **ROS REP-103: "Standard Units of Measure and Coordinate Conventions."** Tully Foote, Mike Purvis. Status: **Active**. `https://reps.openrobotics.org/rep-0103/` (직접 fetch 검증)
  - body-fixed frame: **x forward, y left, z up** (오른손계). `_optical` 접미 프레임: z forward, x right, y down.
  - 인용할 문장(원문): *"Inconsistency in units and conventions is a common source of integration issues for developers and can also lead to software bugs."*
  - **결정적 사실**: MetaDrive 의 차량 로컬 프레임 `(전방, 좌+)` 은 REP-103 준수, 우리 `(전방, 우+)` 은 위반이다. **표준을 근거로 어느 쪽이 옳은지 논쟁 없이 확정**할 수 있다.
- **ROS REP-105: "Coordinate Frames for Mobile Platforms."** `https://reps.openrobotics.org/rep-0105/` — map/odom/base_link 프레임 계층.

### B. 자동 검증 도구 — 프레임/단위를 타입으로 취급 ✅
- **Kate, Chinn, Choi, Zhang, Tan. "PHYSFRAME: Type Checking Physical Frames of Reference for Robotic Systems." ESEC/FSE 2021. arXiv:2106.11266, DOI `10.1145/3468264.3468608`**
  - 요지: 변수의 **프레임 타입을 자동 추론**하고 불일치·규약 위반을 검출하는 타입 시스템. 공개 ROS 프로젝트 **180개에서 190건 검출, 154건 true positive**. 검출 유형에 missing frame, broken TF tree, **프레임 규약 위반(FLU↔RDF 변환이 규약과 어긋남)** 포함.
  - **우리 인용법: 부록 A 체크리스트의 이론적 근거이자 §8 향후 연구.** 핵심 명제 — *"프레임 규약은 주석이 아니라 타입이어야 한다. 우리 `env_numba.py` 의 관측 벡터는 타입 없는 float 배열이었고, 그래서 거울상이 타입 검사를 통과했다."*
- **Ore, Elbaum, Detweiler. "Dimensional inconsistencies in code and ROS messages: A study of 5.9M lines of code." IROS 2017** ⚠️(PDF: `https://cse.unl.edu/~carrick/papers/OreDEIROS2017.pdf`) — 저장소의 6%에서 차원 불일치 검출. 도구: Phriky-Units (ISSTA 2017), 어노테이션 불필요.
- **Canelas, Tabor, Ore, Fonseca, Le Goues, Timperley. "Is it a Bug? Understanding Physical Unit Mismatches in Robot Software."** ✅ (PDF 직접 fetch·본문 추출 검증: `https://clairelegoues.com/assets/papers/canelas2024physunits.pdf`)
  - 요지: Phys 가 검출한 **180건 오류를 수작업 검사**해 3종 불일치·8개 상위 범주 분류. **중요한 뉘앙스** — 로보틱스 코드의 단위 불일치는 *의도적인* 경우가 많아(차동구동, 소각근사, 제어) 순진한 검사는 false positive 를 낳고 개발자 신뢰를 깎는다.
  - **우리 인용법**: 체크리스트를 "모든 불일치를 금지"가 아니라 **"모든 규약 변환을 경계 1곳에 명시적으로 국소화하고 주석·테스트로 봉인"**으로 설계해야 하는 이유. CARLA ros-bridge 가 하는 방식이 정확히 이것.
- **Canelas et al. "Understanding Misconfigurations in ROS: An Empirical Study and Current Approaches." ISSTA 2024. arXiv:2407.19292, DOI `10.1145/3650212.3680350`** ✅

### C. 오라클 없는 시스템을 검증하는 방법 — metamorphic testing ✅
- **Tian, Pei, Jana, Ray. "DeepTest: Automated Testing of Deep-Neural-Network-driven Autonomous Cars." ICSE 2018. arXiv:1708.08559**
  - 요지: **아핀 변환을 포함한 metamorphic relation** 으로 자율주행 DNN 의 일관성 위반을 자동 검출. 문헌은 **"symmetry" 를 MR pattern 의 한 종류**로 정식화한다 — 기하 변환 기반 MR 은 대부분 symmetry 의 사례다.
  - **우리 인용법: 이것이 체크리스트의 방법론적 심장이다.** 우리 대조군 실험 — *"올바르게 정합된 MetaDrive 네이티브 정책에 같은 횡방향 부호 보정을 걸면 55%→0% 로 악화되어야 한다"* — 은 **거울 대칭 metamorphic relation** 그 자체다. 이 관계는 **참조 구현만 있으면 학습 없이도 5분 안에 실행 가능한 오라클**이며, R1 에서 실행했다면 버그가 즉시 드러났다.

### D. 체계적 보고 체크리스트 ✅
- **Kapoor et al. "REFORMS: Consensus-based Recommendations for Machine-learning-based Science." *Science Advances* 10(21), 2024. DOI `10.1126/sciadv.adk3452`. arXiv:2308.07832 ("REFORMS: Reporting Standards for Machine Learning Based Science")** ✅ arXiv 검증 / ⚠️ science.org 는 403
  - **32개 문항 + 가이드라인**, 컴퓨터과학·데이터과학·수학·사회과학·생의학 19명 연구자 합의.
- **Kapoor & Narayanan 의 "model info sheets"** ✅ (Patterns 2023 / arXiv:2207.07048) — 8종 누수 각각에 대해 **부재를 정당화하는 논증을 명시적으로 적게 하는 템플릿**. Mitchell et al. 의 model cards 에서 착안.
  - **우리 인용법: 이 "정당화를 강제하는 시트" 형식이 우리 체크리스트의 형식적 모델이다.** 부록 A 를 "함정 목록"에서 **"규약 정합 info sheet — 각 항목에 대해 왜 정합되었는지 증거와 함께 서술"** 로 승격시킬 것.
- **Pineau et al. ML Reproducibility Checklist / JMLR 22(164), 2021. arXiv:2003.12206** ✅

### E. 제안 — 「좌표·부호 규약 정합 체크리스트」 초안 (부록 A 신설용)
각 항목에 위 근거 문헌을 붙일 수 있다.

| # | 항목 | 근거 문헌 | 우리 사례에서 |
|---|---|---|---|
| C1 | 두 시뮬의 body-fixed frame 규약을 **표준(REP-103)에 대해** 각각 명시하라. "우리 규약"이 아니라 외부 기준에 대해 | REP-103 | ✗ 미수행 |
| C2 | 규약 변환은 **경계 1곳의 명시적 어댑터**로 국소화하고 주석·단위테스트로 봉인하라 | CARLA ros-bridge; Canelas 2024 | ✗ 변환 자체가 부재 |
| C3 | **참조 구현의 소스를 읽어** 규약을 확정하라. 문서·직관·시각화는 부족하다 | Glen 2020("육안으로 자명하지 않다"); CARLA 문서 비일관성 | ✗ 자기참조 프로브만 수행 |
| C4 | **거울 대칭 metamorphic test**: 참조 정책에 의심 변환을 걸어 *악화*되는지 확인. 악화되지 않으면 그 축은 무의미하거나 이미 대칭 | DeepTest; Glen 2020 flip-detection | ✅ 사후 수행 → 55%→0% (규약 불일치 확증) |
| C5 | 관측 벡터의 **각 차원에 프레임/단위 타입을 부착**하고 정적 검사하라 | PHYSFRAME; Ore 2017 | ✗ 타입 없는 float 배열 |
| C6 | **정상 정책의 궤적을 두 시뮬에 재생(replay)** 하고 관측을 차원별로 비교하라 | Collins 2019; Rothert 2024 | ✗ 미수행 |
| C7 | 평가 에피소드의 **행동·관측 트레이스를 보존**해 사후 원격 검증을 가능하게 하라 | Müller-Brockhausen 2022 | 부분(체크포인트만) |
| C8 | in-domain 성공 + 전이 실패 시, **착취 가설을 세우기 전에 규약 가설을 먼저 기각**하라 (규약 오류가 더 흔하고 검사 비용이 훨씬 싸다) | Lipton & Steinhardt(설명 vs 추측); Tambon 2024(silent bug) | ✗ 순서가 반대였다 |

## 5. 논문 구조 개편 권고 (섹션별 인용 배치)

**§1.3 기여 (재정의)** — 기여를 "경량 vs 고충실도 판정"에서 **"sim-to-sim 전이의 인터페이스 정합 방법론"** 으로 이동. 근거: Engstrom(2005.12729), Athalye(1802.00420), Ferrari Dacrema(1907.06902), Kapoor & Narayanan(2207.07048) — 모두 "결론이 알고리즘이 아니라 프로토콜/구현에 있었다"는 발견 자체가 주 기여가 된 논문들.

**§2.2 (시뮬 간 정합과 전이)** — 신규: Aljalbout(2510.20808, Annual Review 2026), Muratore(2111.00956, "different coordinate representations" 문장), Collins(1811.01484), Höfer(2012.03806).

**§2.5 (보고 표준) → "보고·정정 표준"으로 확장** — 신규: Pineau(2003.12206), REFORMS(2308.07832), Kapoor & Narayanan(2207.07048), Lipton & Steinhardt(1807.03341), Müller-Brockhausen(2203.01075).

**§4 (정합 라운드) — 최대 개편 지점**
- R1 행 수정: `lateral 우+` → **"부호 축을 발견했으나 규약 방향을 반대로 확정(R7에서 정정)"**. 이 행을 지우지 말 것 — 실패 지문의 진정성이 이 논문의 자산이다.
- **R7 신설**: 불일치 계층=좌표 규약(전역), 실패 지문=**"정합 완료 후에도 전이 성공 0%/이탈 95%, 그러나 in-domain 은 정상"**, 진단 프로브=**참조 구현 소스 독해 + 거울 대칭 대조 실험**, 수정=lateral 좌+ 로 전환(idx 10, 15, 20+4k, 22+4k). 결과=**성공 0%→90%, 이탈 95%→0%, 전 체크포인트 65~95% 유지**.
- 교훈 문장 개정: 기존 "동일 과제는 선언이 아니라 계층별 검증 대상" → **"…이며, 계층 검증에는 반드시 외부 오라클이 있어야 한다. R1–R6 의 프로브는 모두 자기참조적이었고, 그래서 R7 을 6라운드 동안 통과시켰다."** 근거: REP-103, PHYSFRAME(2106.11266), DeepTest(1708.08559), Tambon(2112.13314).

**§5 (지지집합 원리)** — 원리 자체는 좌표 부호와 **독립적인 층위**이므로 논리적으로는 생존한다. 다만 R6 역설(30%→0~17%)의 수치는 버그 위에서 관측된 것이므로 **보정 후 재실험 필수**. 재실험 전까지는 원리를 "관측된 사실"이 아니라 "가설"로 표기할 것 — Lipton & Steinhardt 의 (i) 설명/추측 미구분 경계.

**§6.3 (착취 메커니즘) — 가장 무거운 재작성**
- 현행 주장(과제 포화 후 잔여 격차 착취)은 **거울상 관측의 지문을 착취로 오독한 것일 가능성이 높다**. 보정 후 "피크 후 붕괴"가 완전히 사라졌다는 실측이 이를 강하게 시사한다.
- **버리지 말고 뒤집어서 쓸 것**: 신규 소절 **"거울상 관측과 시뮬레이터 착취는 거의 동일한 지문을 남긴다"**. 둘 다 (a) in-domain 지표 정상/상승, (b) 전이 성능의 피크 후 단조 붕괴, (c) 학습 후반일수록 악화를 보인다. **이 구별 불가능성 자체가 문헌에 없는 발견**이며, DPC 진단지표의 진짜 한계를 규정한다.
- 처방(§6.5 3종 기각 포함)은 전부 재검증 대상. 근거로 Athalye(1802.00420) — 잘못된 평가 축 위에서 도출된 처방의 기각은 무효.

**§7 (논의·한계) — "정정 노트" 소절 신설**
- 형식은 ACS correction 4단 구조(버그 1문장 → 전/후 수치 병기 → 재실행 범위 → 결론 변화)를 따르고, 문체는 arXiv:2502.01558 철회 코멘트처럼 짧고 원인 명시적으로.
- 선례 인용: Chang retraction(10.1126/science.314.5807.1875b) + Jeffrey(10.1107/S0907444909001292), Glen(10.3389/fninf.2020.00018), Eklund(10.1073/pnas.1602413113), Malato(2502.01558).
- 실무 체크리스트에 **(0)번 항목 선삽입**: *"교차 시뮬 평가 전, 지지집합 감사(§5)보다 먼저 좌표·부호 규약 감사를 하라. 검사 비용이 훨씬 싸고, 실패 확률이 훨씬 높다."*

**부록 A** — 기존 "재현성 함정 목록"에 위 §4-E 의 C1–C8 체크리스트를 **"규약 정합 info sheet"** 형식(각 항목에 정합 근거를 서술)으로 추가. 근거: model info sheets(Kapoor & Narayanan), REFORMS(2308.07832).

## 6. 출처 검증 상태 (인용 전 확인용)

**✅ export.arxiv.org API 로 ID·제목·저자·날짜 검증 완료 (24건)**
`2005.12729` `2308.07832` `2012.03806` `2009.13303` `2106.11266` `1709.06560` `1802.00420` `2101.00135` `2112.13314` `2108.13264` `1907.06902` `2510.20808` `2502.01558`(철회 코멘트 원문 확인) `2203.01075` `2003.12206` `1807.03341` `2111.00956` `1811.01484` `2109.12674` `2407.19292` `1708.08559` `2310.09575` `2306.15864` `2207.07048`

**✅ Crossref API 검증 (2건)**
- `10.1126/science.314.5807.1875b` — Chang, Roth, Reyes, Pornillos, Chen, Chen. "Retraction." *Science* 314(5807):1875, 2006.
- `10.1107/S0907444909001292` — Jeffrey, P.D. "Analysis of errors in the structure determination of MsbA." *Acta Cryst.* D65:193–199, 2009.

**✅ 직접 fetch 성공 (5건)**
- `https://www.frontiersin.org/journals/neuroinformatics/articles/10.3389/fninf.2020.00018/full` — Glen et al. 2020
- `https://reps.openrobotics.org/rep-0103/` — REP-103 (Foote & Purvis, Active)
- `https://raw.githubusercontent.com/carla-simulator/ros-bridge/master/carla_common/src/carla_common/transforms.py` — y 부호 반전 코드·주석 원문
- `https://ora.ox.ac.uk/objects/uuid:31bdede9-0985-4308-a860-236750e7ccb9` — Eklund et al. PNAS 113(28):7900–7905 서지 확인
- `https://clairelegoues.com/assets/papers/canelas2024physunits.pdf` — Canelas et al. 본문 추출 확인

**⚠️ 403 봇 차단 — 문헌은 실존하나 직접 열람 실패 (대체 경로로 서지 확인함)**
- `pnas.org` (Eklund 2016) → ORA 로 확인. `journals.iucr.org` (Jeffrey 2009) → Crossref 로 확인. `science.org` (REFORMS *Science Advances*, Chang retraction) → arXiv/Crossref 로 확인.

**⚠️ 검색 결과 기반 — 인용 전 서지 재확인 권장 (6건)**
- Herndon, Ash, Pollin (2014) *Cambridge Journal of Economics* — Reinhart-Rogoff 정정
- Rothert et al., IEEE ETFA 2024, "Sim-to-Real Transfer for a Robotics Task: Challenges and Lessons Learned"
- Atkeson et al., "What Happened at the DARPA Robotics Challenge Finals" (`cs.cmu.edu/~cga/drc/jfr-what.pdf`)
- Ore, Elbaum, Detweiler, IROS 2017 (`cse.unl.edu/~carrick/papers/OreDEIROS2017.pdf`)
- ACS correction, "Reformulating Reactivity Design for Data-Efficient Machine Learning" (PMC11851427)
- NVIDIA Isaac Lab 마이그레이션 문서 (xyzw ↔ wxyz), NASA MCO Mishap Investigation Board Phase I Report (1999)

**✅ 1차 소스 (우리 환경에서 직접 실측)**
- `C:\Users\a3162\thesis\.venv\Lib\site-packages\metadrive\component\vehicle\base_vehicle.py:1027-1029, 1032-1033`
- `C:\Users\a3162\thesis\.venv\Lib\site-packages\metadrive\base_class\base_object.py:491-505`
- `C:\Users\a3162\thesis\PAPER.md` §4 표 R1 행 (버그 기원 기록), §7 실무 체크리스트

## 권고

1. 논문의 프레임을 바꿔라: '경량 vs 고충실도 판정'에서 'sim-to-sim 전이의 인터페이스 정합 방법론'으로. Engstrom(arXiv:2005.12729), Athalye(1802.00420), Ferrari Dacrema(1907.06902), Kapoor&Narayanan(2207.07048)이 모두 '결론이 알고리즘이 아니라 구현·프로토콜에 있었다'는 발견 자체로 주 기여를 세운 선례다.
2. §4 표의 R1 행('lateral 우+')을 삭제하지 말고 '부호 축은 찾았으나 규약 방향을 반대로 확정 — R7에서 정정'으로 고쳐 남겨라. 그리고 R7(좌표 규약, 지문=정합 완료 후에도 전이 0%/이탈 95%인데 in-domain 정상, 프로브=참조 구현 소스 독해 + 거울 대칭 대조, 결과=0%→90%)을 신설하라. 실패 지문의 진정성이 이 논문의 최대 자산이다.
3. §4 교훈 문장을 '동일 과제는 선언이 아니라 계층별 검증 대상이며, 계층 검증에는 반드시 외부 오라클이 필요하다'로 개정하라. R1–R6 프로브가 전부 자기참조적이었다는 것이 6라운드 동안 버그가 통과한 진짜 원인이다. 근거: REP-103, PHYSFRAME(2106.11266), Tambon silent bugs(2112.13314).
4. MetaDrive 소스 인용으로 규약을 논쟁 없이 확정하라: base_vehicle.py:1027-1029의 `return np.array([ret[1], -ret[0]])`는 Panda3D 바디 프레임(+X 우/+Y 전방)에서 (전방, 좌+)를 만들며, 이는 ROS REP-103(x forward, y left)과 동일하다. 우리 (전방, 우+)는 표준 위반이다.
5. §6.3을 폐기하지 말고 뒤집어라. 신규 소절 '거울상 관측과 시뮬레이터 착취는 거의 동일한 지문을 남긴다'로 재작성 — 둘 다 in-domain 정상/상승 + 전이 피크 후 붕괴 + 학습 후반 악화를 보인다. 이 구별 불가능성 자체가 문헌에 없는 발견이며 DPC 진단지표의 진짜 한계를 규정한다.
6. §6.5 처방 3종 기각과 DPC 지표는 전부 재검증 대상으로 명시하라. 잘못된 평가 축 위에서 도출된 기각은 무효라는 근거로 Athalye et al.(1802.00420, ICLR 2018 방어 9편 중 7편 무력화)을 인용하라.
7. §5 지지집합 원리는 좌표 부호와 독립 층위이므로 논리는 생존하지만 R6 역설 수치(30%→0~17%)는 재실험 전까지 '관측된 사실'이 아니라 '가설'로 표기하라. Lipton & Steinhardt(1807.03341)의 '설명 vs 추측 미구분' 경계선이다.
8. §7에 '정정 노트' 소절을 신설하되 형식은 ACS correction 4단 구조(버그 1문장 → 정정 전/후 수치 병기 → 재실행 범위 → 결론 변화), 문체는 arXiv:2502.01558 철회 코멘트('Bug in code invalidates results: [원인 한 문장]')처럼 짧고 원인 명시적으로 하라.
9. 정정 노트의 선례 인용 3종 세트를 쓰라: 부호 오류로 5편 철회(Science 314:1875, 2006 + Acta Cryst D65:193, 2009), 공개 MRI 데이터셋의 체계적 좌우 반전(Front. Neuroinform. 14:18, 2020), RL 논문의 관측 전처리 버그 철회(arXiv:2502.01558). 이 셋이 '알려진 실패 클래스'임을 확립한다.
10. 부록 A를 '함정 목록'에서 '규약 정합 info sheet'로 승격시켜라 — Kapoor&Narayanan의 model info sheets 형식대로 각 항목에 '왜 정합되었는지'를 증거와 함께 서술하게 만드는 템플릿. 본문의 C1–C8 체크리스트를 그대로 쓸 수 있다.
11. §7 실무 체크리스트에 (0)번을 선삽입하라: '교차 시뮬 평가 전, 지지집합 감사(§5)보다 좌표·부호 규약 감사를 먼저 하라 — 검사 비용이 훨씬 싸고 실패 확률이 훨씬 높다.' 현재 (1)번이 지지집합 감사인데 순서가 뒤집혀 있다.
12. 대조군 실험(MetaDrive 네이티브 정책 + 같은 보정 → 55%→0%)을 부끄러운 사후 확인이 아니라 정식 오라클로 승격시켜 서술하라. 이는 DeepTest(1708.08559) 계열의 거울 대칭 metamorphic relation이며, 참조 구현만 있으면 학습 없이 즉시 실행 가능하다. R1에서 했다면 버그가 그 자리에서 드러났다.
13. §2.2에 Aljalbout et al.(2510.20808, Annual Review of Control Robotics and Autonomous Systems 2026)과 Muratore et al.(2111.00956)을 추가하라. 후자는 reality gap 원인으로 'different coordinate representations'를 마찰·접촉 모델과 동급으로 열거하므로, 우리 버그를 '문헌이 예고한 실패 지점'으로 재프레이밍할 수 있다.
14. §2.5를 '소시드 RL 보고 표준'에서 '보고·정정 표준'으로 확장하고 Pineau(2003.12206, JMLR 22:164), REFORMS(2308.07832 / sciadv.adk3452), Müller-Brockhausen(2203.01075)을 추가하라. 마지막 것은 평가 트레이스 보존으로 사후 원격 검증을 가능하게 하는 방법이라 부록 A의 체크포인트 항목과 직결된다.
15. 실험 설계 방어 논거를 명시하라: sim-to-sim 전이를 실로봇 앞의 필수 검증 단계로 두라는 것이 Rothert et al.(IEEE ETFA 2024)의 권고이며, 우리는 그 권고를 따랐기 때문에 결국 버그가 드러났다. 다만 이 문헌은 IEEE Xplore 서지만 확인했으므로 인용 전 전문을 확보하라.
16. 인용 전 재확인이 필요한 6건을 별도 관리하라: Herndon-Ash-Pollin(2014), Rothert(ETFA 2024), Atkeson(DRC finals), Ore(IROS 2017), ACS correction(PMC11851427), NASA MCO 보고서. pnas.org/journals.iucr.org/science.org는 403 봇 차단일 뿐 문헌은 실존하며 각각 ORA/Crossref/arXiv로 서지를 확인해 두었다.