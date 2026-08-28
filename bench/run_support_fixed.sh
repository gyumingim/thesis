#!/bin/bash
# §5 지지집합 실험 재측정 (부호 정정판, 2026-08-28).
# V=2 로 학습하면 주변차 슬롯 3~8 이 항상 0 → 지지집합 결손. 타깃(V=3)에서 그 슬롯이
# 채워지면 미학습 입력이 들어온다. 마스킹 구제(--mask-degenerate)의 효과를 함께 잰다.
# CARLA 진화 루프와 CPU 를 나눠 쓰도록 스레드 수를 낮춘다.
set -u
cd "$(dirname "$0")/.."
PY=/c/Users/a3162/thesis/.venv/Scripts/python.exe
OUT=bench_results/support_fixed
mkdir -p $OUT
export PYTHONUTF8=1 NUMBA_NUM_THREADS=6

for s in 1 2; do
  if ls runs/Intersection__sup2_custom__${s}__*/ckpt/final.pt > /dev/null 2>&1; then
    echo "skip train s$s" >> $OUT/console.log
  else
    echo "=== sup2 s$s 학습 시작 $(date +%H:%M) ===" >> $OUT/console.log
    $PY bench/ppo.py --sim custom --num-envs 1024 --num-steps 64 --n-vehicles 2 \
      --total-timesteps 2000000000 --time-budget-s 3600 --checkpoint-every-s 600 \
      --seed $s --exp-name sup2_custom > $OUT/train_s$s.log 2>&1
  fi
done

for d in runs/Intersection__sup2_custom__*; do
  [ -d "$d" ] || continue
  s=$(basename "$d" | grep -oE '__[0-9]+__' | tr -d '_')
  # (a) 전이 (마스킹 없음)
  $PY bench/evaluate.py --ckpt "$d/ckpt/final.pt" --target metadrive --episodes 30 \
    --seed 500000 --out $OUT/eval_md__sup2_s$s.json >> $OUT/eval.log 2>&1
  # (b) 마스킹 구제
  $PY bench/evaluate.py --ckpt "$d/ckpt/final.pt" --target metadrive --episodes 30 \
    --seed 500000 --mask-degenerate --out $OUT/eval_md__sup2mask_s$s.json >> $OUT/eval.log 2>&1
  # (c) in-domain (V=2 자체)
  $PY bench/evaluate.py --ckpt "$d/ckpt/final.pt" --target custom --episodes 64 \
    --seed 500000 --n-vehicles 2 --out $OUT/eval_cu__sup2_s$s.json >> $OUT/eval.log 2>&1
done
touch $OUT/DONE
echo "SUPPORT_FIXED_DONE $(date +%H:%M)" >> $OUT/console.log
