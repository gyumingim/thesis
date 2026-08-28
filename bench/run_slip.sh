#!/bin/bash
# 타이어 마찰 한계(MU_LAT)를 켠 학습 — CARLA 회전 실패의 근본 처방 실험 (2026-08-28).
# 가설: 학습 시뮬에 횡가속 한계가 있으면 정책이 좁은 회전에서 감속을 배우고,
#       CARLA 에서 속도 거버너 없이도 주행할 수 있다.
set -u
cd "$(dirname "$0")/.."
PY=/c/Users/a3162/thesis/.venv/Scripts/python.exe
OUT=bench_results/slip
mkdir -p $OUT
export PYTHONUTF8=1 NUMBA_NUM_THREADS=6 MU_LAT=0.8

for s in 1; do
  echo "=== slip s$s 학습 시작 $(date +%H:%M) ===" >> $OUT/console.log
  $PY bench/ppo.py --sim custom --num-envs 1024 --num-steps 64 --n-vehicles 3 \
    --total-timesteps 2000000000 --time-budget-s 3600 --checkpoint-every-s 600 \
    --seed $s --exp-name slip_custom > $OUT/train_s$s.log 2>&1
done

for d in runs/Intersection__slip_custom__*; do
  [ -d "$d" ] || continue
  s=$(basename "$d" | grep -oE '__[0-9]+__' | tr -d '_')
  # in-domain (마찰 한계 환경) / MetaDrive 전이 (마찰 한계 없음 = 원 환경)
  $PY bench/evaluate.py --ckpt "$d/ckpt/final.pt" --target custom --episodes 64 \
    --seed 500000 --n-vehicles 3 --out $OUT/eval_cu__slip_s$s.json >> $OUT/eval.log 2>&1
  MU_LAT=0 $PY bench/evaluate.py --ckpt "$d/ckpt/final.pt" --target metadrive --episodes 30 \
    --seed 500000 --out $OUT/eval_md__slip_s$s.json >> $OUT/eval.log 2>&1
done
touch $OUT/DONE
echo "SLIP_DONE $(date +%H:%M)" >> $OUT/console.log
