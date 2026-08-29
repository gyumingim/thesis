# CARLA 폐루프 에피소드 원자료

`carla_drive.py --out` 이 남긴 에피소드 단위 JSON 이다. 논문(§5.4·§6.6)의 CARLA 수치는
전부 여기서 나온다. 이전에는 `/c/carla/` 에만 있어 저장소 밖이었고, 그래서 감사에서
"n=180 풀의 출처 미기재"로 지적됐다(2026-08-29).

## 디렉터리

| 경로 | 내용 |
|---|---|
| `evolve/`, `evolve5/` | 조건 순회 진화 루프(회전종류 × NPC × 거버너 × 마스킹). §6.6 구성 A·B 절제와 실행 기동별 표의 출처 |
| `policy_ab/` | 정책 × 거버너 절제 1라운드 (20M / 136M / MU_LAT, 각 n=20) |
| `seed_sweep/` | 시드 정합 스윕 (계획, `carla_seed_sweep.sh`) |
| `drive*/` | 초기 단일 실행 기록 |

## 레코드 스키마

`ep, kind(앵커 라벨), outcome, steps, entry_kmh, min_R, max_lat, turn_deg(실행 총 회전각),
n_junc, ood_max, ood_peak, ood_dims, ood_top_dim, ood_dim_mean[51]`

**집계 시 주의**: 기동은 `kind`(앵커 라벨)가 아니라 `turn_deg`(실행된 경로의 총 회전각)로
재라벨해야 한다 — 경로계획기가 회전 앵커에서도 직진·유턴 경로를 내놓는다(≥150° = 유턴,
<30° = 직진). `tools/carla_ab_analysis.py` 가 이 규약을 구현한다.

**정책 출처**: 파일명에 정책이 없는 배치(`evolve*`)는 전부 `C:/ue/policy.npz`
= 부호 정정판 시드 1 의 20M-step 체크포인트(GPU 경합 조건)로 실행했다.
