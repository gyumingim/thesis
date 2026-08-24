#!/bin/bash
# 본판 전체 재측정 — 한 장비에서 전 조건을 순차 실행한다.
#
# 왜 전부 다시 도는가: §6.2 는 "동일 wall-clock 예산" 비교다. 조건마다 장비가 다르면
# 1시간이 뜻하는 샘플 수가 달라져 표가 성립하지 않는다. 장비를 옮겼으면 전 조건 재측정이
# 유일하게 옳은 선택이다. (기존 4060 노트북 수치의 출처는 run_main*.sh 5벌 = git 이력)
#
# 왜 순차인가: 조건 간 CPU/GPU 경합이 생기면 벽시계 예산이 오염된다. 절대 병렬로 돌리지 말 것.
#             같은 이유로 이 배치가 도는 동안 언리얼 렌더 등 무거운 작업을 겹치면 안 된다.
#
# 재개 가능: 각 단계는 산출물이 이미 있으면 건너뛴다. 중단 후 다시 실행하면 이어서 돈다.
#
# 실행: bash bench/run_all.sh
set -u
source "$(dirname "${BASH_SOURCE[0]}")/env.sh"

B=3600          # 본판 벽시계 예산(초)
CK=300          # 체크포인트 주기(초)
EXT=10800       # 예산확장 실험(초)
EVAL_SEED=500000  # 학습 시나리오 범위(1..14000)와 비겹침
OUT=bench_results/main
mkdir -p "$OUT"

step() { echo "=== $* | $(date '+%m-%d %H:%M:%S') ==="; }
have_run() { [ -n "$(ls -d runs/Intersection__$1__$2__* 2>/dev/null)" ]; }

# 학습 1건. $1=exp_name $2=seed $3=예산 $4=체크포인트주기 $5.. = 추가 인자
train_custom() {
  local exp=$1 seed=$2 budget=$3 ck=$4; shift 4
  have_run "$exp" "$seed" && { echo "skip(train) $exp s$seed"; return; }
  step "train $exp seed=$seed"
  PYRUN bench/ppo.py --sim custom --num-envs 1024 --num-steps 64 \
    --total-timesteps 2000000000 --time-budget-s "$budget" --checkpoint-every-s "$ck" \
    --seed "$seed" --exp-name "$exp" "$@" > "$OUT/${exp}_s${seed}.log" 2>&1
}

train_md() {
  local seed=$1
  have_run main_md "$seed" && { echo "skip(train) main_md s$seed"; return; }
  step "train main_md seed=$seed"
  PYRUN_MD bench/ppo.py --sim metadrive --num-envs 12 --num-steps 256 \
    --total-timesteps 2000000000 --time-budget-s "$B" --checkpoint-every-s "$CK" \
    --seed "$seed" --exp-name main_md > "$OUT/md_s${seed}.log" 2>&1
}

# ── 1) 학습 ──────────────────────────────────────────────────────────────────
# 순서 = 논문 기여도 순. 중간에 멈춰도 위쪽부터 쓸 수 있게 배치했다.

# (a) 기준선: MetaDrive 네이티브 3시드
for s in 1 2 3; do train_md $s; done

# (b) 주 결과: 경량 V=3 (수정판) 3시드
for s in 1 2 3; do train_custom final_custom $s $B $CK --n-vehicles 3; done

# (c) 병리 표본: 경량 V=2 (지지집합 결함) 3시드
#     --n-vehicles 2 를 반드시 명시한다. ppo.py 의 기본값은 f8aa92c 에서 2→3 으로 바뀌었고,
#     원 run_main.sh 는 기본값에 의존했다. 생략하면 병리 조건이 조용히 V=3 이 된다.
for s in 1 2 3; do train_custom main_custom $s $B $CK --n-vehicles 2; done

# (d) 예산확장: 경량 V=3 를 3시간 (벽시계 곡선 연장점)
train_custom ext3h_custom 7 $EXT 600 --n-vehicles 3

# ── 2) 평가 ──────────────────────────────────────────────────────────────────
# 파일명은 plot_curves.py 의 glob 과 맞춰야 한다:
#   eval_md__main_md__*      eval_md__final_custom_s*      eval_md__main_custom__*
#   evalmask_md__custom_s*   eval_md__ext3h
# run_main2.sh 와 동일한 이름 규칙을 그대로 쓴다.
name_of()  { basename "$1" | sed 's/Intersection__//; s/__[0-9]*$//'; }   # 예: main_md__1
stamp_of() { basename "$1" | grep -oE '[0-9]+$' | tail -c 5; }            # 타임스탬프 끝 4자리
seed_of()  { basename "$1" | grep -oE '__[0-9]+__' | tr -d '_'; }

eval_pair() {   # $1=런디렉터리 $2=출력 라벨
  local d=$1 label=$2
  if [ ! -f "$OUT/eval_md__$label.json" ]; then
    step "eval →MetaDrive $label"
    PYRUN bench/evaluate.py --run-dir "$d" --target metadrive \
      --episodes 30 --seed $EVAL_SEED --out "$OUT/eval_md__$label.json" >> "$OUT/eval.log" 2>&1
  fi
  if [ ! -f "$OUT/eval_cu__$label.json" ]; then
    step "eval →custom $label"
    PYRUN bench/evaluate.py --ckpt "$d/ckpt/final.pt" --target custom \
      --episodes 64 --seed $EVAL_SEED --out "$OUT/eval_cu__$label.json" >> "$OUT/eval.log" 2>&1
  fi
}

for d in runs/Intersection__main_md__* runs/Intersection__main_custom__*; do
  [ -d "$d" ] || continue
  eval_pair "$d" "$(name_of "$d")_$(stamp_of "$d")"
done

for d in runs/Intersection__final_custom__*; do
  [ -d "$d" ] || continue
  eval_pair "$d" "final_custom_s$(seed_of "$d")"
done

# 퇴화차원 마스킹 구제 재평가 — V=2 런만 대상 (§5 검증 b)
for d in runs/Intersection__main_custom__*; do
  [ -d "$d" ] || continue
  f="$OUT/evalmask_md__custom_s$(seed_of "$d").json"
  [ -f "$f" ] && continue
  step "eval(mask) →MetaDrive $(basename "$d")"
  PYRUN bench/evaluate.py --run-dir "$d" --target metadrive --episodes 30 \
    --seed $EVAL_SEED --mask-degenerate --out "$f" >> "$OUT/eval.log" 2>&1
done

# 예산확장 런 평가
for d in runs/Intersection__ext3h_custom__*; do
  [ -d "$d" ] || continue
  [ -f "$OUT/eval_md__ext3h.json" ] && continue
  step "eval →MetaDrive ext3h"
  PYRUN bench/evaluate.py --run-dir "$d" --target metadrive --episodes 30 \
    --seed $EVAL_SEED --out "$OUT/eval_md__ext3h.json" >> "$OUT/eval.log" 2>&1
done

# ── 3) 그림 ──────────────────────────────────────────────────────────────────
step "plot_curves"
PYRUN bench/plot_curves.py >> "$OUT/eval.log" 2>&1

date > "$OUT/DONE_ALL"
step "ALL DONE"
