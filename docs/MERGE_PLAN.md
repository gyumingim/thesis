# main 병합 계획 (fix-lateral-sign)

## 병합하면 바뀌는 것

| 파일 | 변경 | 되돌릴 수 있나 |
|---|---|---|
| `bench/env_numba.py` | 횡방향 기저를 좌(+)로 정정 (2줄) | 예 — 상수 2개 |
| `bench/evaluate.py` | `--mirror-lateral` 진단 옵션 추가 | 예 — 기본 꺼짐 |
| `PAPER.md` | 대규모 개정 (정정 고지·§1.2·§1.3·§4.7·§5.4·§6.2·§6.6·§7·§8·초록·부록) | 예 — 커밋 되돌리기 |
| 신규 코드 | `carla_drive.py`, `carla_evolve*.sh`, `viz_carla_*.py`, `tools/*` | 신규라 무해 |
| 신규 문서·그림 | `docs/REVISION_*`, `docs/CARLA_CLOSED_LOOP.md`, `figs/fig_sign_error.png` 등 | 신규라 무해 |

**중요**: 부호 정정은 **학습 결과를 바꾼다**. main 의 기존 실험 산출물(runs/, bench_results/main)은
부호 오류판이므로, 병합 후에는 정정판(bench_results/fixed)만 논문 수치로 쓴다.

## 병합 전에 확인할 것

1. **주 결과 수치 확정** — 정숙 조건 3시드 48.9%±20.4% 로 확정(136M steps). 20M 경합 조건 67.8%±19.0% 는 병기. 5시드 확장·동일 장비 네이티브 기준선은 미결
   (노트북 전원 필요, 기존 5시드 체크포인트를 `--mirror-lateral` 로 재평가하면 15분)
2. **서사 방향** — 부호 사건을 §4.7 로 전면 배치(현재) vs 각주로 축소
3. **폐기 절 처리** — §6.3·§6.5 를 본문에 아티팩트 표기로 남길지, 부록으로 내릴지

## 병합 절차 (권장)

```
git checkout main
git merge --no-ff fix-lateral-sign -m "부호 규약 오류 정정과 논문 재구성 (2026-08-28)"
git push origin main
```

되돌리려면 `git revert -m 1 <merge-commit>`.

## 병합하지 않고 유지하는 선택지

브랜치를 그대로 두고 심사 원고만 브랜치에서 뽑아도 된다. main 은 "오류판 기록"으로 보존되어
§4.7 의 사례 근거(원자료)가 된다.
