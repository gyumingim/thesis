#!/bin/bash
# 야간 연장: DONE4 후 예산확장 실험 — custom V=3 를 3시간 학습 (벽시계 곡선 연장점)
set -u
cd /home/karma/thesis
until [ -f bench_results/main/DONE4 ]; do sleep 120; done
sleep 30
echo "=== extended custom(V=3) 3h seed=7 $(date +%H:%M) ==="
env -u PYTHONPATH NUMBA_NUM_THREADS=8 .venv/bin/python bench/ppo.py \
  --sim custom --num-envs 1024 --num-steps 64 --n-vehicles 3 \
  --total-timesteps 2000000000 --time-budget-s 10800 --checkpoint-every-s 600 \
  --seed 7 --exp-name ext3h_custom > bench_results/main/ext3h.log 2>&1
for d in runs/Intersection__ext3h_custom__*; do
  env -u PYTHONPATH NUMBA_NUM_THREADS=8 .venv/bin/python bench/evaluate.py \
    --run-dir $d --target metadrive --episodes 30 --seed 500000 \
    --out bench_results/main/eval_md__ext3h.json >> bench_results/main/eval5.log 2>&1
done
date > bench_results/main/DONE5
