#!/bin/bash
# 학습이 끝나는 **순간**을 기다렸다가 두 감시를 돌려 둔다 — 사전 등록 절차의 2단계.
#
# 사전 등록(STATUS): 학습 종료 → **두 검사 통과 확인** → 도구 시드 목록 확장 → 재계산 →
# 논문 반영. 1단계와 2단계 사이에 사람이 끼면 기계가 노는 시간이 길어지므로, 종료 표식을
# 기다렸다가 2단계만 자동으로 해 둔다. **3단계 이후는 하지 않는다** — 도구 확장과 재계산은
# 검사 통과를 확인한 뒤에 의도적으로 해야 한다.
#
# 정숙 조건: 폴링은 sleep 뿐이라 부하가 없고, 검사는 학습이 끝난 뒤에만 돈다.
set -u
cd "$(dirname "$0")/.."
PY=/c/Users/a3162/thesis/.venv/Scripts/python.exe
LOG=bench_results/seeds6to10/after_done.log
export PYTHONUTF8=1
for _ in $(seq 1 240); do            # 최대 4시간
  grep -q SEEDS6TO10_DONE bench_results/seeds6to10/console.log 2>/dev/null && break
  sleep 60
done
if ! grep -q SEEDS6TO10_DONE bench_results/seeds6to10/console.log 2>/dev/null; then
  echo "$(date +%H:%M) 종료 표식을 못 봤다 — 학습이 아직이거나 실패했다" >> $LOG
  exit 1
fi
sleep 20                              # 마지막 파일 쓰기 여유
{
  echo "=== $(date +%H:%M) 학습 종료 확인, 감시 실행 ==="
  echo "--- paper_numbers_check ---"
  $PY tools/paper_numbers_check.py 2>&1 | grep -E "건너뜀|불일치|일치$"
  echo "--- carla_numbers_check ---"
  $PY tools/carla_numbers_check.py 2>&1 | grep -E "건너뜀|불일치|일치$"
  echo "=== 여기까지가 사전 등록 2단계. 3단계(도구 확장)는 사람이 확인하고 시작한다. ==="
} >> $LOG 2>&1
