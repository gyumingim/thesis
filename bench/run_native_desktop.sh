#!/bin/bash
# 데스크톱 MetaDrive 네이티브 다시드 기준선 (2026-08-29).
#
# 왜. 확정 헤드라인(경량 전이 48.9%)은 데스크톱(RTX 5080) 정숙 조건에서 얻었는데,
# 비교 대상인 네이티브 68%±9% 는 노트북(RTX 4060) 5시드다. 즉 논문의 주 판정이
# **장비 교차 비교**에 걸려 있다. 데스크톱 단일 시드는 53.3% 로 이미 격차가 크게
# 좁아졌으므로(§7), 같은 장비에서 다시드 기준선을 확보해야 판정이 확정된다.
#
# 프로토콜은 run_all.sh / run_desktop_viz.sh 와 동일 — 1시간 벽시계, 300s 체크포인트,
# 12프로세스. 이미 있는 dt_md 시드 1 과 합쳐 4시드가 된다.
# ★ 반드시 정숙 조건에서 — CARLA·UE 등 다른 부하가 돌면 벽시계 예산 실험이 오염된다.
set -u
cd "$(dirname "$0")/.."
PY=/c/Users/a3162/thesis/.venv/Scripts/python.exe
OUT=bench_results/native_desktop; mkdir -p $OUT
export PYTHONUTF8=1 NUMBA_NUM_THREADS=8
unset PYTHONPATH
for s in 2 3 4; do
  echo "=== nd_md s$s 시작 $(date +%H:%M) ===" >> $OUT/console.log
  $PY bench/ppo.py --sim metadrive --num-envs 12 --num-steps 256 \
    --total-timesteps 2000000000 --time-budget-s 3600 --checkpoint-every-s 300 \
    --seed $s --exp-name nd_md > $OUT/train_s$s.log 2>&1
done
for d in runs/Intersection__nd_md__*; do
  [ -d "$d" ] || continue
  s=$(basename "$d" | grep -oE '__[0-9]+__' | tr -d '_')
  echo "=== eval s$s $(date +%H:%M) ===" >> $OUT/console.log
  $PY bench/evaluate.py --run-dir "$d" --target metadrive --episodes 30 --seed 500000 \
    --out $OUT/eval_md__nd_s$s.json >> $OUT/eval.log 2>&1
done
touch $OUT/DONE
echo "NATIVE_DESKTOP_DONE $(date +%H:%M)" >> $OUT/console.log
