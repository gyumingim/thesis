# 국문 용어 표준 조사 (2026-08-27)

## 강화학습 일반 용어

| 영문 | 국내 통용 표기(빈도순) | 권장 | 근거 |
|---|---|---|---|
| policy | **정책**(사실상 유일) | 정책 | 국문 문헌 전반에서 '정책', '정책 경사(policy gradient)'로 확립. [wikidocs AI/ML 사전 policy(정책)](https://wikidocs.net/120363), [정책 경사 해설](https://4four.us/article/2018/08/policy-gradient) |
| checkpoint | **체크포인트**(우세), 검사점(DB 분야 구용어, ML에선 안 씀) | 체크포인트(checkpoint) 초출 병기 | [PyTorch 한국어 공식 튜토리얼 '체크포인트 저장하기'](https://tutorials.pytorch.kr/recipes/recipes/saving_and_loading_a_general_checkpoint.html), [wikidocs AI/ML 사전 checkpoint(체크포인트)](https://wikidocs.net/201324). 국문 대역어가 정착돼 있지 않으므로 음차+영문 병기가 안전 |
| rollout | **롤아웃**(우세), 플레이아웃(MCTS 문맥), '에피소드 전개'류 풀어쓰기 | 롤아웃(rollout) 초출 병기 | [한국어 위키백과 몬테카를로 트리 탐색](https://ko.wikipedia.org/wiki/%EB%AA%AC%ED%85%8C%EC%B9%B4%EB%A5%BC%EB%A1%9C_%ED%8A%B8%EB%A6%AC_%ED%83%90%EC%83%89)에서 롤아웃/플레이아웃 병용. 국문 대역어 미확립 — 음차 표기가 국내 관례 |
| fine-tuning | **미세 조정**·**파인튜닝** 혼용(KCI에 둘 다 논문 제목으로 존재) | 미세 조정(fine-tuning) — 국문 학위논문 심사에 더 안전 | TTA 정보통신용어사전에 '미세 조정' 등재([word.tta.or.kr](http://word.tta.or.kr/main.do)), KCI 논문 제목 '[대형 사전훈련 모델의 파인튜닝을 통한 강건한 한국어 음성인식 모델 구축](https://www.kci.go.kr/kciportal/ci/sereArticleSearch/ciSereArtiView.kci?sereArticleSearchBean.artiId=ART003003714)', [wikidocs fine-tuning(파인 튜닝, 미세 조정)](https://wikidocs.net/120208) |
| pretraining | **사전 학습**(압도적), 사전 훈련(소수) | 사전 학습(pre-training) | KCI 다수: '[대형 사전학습 언어모델 연구에 대한 고찰](https://www.kci.go.kr/kciportal/landing/article.kci?arti_id=ART002779266)', '[딥러닝 기반 사전학습 언어모델에 대한 이해와 현황](https://www.kci.go.kr/kciportal/landing/article.kci?arti_id=ART002917552)', '[KB-BERT: 금융 특화 한국어 사전학습 언어모델](https://www.kci.go.kr/kciportal/ci/sereArticleSearch/ciSereArtiView.kci?sereArticleSearchBean.artiId=ART002854747)' |
| zero-shot transfer | **제로샷 전이**(우세), 제로-샷(하이픈 변형) | 제로샷 전이(zero-shot transfer) | KCI '[Zero-Shot 기반 기계번역 품질 예측 연구](https://www.kci.go.kr/kciportal/ci/sereArticleSearch/ciSereArtiView.kci?sereArticleSearchBean.artiId=ART002777668)'(본문 '제로샷 교차언어 전이'), [서울대 학위논문 국문초록 '제로샷 설정에서의 전이'](https://s-space.snu.ac.kr/handle/10371/175176), KCI '[언어-기반 제로-샷 물체 목표 탐색](https://www.kci.go.kr/kciportal/landing/article.kci?arti_id=ART003109895)' |

## 강화학습 sim-to-real·비용 용어

| 영문 | 국내 통용 표기 | 권장 | 근거 |
|---|---|---|---|
| domain randomization | **도메인 랜덤화**(우세), 도메인 무작위화(소수) | 도메인 랜덤화(domain randomization) | 제어로봇시스템학회 국내학술대회 논문 '[심층강화학습의 응용을 위한 도메인 랜덤화 및 도메인 적응 기법](https://www.dbpia.co.kr/journal/articleDetail?nodeId=NODE09410393)', [서울대 학위논문 국문초록 '도메인 랜덤화 기법'](https://s-space.snu.ac.kr/handle/10371/175176) |
| domain gap | 도메인 갭(음차)·도메인 격차 혼용, 국내 학술 용례 자체가 적음. sim-to-real 문맥에선 '시뮬레이션-실환경 격차(sim-to-real gap)'로 풀어쓰는 사례도 | 도메인 격차(domain gap) 초출 병기 — 순국문 선호 심사위원까지 안전. 음차 '도메인 갭'도 허용 범위 | 확립 표기 부재가 조사 결론. 위 DBpia 논문과 [AWS 국문 기술블로그](https://aws.amazon.com/ko/blogs/tech/sim-to-real-and-real-to-sim-the-engine-behind-capable-physical-ai/) 참고 |
| sample efficiency | **샘플 효율(성)**(RL 국내 문헌 우세), 표본 효율(통계 어감), 데이터 효율(유사 표현) | 샘플 효율성(sample efficiency) 초출 병기 | 국내 RL 문헌은 '샘플/데이터 효율' 계열이 우세(예: [DBpia 심층강화학습 관련 논문들](https://www.dbpia.co.kr/journal/articleDetail?nodeId=NODE11744040)). '표본 효율'은 통계 용어 '표본(sample)'과 일관되나 RL 문헌 빈도는 낮음 |
| wall-clock (time) | **실제 실행 시간 / 실제 경과 시간**(학술·HPC 관례), 벽시계 시간(블로그·위키독스 수준) | "실제 학습 소요 시간(wall-clock time)" 식 병기. '벽시계 시간' 단독 사용은 비권장 | [기상청 국가기상슈퍼컴퓨터센터 병렬프로그래밍 문서](https://www.kma.go.kr/aboutkma/intro/supercom/super/super_program.jsp?printable=true)가 '실제 실행시간(wall-clock time)' 사용, [한국어 위키백과 표제어 '실제 경과 시간'](https://ko.wikipedia.org/wiki/%EC%8B%A4%EC%A0%9C_%EA%B2%BD%EA%B3%BC_%EC%8B%9C%EA%B0%84), '벽시계 시간'은 [wikidocs](https://wikidocs.net/216375) 등 비학술 자료 중심 |

## 통계 용어

| 영문 | 국내 통용 표기 | 권장 | 근거 |
|---|---|---|---|
| bootstrap CI | 통계학계(KCI 통계 학술지) 전통 표기 **붓스트랩**, ML/일반 문헌은 부트스트랩 | 붓스트랩 신뢰구간(bootstrap confidence interval) — 통계 전공 심사위원에게 안전. '부트스트랩'도 오류는 아님(일관성만 유지) | KCI 통계 논문 '[붓스트랩 방법을 이용한 분산의 신뢰구간 추정](https://www.kci.go.kr/kciportal/ci/sereArticleSearch/ciSereArtiView.kci?sereArticleSearchBean.artiId=ART000964917)', '[붓스트랩 기법을 이용한 환율의 장단기 신뢰구간 예측](https://www.kci.go.kr/kciportal/ci/sereArticleSearch/ciSereArtiView.kci?sereArticleSearchBean.artiId=ART001449241)'. 한국통계학회는 [통계학용어집](https://product.kyobobook.co.kr/detail/S000001136979)을 간행하며 [홈페이지 통계용어 게시판](https://www.kss.or.kr/bbs/board.php?bo_table=psd_sec) 운영(사이트 직접 조회는 403으로 실패 — 최종 확정 시 서면 용어집 확인 권장) |
| rank correlation | **순위 상관(계수)**(사실상 유일) | 순위 상관(rank correlation) | 대학 강의자료 '[Kendall의 순위상관계수](https://www.mokwon.ac.kr/aj/html/sub04/0402.html?mode=D&no=2e3073eb10dc616650cd4197973de19c&file_id=689084&category=%EC%A1%B0%EC%A0%84%EA%B7%BC)', R 교재 '[켄달의 순위 상관 계수](https://thebook.io/006723/0271/)' |
| Kendall tau | **켄달의 타우 / 켄달 순위상관계수**, 켄달의 τ | "켄달의 타우(Kendall's τ)" 초출 병기, 이후 'τ' 기호 사용 가능 | 위 목원대 강의자료·R 교재, [해설 자료](https://medium.com/@leejukyung/%EC%BC%84%EB%8B%AC%ED%83%80%EC%9A%B0-kendalltau-18fb90ba4e7). '켄달'(두음 표기)이 최빈, '켄들'은 드묾 |
| IQM (interquartile mean) | **국내 확립 표기 없음** — KCI·국문 교과서 용례 사실상 부재. 인접 표준어는 절사평균(trimmed mean) | "사분위간 평균(interquartile mean, IQM)" 초출 병기 후 약어 IQM 사용. 각주로 '25% 절사평균과 동일'을 밝히면 통계 심사위원에게 안전 | rliable 계열 지표로 국문 용례가 아직 없음([rliable 해설](https://araffin.github.io/post/rliable/), [Google Research 블로그](https://research.google/blog/rliable-towards-reliable-evaluation-reporting-in-reinforcement-learning/)). '절사평균'은 국문 표준 통계 용어([위키백과 절사평균](https://ko.wikipedia.org/wiki/%EC%A0%88%EC%82%AC%ED%8F%89%EA%B7%A0), [디지털집현전 용어정보](https://k-knowledge.kr/srch/read.jsp?id=268361918)) |

## 조어 후보 3건 판정

**1. support set = 지지집합 — 수학적 support 의미라면 표준 역어 맞음 (안전)**

대한수학회 수학용어집([kms.or.kr/mathdict](https://www.kms.or.kr/mathdict/list.html))에서 직접 확인: **support → "지지집합, 받침"**, support function → 지지함수/받침함수, supporting set → 받침집합/버팀집합. [한국어 위키백과 표제어도 '지지집합'](https://ko.wikipedia.org/wiki/%EC%A7%80%EC%A7%80%EC%A7%91%ED%95%A9). 따라서 분포·측도의 support 의미로 쓴다면 '지지집합(support)' 초출 병기로 심사 안전. **주의**: few-shot learning의 support set은 국내에서 '서포트 셋' 음차가 관례([DACON](https://dacon.io/en/forum/405801) 등)이므로, 어느 의미인지에 따라 표기를 갈라야 함. 본인 논문에서 '체크포인트들의 집합'이라는 독자 개념이라면 조어임을 밝히고 초출 시 영문 병기 필수.

**2. exploitation = 착취 — 비권장. RL 표준 역어는 '활용'(또는 '이용'), reward hacking 문맥은 '악용'**

exploration–exploitation의 표준 국문은 **탐색–활용**([wikidocs '탐색-활용 트레이드오프'](https://wikidocs.net/167325)), [한국어 위키백과 강화학습](https://ko.wikipedia.org/wiki/%EA%B0%95%ED%99%94_%ED%95%99%EC%8A%B5)은 '이용', 경영학 KCI 문헌도 [활용(exploitation)·탐험(exploration)](https://www.kci.go.kr/kciportal/ci/sereArticleSearch/ciSereArtiView.kci?sereArticleSearchBean.artiId=ART001509644). '착취'는 일부 번역 자료에만 나타나는 비표준 표기로, 학위논문에 쓰면 지적 소지가 큼. **reward hacking 문맥**에서는 (a) 현상명은 **보상 해킹(reward hacking)** — [IT위키](http://itwiki.kr/w/%EB%B3%B4%EC%83%81_%ED%95%B4%ED%82%B9), [한경 경제용어사전](https://dic.hankyung.com/economy/view/?seq=16320), [국내 언론](https://www.e-science.co.kr/news/articleView.html?idxno=133550) 모두 이 표기; (b) '보상 함수의 허점을 exploit하다'는 동사적 용법은 **'악용'**(허점을 악용)으로 옮기는 것이 국내 통용 서술이며, 탐색–활용의 '활용'과의 충돌도 피함. 즉 한 논문 안에서 exploitation(활용)과 exploit(악용)을 문맥으로 구분하고 각각 초출 시 영문 병기하는 것이 가장 안전.

**3. predictivity = 예측력 — 안전**

'예측력'은 KCI에서 광범위하게 쓰이는 확립 표현(예: '[내재변동성 측정방법에 따른 실현변동성 예측력 분석](https://www.kci.go.kr/kciportal/ci/sereArticleSearch/ciSereArtiView.kci?sereArticleSearchBean.artiId=ART001040113)'). 다만 국내 용례 대부분은 predictive power/predictive performance의 역어이므로, predictivity라는 특정 영문 용어를 지표명으로 쓴다면 초출 시 '예측력(predictivity)' 병기 권장. '예측 성능'은 모델 성능 일반을 가리킬 때의 대안.

## 초출 영문 병기 관례

조사 과정에서 확인된 KCI 논문들의 일관된 관행: 확립된 역어라도 전문용어는 **초출 시 '국문(영문)' 병기 후 이후 국문 단독 사용**이 국문 학위논문·KCI 논문의 표준 관례다(예: '사전학습 언어모델(pre-trained language model)', '제로샷 교차언어 전이(zero-shot cross-lingual transfer)', '도메인 랜덤화(domain randomization)'). 약어가 있는 용어는 '국문(영문 전체 명칭, 약어)' 형식 — 예: '사분위간 평균(interquartile mean, IQM)' — 후 약어 사용. 확립 표기가 없는 조어(IQM, 도메인 격차, 지지집합의 독자적 용법 등)는 이 병기가 선택이 아니라 필수이며, 필요하면 용어 정의 절이나 각주에서 선택 이유를 한 줄 밝히는 것이 심사 방어에 유리하다.

## 권고

1. policy → 정책 (병기 불필요할 만큼 확립; 초출 병기는 무방)
2. checkpoint → 체크포인트(checkpoint) 초출 병기 — 국문 대역어 미확립
3. rollout → 롤아웃(rollout) 초출 병기
4. fine-tuning → 미세 조정(fine-tuning) — TTA 등재 표기, '파인튜닝'보다 심사 안전
5. pretraining → 사전 학습(pre-training) — KCI 최빈 표기
6. zero-shot transfer → 제로샷 전이(zero-shot transfer)
7. domain randomization → 도메인 랜덤화(domain randomization) — 제어로봇시스템학회·서울대 학위논문 용례
8. domain gap → 도메인 격차(domain gap) 초출 병기 (확립 표기 없음, '도메인 갭'도 허용)
9. sample efficiency → 샘플 효율성(sample efficiency) 초출 병기
10. wall-clock time → '실제 학습 소요 시간(wall-clock time)' 식 병기 — '벽시계 시간' 단독 사용 비권장 (학술 관례는 '실제 실행/경과 시간')
11. IQM → 사분위간 평균(interquartile mean, IQM) 초출 병기 + '25% 절사평균과 동일' 각주 — 국내 용례 부재로 병기 필수
12. bootstrap CI → 붓스트랩 신뢰구간(bootstrap confidence interval) — 한국통계학회 계열 KCI 논문 표기; '부트스트랩'과 혼용 금지(일관성)
13. rank correlation → 순위 상관(rank correlation)
14. Kendall tau → 켄달의 타우(Kendall's τ) 또는 켄달 순위상관계수
15. support set → 수학적 support 의미면 지지집합(support) — 대한수학회 용어집 표준 역어라 안전; few-shot 의미면 서포트 셋 음차가 관례이므로 의미 구분 필수
16. exploitation → 탐색-활용 문맥은 '활용', reward hacking 문맥의 exploit은 '악용'(허점을 악용), 현상명은 '보상 해킹(reward hacking)' — '착취'는 두 문맥 모두 비권장
17. predictivity → 예측력(predictivity) 초출 병기 — KCI 확립 표현
18. 공통 관례: 전문용어는 초출 시 '국문(영문)' 병기 후 국문 단독 사용, 조어는 병기 필수 + 용어 선택 이유 각주 권장
19. 한국통계학회 홈페이지 용어집은 원격 조회가 차단(403)되어 서면 '통계학용어집'(자유아카데미)으로 붓스트랩·순위상관 표기 최종 확인 권장