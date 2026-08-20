# 단안 카메라 깊이/3D 위치 추출 조사 (플로우 A 설계 근거)

작성 2026-08-20. 목적: 이미지 → 주변 차량 3D 위치(우리 인터페이스 규격) 모델의 접근 선정.

## 1. 테슬라는 어떻게 하나 (공식 논문은 없음 — 발표·특허가 1차 자료)

테슬라는 학술 논문을 거의 내지 않는다. 실제 1차 자료는 AI Day(2021/2022)와 CVPR 워크숍
키노트(Ashok Elluswamy, CVPR 2022 WAD / [CVPR'23 WAD](https://www.youtube.com/watch?v=6x-Xb_uT7ts)):

- 카메라 8대, vision-only. 카메라별 특징 추출 → 트랜스포머로 BEV(조감) 공간 투영
  → **vector space**(객체 리스트) + **Occupancy Network**(3D 복셀 점유 확률 + 미래 운동).
- **핵심 발언: "픽셀 단위 depth는 문제가 많다"** — 이미지 공간 depth map 을 중간 표현으로
  쓰는 것을 명시적으로 거부하고, 3D 공간을 직접 예측한다.
  ([CVPR 2022 발표 정리](https://gaussian37.github.io/autodrive-concept-tesla_cvpr_2022/),
  [해설](https://www.thinkautonomous.ai/blog/occupancy-networks/))
- 학술계의 근접 대응물: Lift-Splat-Shoot(NVIDIA), BEVFormer, TPVFormer/Occ3D 계열.

**우리에게 주는 함의**: "이미지→depth map→위치" 2단이 아니라 **"이미지→3D 위치" 직접 회귀**가
테슬라 철학이며, 우리 관측 인터페이스(객체 리스트)와도 정확히 일치한다.

## 2. 접근 3가지 비교 (우리 과제: 전방 단안, 차량 상대 3D 위치)

### A. 지면평면 기하 (학습 0, 즉시 가동)
2D 검출 bbox 하단 모서리 + 카메라 높이 h + 평지 가정 → 광선-지면 교점 = 거리.
- 근거: bbox 하단 세로좌표가 거리의 지배 신호, ground-plane 방식 중앙값 상대오차 ~0.12
  ([MDPI 2025](https://www.mdpi.com/2079-9292/14/7/1291), [Ground Plane Polling](https://arxiv.org/pdf/1811.06666))
- 우리 시뮬은 완전 평지 → 가정이 정확히 성립. **v0 베이스라인으로 최적.**
- 한계: 실세계 경사·요철에서 붕괴, 높이 h 캘리브레이션 민감.

### B. 모노 3D 검출기 직접 학습 (본명 후보)
이미지 → 차량별 (위치, 크기, 요각) 직접 예측. KITTI 계열 표준 과제
(MonoDLE/MonoDETR/[MonoDETRNext](https://arxiv.org/pdf/2405.15176), 2025-26에도
[MonoPRIO](https://arxiv.org/pdf/2605.14781) 등 활발).
- 학계 공통 병목 = **라벨 데이터 부족 (KITTI ~7천 장)** — 우리는 생성기로 무제한 해결.
  이게 플로우 A(합성 데이터 공장)의 존재 이유와 정확히 맞물린다.
- 테슬라 철학(직접 3D)과 일치. **v1 본명.**

### C. 파운데이션 metric depth 모델 + 2D 검출 결합
제로샷 미터 단위 depth: Depth Pro(Apple), Depth Anything V2, Metric3D v2, UniDepth(V2).
- 야생 벤치마크에서 DA V2 MAE 0.45m 급, Depth Pro 는 in-the-wild 강함
  ([벤치마크](https://arxiv.org/abs/2510.04723), [서베이](https://www.mdpi.com/2073-431X/14/11/502),
  [Depth Pro 해설](https://learnopencv.com/depth-pro-monocular-metric-depth/))
- 장점: 학습 불필요, 강력한 프라이어. 단점: 무겁고, depth map 중간표현(테슬라가 기각한 경로),
  합성 도메인에서의 오차 특성 미검증.
- 용도: **v1 의 교사(distillation) 또는 비교군.** 5080에서 추론 가능.

## 3. 결정 제안

| 단계 | 방법 | 왜 |
|---|---|---|
| v0 (즉시) | A. 지면평면 기하 | 학습 0으로 파이프라인 끝까지 관통 + 오차 하한 기준선 |
| v1 (본명) | B. 모노 3D 직접 회귀, 우리 합성 GT로 학습 | 데이터 병목을 생성기가 해소, 테슬라 철학, 인터페이스 일치 |
| 비교/교사 | C. Depth Pro 또는 DA V2 | 제로샷 기준선, 필요 시 distillation |

인지 오차 통계(거리별 σ)는 B4(RL 노이즈 주입 실험)의 입력이 된다.
