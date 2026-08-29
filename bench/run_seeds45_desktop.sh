#!/bin/bash
# 시드 보강 (2026-08-29) — 헤드라인 판정을 n=3 에서 n=5 로.
#
# 왜. 동일 장비 대조에서 격차 14.5%p 의 Welch p 가 0.385 이고 차이의 95% 구간이
# [-56.6, +27.6]%p 다. n=3 으로는 이 질문에 답할 수 없다는 것이 현재의 정직한 결론이며,
# 시드 보강이 §8 최우선 과제다. 경량·네이티브 각 2시드를 같은 정숙 조건에서 추가한다.
#
# 순서: 경량 s4 → 경량 s5 → 네이티브 s5 → 네이티브 s6 (각 1시간) → 전부 평가.
# ★ 정숙 조건 필수 — CARLA·UE 가 돌면 벽시계 예산 실험이 오염된다(§7, HARDWARE_CONFOUND).
set -u
cd "$(dirname "$0")/.."
PY=/c/Users/a3162/thesis/.venv/Scripts/python.exe
OUT=bench_results/seeds45; mkdir -p $OUT
export PYTHONUTF8=1 NUMBA_NUM_THREADS=8
unset PYTHONPATH

for s in 4 5; do
  echo "=== clean_custom s$s 시작 $(date +%H:%M) ===" >> $OUT/console.log
  $PY bench/ppo.py --sim custom --num-envs 1024 --num-steps 64 --n-vehicles 3 \
    --total-timesteps 2000000000 --time-budget-s 3600 --checkpoint-every-s 300 \
    --seed $s --exp-name clean_custom > $OUT/train_light_s$s.log 2>&1
done
for s in 5 6; do
  echo "=== nd_md s$s 시작 $(date +%H:%M) ===" >> $OUT/console.log
  $PY bench/ppo.py --sim metadrive --num-envs 12 --num-steps 256 \
    --total-timesteps 2000000000 --time-budget-s 3600 --checkpoint-every-s 300 \
    --seed $s --exp-name nd_md > $OUT/train_nat_s$s.log 2>&1
done

for d in runs/Intersection__clean_custom__4__* runs/Intersection__clean_custom__5__*; do
  [ -d "$d" ] || continue
  s=$(basename "$d" | grep -oE '__[0-9]+__' | tr -d '_')
  echo "=== eval light s$s $(date +%H:%M) ===" >> $OUT/console.log
  $PY bench/evaluate.py --run-dir "$d" --target metadrive --episodes 30 --seed 500000 \
    --out bench_results/clean/eval_md__clean_s$s.json >> $OUT/eval.log 2>&1
  $PY bench/evaluate.py --ckpt "$d/ckpt/final.pt" --target custom --episodes 64 --seed 500000 \
    --n-vehicles 3 --out bench_results/clean/eval_cu__clean_s$s.json >> $OUT/eval.log 2>&1
done
for d in runs/Intersection__nd_md__5__* runs/Intersection__nd_md__6__*; do
  [ -d "$d" ] || continue
  s=$(basename "$d" | grep -oE '__[0-9]+__' | tr -d '_')
  echo "=== eval native s$s $(date +%H:%M) ===" >> $OUT/console.log
  $PY bench/evaluate.py --run-dir "$d" --target metadrive --episodes 30 --seed 500000 \
    --out bench_results/native_desktop/eval_md__nd_s$s.json >> $OUT/eval.log 2>&1
done
touch $OUT/DONE
echo "SEEDS45_DONE $(date +%H:%M)" >> $OUT/console.log
