#!/bin/bash
# 본판: 1시간 x 3시드 x 2시뮬 (순차) → 전 체크포인트 교차평가 → Figure
# 환경 = R6 동결 (실측 차선). MetaDrive 학습은 워커당 100 시나리오 (파일럿 반영).
# 평가 시드 500000 (학습 시나리오 범위 1..14000 과 비겹침).
set -u
cd /home/karma/thesis
B=3600; CK=300
mkdir -p bench_results/main

for seed in 1 2 3; do
  echo "=== main custom seed=$seed $(date +%H:%M) ==="
  env -u PYTHONPATH NUMBA_NUM_THREADS=8 .venv/bin/python bench/ppo.py \
    --sim custom --num-envs 1024 --num-steps 64 \
    --total-timesteps 2000000000 --time-budget-s $B --checkpoint-every-s $CK \
    --seed $seed --exp-name main_custom > bench_results/main/custom_s$seed.log 2>&1
done
for seed in 1 2 3; do
  echo "=== main metadrive seed=$seed $(date +%H:%M) ==="
  env -u PYTHONPATH .venv/bin/python bench/ppo.py \
    --sim metadrive --num-envs 12 --num-steps 256 \
    --total-timesteps 2000000000 --time-budget-s $B --checkpoint-every-s $CK \
    --seed $seed --exp-name main_md > bench_results/main/md_s$seed.log 2>&1
done

echo "=== 교차평가 $(date +%H:%M) ==="
for d in runs/*main_custom* runs/*main_md*; do
  name=$(basename $d | sed 's/Intersection__//;s/__[0-9]*$//')
  env -u PYTHONPATH NUMBA_NUM_THREADS=8 .venv/bin/python bench/evaluate.py \
    --run-dir $d --target metadrive --episodes 30 --seed 500000 \
    --out bench_results/main/eval_md__$name.json >> bench_results/main/eval.log 2>&1
  env -u PYTHONPATH NUMBA_NUM_THREADS=8 .venv/bin/python bench/evaluate.py \
    --ckpt $d/ckpt/final.pt --target custom --episodes 64 --seed 500000 \
    --out bench_results/main/eval_cu__$name.json >> bench_results/main/eval.log 2>&1
done
env -u PYTHONPATH .venv/bin/python bench/plot_curves.py >> bench_results/main/eval.log 2>&1
date +%H:%M > bench_results/main/DONE
echo "=== MAIN BATCH DONE $(date +%H:%M) ==="
