#!/bin/bash
# 시드 보강 5 → 10 (2026-09-16) — 헤드라인 판정을 «구별 못함» 에서 벗어나게 할 유일한 축.
#
# 왜 지금인가. §2.5 의 「팔당 25시드(총 50시간)」는 과대였다(tools/variance_components.py):
# 표적을 b500000 한 블록의 12.7%p 가 아니라 **블록 평균 19.7%p** 로 잡고 σ 를 성분
# 분해하면 **팔당 10시드**면 80% 검정력에 닿는다. 이미 5시드가 있으므로 팔당 5시드,
# 약 10 GPU-시간이면 된다.
#
# 비교 가능성 사전 확인 (2026-09-16, 이 스크립트를 쓰기 전에 검증했다):
#  - 학습 경로 코드(ppo.py / env_numba.py / md_env.py / spec.py)가 확정 런을 만든
#    ecfe8c6 과 **바이트 동일**하다. 「혼용 금지」 규칙에 걸리지 않는다.
#  - 같은 장비다 — RTX 5080 데스크톱. 장비 교차 교락(§7)을 만들지 않는다.
#  - 프로토콜 동일: 1시간 벽시계, 300s 체크포인트, 경량 1024envs·64steps·V=3,
#    네이티브 12envs·256steps.
#
# ★ 정숙 조건 필수 — CARLA·UE 와 동시에 돌리지 않는다. 벽시계 예산 실험이라
#   경합이 결과를 조용히 오염시킨다(실측: 네이티브 62.0% → 53.3%).
# ★ **두 팔을 번갈아** 돈다. 도중에 멈춰도 팔이 균형을 유지하도록(최대 1시드 차)
#   설계했다 — 한 팔만 늘어난 상태로 중단되면 그 자료는 비교에 쓸 수 없다.
# ★ 멱등: 이미 있는 런/평가는 건너뛴다. 워치독 재시작 후 그냥 다시 부르면 된다.
set -u
cd "$(dirname "$0")/.."
PY=/c/Users/a3162/thesis/.venv/Scripts/python.exe
OUT=bench_results/seeds6to10; mkdir -p $OUT
export PYTHONUTF8=1 NUMBA_NUM_THREADS=8
unset PYTHONPATH
# b500000 도 포함한다 — (a) 의 12체크포인트 평가와 별개로, 새 시드도 옛 시드와 **같은
# 파일 배치**(scenario_blocks/…__b500000.json)를 갖게 해야 분석 도구가 8블록을 고르게 본다.
BLOCKS="500000 510000 520000 530000 540000 550000 560000 570000"

log() { echo "$(date +%H:%M:%S) $*" | tee -a $OUT/console.log; }

train() {   # train <exp> <seed> <sim args...>
  local exp="$1" s="$2"; shift 2
  if ls -d runs/Intersection__${exp}__${s}__* >/dev/null 2>&1; then
    log "skip train $exp s$s (이미 있음)"; return 0
  fi
  log "train $exp s$s 시작"
  $PY bench/ppo.py "$@" --total-timesteps 2000000000 --time-budget-s 3600 \
    --checkpoint-every-s 300 --seed "$s" --exp-name "$exp" \
    > $OUT/train_${exp}_s$s.log 2>&1
  log "train $exp s$s 끝 (rc=$?)"
}

evaluate() {  # evaluate <exp> <seed> <tag>
  local exp="$1" s="$2" tag="$3"
  local d; d=$(ls -d runs/Intersection__${exp}__${s}__* 2>/dev/null | head -1)
  [ -n "$d" ] || { log "eval $exp s$s: 런 없음"; return 1; }
  # (a) 전 체크포인트 × b500000 — bench_results/clean · native_desktop 과 같은 형식
  local f="$OUT/eval_md__${tag}_s$s.json"
  if [ ! -f "$f" ]; then
    $PY bench/evaluate.py --run-dir "$d" --target metadrive --episodes 30 \
      --seed 500000 --out "$f" >> $OUT/eval.log 2>&1 && log "eval $tag s$s b500000 완료"
  fi
  # (b) final.pt × 나머지 7블록 — §7 표 6 과 같은 형식(분산 성분 분석에 필요)
  for b in $BLOCKS; do
    local g="bench_results/scenario_blocks/eval_md__${tag}_s${s}__b${b}.json"
    [ -f "$g" ] && continue
    $PY bench/evaluate.py --ckpt "$d/ckpt/final.pt" --target metadrive --episodes 30 \
      --seed "$b" --out "$g" >> $OUT/eval.log 2>&1
  done
  log "eval $tag s$s 블록 완료"
}

pair() {    # pair <light_seed> <native_seed>
  train clean_custom "$1" --sim custom --num-envs 1024 --num-steps 64 --n-vehicles 3
  evaluate clean_custom "$1" clean
  train nd_md "$2" --sim metadrive --num-envs 12 --num-steps 256
  evaluate nd_md "$2" nd
  log "=== 쌍 완료: 경량 s$1 / 네이티브 s$2 ==="
}

log "SEEDS6TO10 시작 (장비 $(hostname))"
pair 6 7
pair 7 8
pair 8 9
pair 9 10
pair 10 11
log "SEEDS6TO10_DONE"
