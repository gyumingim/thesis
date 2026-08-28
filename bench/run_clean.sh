#!/bin/bash
# 부호 정정판 본판 재현 (2026-08-28). 경량 V=3 3시드 — MetaDrive 네이티브는 영향 없음(재사용).
set -u
cd "$(dirname "$0")/.."
PY=/c/Users/a3162/thesis/.venv/Scripts/python.exe
OUT=bench_results/clean; mkdir -p $OUT
export PYTHONUTF8=1 NUMBA_NUM_THREADS=8
for s in 1 2 3; do
  echo "=== fix_custom s$s $(date +%H:%M) ===" >> $OUT/console.log
  $PY bench/ppo.py --sim custom --num-envs 1024 --num-steps 64 --n-vehicles 3 \
    --total-timesteps 2000000000 --time-budget-s 3600 --checkpoint-every-s 300 \
    --seed $s --exp-name clean_custom > $OUT/train_s$s.log 2>&1
done
for d in runs/Intersection__clean_custom__*; do
  [ -d "$d" ] || continue
  s=$(basename "$d" | grep -oE '__[0-9]+__' | tr -d '_')
  $PY bench/evaluate.py --run-dir "$d" --target metadrive --episodes 30 --seed 500000 \
    --out $OUT/eval_md__clean_s$s.json >> $OUT/eval.log 2>&1
  $PY bench/evaluate.py --ckpt "$d/ckpt/final.pt" --target custom --episodes 64 --seed 500000 \
    --n-vehicles 3 --out $OUT/eval_cu__clean_s$s.json >> $OUT/eval.log 2>&1
done
touch $OUT/DONE
echo "FIXED_RERUN_DONE $(date +%H:%M)" >> $OUT/console.log
