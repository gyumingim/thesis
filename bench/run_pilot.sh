#!/bin/bash
# 파일럿: 30분 x 2시드 x 2시뮬, 반드시 순차 (동시 실행은 CPU 경합으로 비교 오염)
# custom 은 처리량 최적 구성(1024env), metadrive 는 병렬 정점(12env).
# PPO 업데이트 하이퍼파라미터(lr/epochs/clip/GAE)는 양쪽 동일 (CleanRL 기본값).
# time budget 하에서는 lr annealing 이 사실상 무효(둘 다 동일 조건).
set -u
cd /home/karma/thesis
BUDGET=1800
CKPT=300

for seed in 1 2; do
  echo "=== pilot custom seed=$seed $(date +%H:%M:%S) ==="
  env -u PYTHONPATH NUMBA_NUM_THREADS=8 .venv/bin/python bench/ppo.py \
    --sim custom --num-envs 1024 --num-steps 64 \
    --total-timesteps 2000000000 --time-budget-s $BUDGET --checkpoint-every-s $CKPT \
    --seed $seed --exp-name pilot_custom \
    > bench_results/pilot_custom_s$seed.log 2>&1
  echo "exit=$?"
done

for seed in 1 2; do
  echo "=== pilot metadrive seed=$seed $(date +%H:%M:%S) ==="
  env -u PYTHONPATH .venv/bin/python bench/ppo.py \
    --sim metadrive --num-envs 12 --num-steps 256 \
    --total-timesteps 2000000000 --time-budget-s $BUDGET --checkpoint-every-s $CKPT \
    --seed $seed --exp-name pilot_md \
    > bench_results/pilot_md_s$seed.log 2>&1
  echo "exit=$?"
done
echo "=== pilot 전체 완료 $(date +%H:%M:%S) ==="
