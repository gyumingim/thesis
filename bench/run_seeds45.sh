#!/bin/bash
# 본판 시드 보강 (4,5) — run_all.sh 와 동일 커맨드·코드(노트북 main HEAD), 2026-08-26.
# 목적: 주 결과(§6.2 main_md 66%±10%, final_custom V=3 전이)의 오차막대를 3->5시드로 강화.
set -u
cd "$(dirname "$0")/.."
source bench/env.sh
OUT=bench_results/main
B=3600; CK=300; EVAL_SEED=500000; EVT=5400
step() { echo "=== $* | $(date '+%m-%d %H:%M:%S') ==="; }
done_run() { ls -d runs/Intersection__$1__$2__*/ckpt/final.pt 2>/dev/null | head -1 | xargs -r dirname | xargs -r dirname; }
train_custom() {
  local exp=$1 seed=$2; shift 2
  [ -n "$(done_run "$exp" "$seed")" ] && { echo "skip $exp s$seed"; return; }
  step "train $exp seed=$seed"
  timeout -k 60 $((B * 2)) env -u PYTHONPATH PYTHONUTF8=1 NUMBA_NUM_THREADS=8 "$PY" \
    bench/ppo.py --sim custom --num-envs 1024 --num-steps 64 \
    --total-timesteps 2000000000 --time-budget-s $B --checkpoint-every-s $CK \
    --seed "$seed" --exp-name "$exp" "$@" > "$OUT/${exp}_s${seed}.log" 2>&1 || echo "!! $exp s$seed exit=$?"
}
train_md() {
  local seed=$1
  [ -n "$(done_run main_md "$seed")" ] && { echo "skip md s$seed"; return; }
  step "train main_md seed=$seed"
  timeout -k 60 $((B * 2)) env -u PYTHONPATH PYTHONUTF8=1 "$PY" \
    bench/ppo.py --sim metadrive --num-envs 12 --num-steps 256 \
    --total-timesteps 2000000000 --time-budget-s $B --checkpoint-every-s $CK \
    --seed "$seed" --exp-name main_md > "$OUT/md_s${seed}.log" 2>&1 || echo "!! md s$seed exit=$?"
}
for s in 4 5; do train_md $s; done
for s in 4 5; do train_custom final_custom $s --n-vehicles 3; done
name_of()  { basename "$1" | sed 's/Intersection__//; s/__[0-9]*$//'; }
stamp_of() { basename "$1" | grep -oE '[0-9]+$' | tail -c 5; }
seed_of()  { basename "$1" | grep -oE '__[0-9]+__' | tr -d '_'; }
run_eval() {
  local out=$1; shift
  [ -f "$out" ] && return
  step "eval $(basename "$out")"
  timeout -k 60 $EVT env -u PYTHONPATH PYTHONUTF8=1 NUMBA_NUM_THREADS=8 "$PY" \
    bench/evaluate.py "$@" --out "$out" >> "$OUT/eval45.log" 2>&1 || echo "!! eval exit=$?"
}
for s in 4 5; do
  for d in runs/Intersection__main_md__${s}__*; do
    [ -d "$d" ] || continue
    lbl="$(name_of "$d")_$(stamp_of "$d")"
    run_eval "$OUT/eval_md__$lbl.json" --run-dir "$d" --target metadrive --episodes 30 --seed $EVAL_SEED
    run_eval "$OUT/eval_cu__$lbl.json" --ckpt "$d/ckpt/final.pt" --target custom --episodes 64 --seed $EVAL_SEED --n-vehicles 3
  done
  for d in runs/Intersection__final_custom__${s}__*; do
    [ -d "$d" ] || continue
    lbl="final_custom_s$(seed_of "$d")"
    run_eval "$OUT/eval_md__$lbl.json" --run-dir "$d" --target metadrive --episodes 30 --seed $EVAL_SEED
    run_eval "$OUT/eval_cu__$lbl.json" --ckpt "$d/ckpt/final.pt" --target custom --episodes 64 --seed $EVAL_SEED --n-vehicles 3
  done
done
touch $OUT/DONE45
echo "SEEDS45_DONE $(date '+%m-%d %H:%M')"
