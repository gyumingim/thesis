#!/bin/bash
# 본판 최종: V=3 custom 3시드 + 마스킹 검증 + 평가. 배치3 종료를 스스로 대기 후 시작.
set -u
cd /home/karma/thesis
until [ -f bench_results/main/DONE ]; do sleep 60; done
sleep 30
for seed in 1 2 3; do
  echo "=== final custom(V=3) seed=$seed $(date +%H:%M) ==="
  env -u PYTHONPATH NUMBA_NUM_THREADS=8 .venv/bin/python bench/ppo.py \
    --sim custom --num-envs 1024 --num-steps 64 --n-vehicles 3 \
    --total-timesteps 2000000000 --time-budget-s 3600 --checkpoint-every-s 300 \
    --seed $seed --exp-name final_custom > bench_results/main/finalc_s$seed.log 2>&1
done
echo "=== V=2 런 마스킹 구제 재평가 $(date +%H:%M) ==="
for d in runs/Intersection__main_custom__*; do
  n=$(basename $d | grep -oE '__[0-9]+__' | tr -d '_')
  env -u PYTHONPATH NUMBA_NUM_THREADS=8 .venv/bin/python bench/evaluate.py \
    --run-dir $d --target metadrive --episodes 30 --seed 500000 --mask-degenerate \
    --out bench_results/main/evalmask_md__custom_s$n.json >> bench_results/main/eval4.log 2>&1
done
echo "=== V=3 신규 런 평가 $(date +%H:%M) ==="
for d in runs/Intersection__final_custom__*; do
  n=$(basename $d | grep -oE '__[0-9]+__' | tr -d '_')
  env -u PYTHONPATH NUMBA_NUM_THREADS=8 .venv/bin/python bench/evaluate.py \
    --run-dir $d --target metadrive --episodes 30 --seed 500000 \
    --out bench_results/main/eval_md__final_custom_s$n.json >> bench_results/main/eval4.log 2>&1
  env -u PYTHONPATH NUMBA_NUM_THREADS=8 .venv/bin/python bench/evaluate.py \
    --ckpt $d/ckpt/final.pt --target custom --episodes 64 --seed 500000 \
    --out bench_results/main/eval_cu__final_custom_s$n.json >> bench_results/main/eval4.log 2>&1
done
date > bench_results/main/DONE4
echo "=== FINAL BATCH DONE $(date +%H:%M) ==="
