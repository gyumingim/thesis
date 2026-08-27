#!/bin/bash
# 데스크톱(RTX 5080) 재현 + 시각화용 정책 2종 (2026-08-28).
# 목적 (1) 주행 시각화용 체크포인트 확보 (2) §7 "단일 장비" 한계 부분 반박(하드웨어 일반화).
# 프로토콜은 run_all.sh 와 동일 (1시간, ckpt 300s).
set -u
cd "$(dirname "$0")/.."
PY=/c/Users/a3162/thesis/.venv/Scripts/python.exe
LOG=bench_results/desktop
mkdir -p $LOG
export PYTHONUTF8=1 NUMBA_NUM_THREADS=8
echo "=== dt_md 시작 $(date +%H:%M) ===" >> $LOG/console.log
$PY bench/ppo.py --sim metadrive --num-envs 12 --num-steps 256 \
  --total-timesteps 2000000000 --time-budget-s 3600 --checkpoint-every-s 300 \
  --seed 1 --exp-name dt_md > $LOG/dt_md.log 2>&1
echo "=== dt_custom 시작 $(date +%H:%M) ===" >> $LOG/console.log
$PY bench/ppo.py --sim custom --num-envs 1024 --num-steps 64 --n-vehicles 3 \
  --total-timesteps 2000000000 --time-budget-s 3600 --checkpoint-every-s 300 \
  --seed 1 --exp-name dt_custom > $LOG/dt_custom.log 2>&1
echo "DESKTOP_VIZ_DONE $(date +%H:%M)" >> $LOG/console.log
