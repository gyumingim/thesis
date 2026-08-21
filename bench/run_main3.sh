#!/bin/bash
# 본판 3차: MD 3시드 + 전체 평가 (custom 3런은 완료분 사용)
set -u
cd /home/karma/thesis
for seed in 1 2 3; do
  echo "=== main metadrive seed=$seed $(date +%H:%M) ==="
  env -u PYTHONPATH .venv/bin/python bench/ppo.py \
    --sim metadrive --num-envs 12 --num-steps 256 \
    --total-timesteps 2000000000 --time-budget-s 3600 --checkpoint-every-s 300 \
    --seed $seed --exp-name main_md > bench_results/main/md_s$seed.log 2>&1
done
echo "=== 교차평가 $(date +%H:%M) ==="
for d in runs/Intersection__main_*; do
  name=$(basename $d | sed 's/Intersection__//;s/__[0-9]*$//')_$(basename $d | grep -oE '[0-9]+$' | tail -c 5)
  env -u PYTHONPATH NUMBA_NUM_THREADS=8 .venv/bin/python bench/evaluate.py \
    --run-dir $d --target metadrive --episodes 30 --seed 500000 \
    --out bench_results/main/eval_md__$name.json >> bench_results/main/eval.log 2>&1
  env -u PYTHONPATH NUMBA_NUM_THREADS=8 .venv/bin/python bench/evaluate.py \
    --ckpt $d/ckpt/final.pt --target custom --episodes 64 --seed 500000 \
    --out bench_results/main/eval_cu__$name.json >> bench_results/main/eval.log 2>&1
done
date > bench_results/main/DONE
echo "=== DONE $(date +%H:%M) ==="
