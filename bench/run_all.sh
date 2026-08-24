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
#   학습의 완주 판정은 ckpt/final.pt 존재다 — 디렉터리 존재만 보면 중도 사망한 반쪽 런이
#   영구히 skip 되는 함정이 있다 (V=2 s2 가 11분에 죽었던 전례, PAPER 각주2).
#
# 실행: bash bench/run_all.sh   (sh 로 띄우면 BASH_SOURCE + set -u 로 즉사)
set -u
source "$(dirname "${BASH_SOURCE[0]}")/env.sh"

B=3600          # 본판 벽시계 예산(초)
CK=300          # 체크포인트 주기(초)
EXT=10800       # 예산확장 실험(초)
EVAL_SEED=500000  # 학습 시나리오 범위(1..14000)와 비겹침
OUT=bench_results/main
mkdir -p "$OUT"

# ── 절전 방지: 14시간 무인 실행 중 윈도우가 잠들면 time.time() 예산이 오염된다.
#    SetThreadExecutionState 를 주기 호출하는 파수꾼을 배치 수명 동안만 띄운다.
powershell -NoProfile -ExecutionPolicy Bypass -File bench/keepawake.ps1 &
KEEPAWAKE_PID=$!
trap 'kill $KEEPAWAKE_PID 2>/dev/null' EXIT

step() { echo "=== $* | $(date '+%m-%d %H:%M:%S') ==="; }
# 완주한 런의 디렉터리를 출력 (없으면 빈 문자열)
done_run() { ls -d runs/Intersection__$1__$2__*/ckpt/final.pt 2>/dev/null | head -1 | xargs -r dirname | xargs -r dirname; }

# 학습 1건. $1=exp_name $2=seed $3=예산 $4=체크포인트주기 $5.. = 추가 인자
# timeout = 예산 x2: 워커 스톨(전례 2.8h)로 예산 체크가 발화하지 못해도 배치가 멈추지 않는다.
train_custom() {
  local exp=$1 seed=$2 budget=$3 ck=$4; shift 4
  [ -n "$(done_run "$exp" "$seed")" ] && { echo "skip(train) $exp s$seed"; return; }
  step "train $exp seed=$seed"
  timeout -k 60 $((budget * 2)) \
    env -u PYTHONPATH PYTHONUTF8=1 NUMBA_NUM_THREADS=8 "$PY" \
    bench/ppo.py --sim custom --num-envs 1024 --num-steps 64 \
    --total-timesteps 2000000000 --time-budget-s "$budget" --checkpoint-every-s "$ck" \
    --seed "$seed" --exp-name "$exp" "$@" > "$OUT/${exp}_s${seed}.log" 2>&1 \
    || echo "!! train $exp s$seed 비정상 종료 (exit=$?)"
}

train_md() {
  local seed=$1
  [ -n "$(done_run main_md "$seed")" ] && { echo "skip(train) main_md s$seed"; return; }
  step "train main_md seed=$seed"
  timeout -k 60 $((B * 2)) \
    env -u PYTHONPATH PYTHONUTF8=1 "$PY" \
    bench/ppo.py --sim metadrive --num-envs 12 --num-steps 256 \
    --total-timesteps 2000000000 --time-budget-s "$B" --checkpoint-every-s "$CK" \
    --seed "$seed" --exp-name main_md > "$OUT/md_s${seed}.log" 2>&1 \
    || echo "!! train main_md s$seed 비정상 종료 (exit=$?)"
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

# (d) 예산확장: 경량 V=3 를 3시간 (벽시계 곡선 연장점 — fig_budget_ext 가 소비)
train_custom ext3h_custom 7 $EXT 600 --n-vehicles 3

# ── 2) 평가 ──────────────────────────────────────────────────────────────────
# 파일명은 plot_curves.py 의 glob 과 맞춰야 한다:
#   eval_md__main_md__*      eval_md__final_custom_s*      eval_md__main_custom__*
#   evalmask_md__custom_s*   eval_md__ext3h
# 곡선 그림이 읽는 조건(main_md, final_custom, ext3h)만 --run-dir(전 ckpt)로 돌고,
# 막대 그림이 final 만 읽는 조건(main_custom, 마스킹)은 --ckpt final.pt 로 돈다
# — 안 읽히는 66건의 MetaDrive 평가(수 시간)를 없앤다.
name_of()  { basename "$1" | sed 's/Intersection__//; s/__[0-9]*$//'; }   # 예: main_md__1
stamp_of() { basename "$1" | grep -oE '[0-9]+$' | tail -c 5; }            # 타임스탬프 끝 4자리
seed_of()  { basename "$1" | grep -oE '__[0-9]+__' | tr -d '_'; }

EVT=5400   # 평가 1건 상한(초) — 30ep x 1000스텝이 이걸 넘으면 걸린 것

run_eval() {  # $1=출력 json, $2.. = evaluate.py 인자
  local out=$1; shift
  [ -f "$out" ] && return
  step "eval → $(basename "$out")"
  timeout -k 60 $EVT \
    env -u PYTHONPATH PYTHONUTF8=1 NUMBA_NUM_THREADS=8 "$PY" \
    bench/evaluate.py "$@" --out "$out" >> "$OUT/eval.log" 2>&1 \
    || echo "!! eval $(basename "$out") 비정상 종료 (exit=$?)"
}

# (곡선) MD 네이티브: →MetaDrive 전 ckpt + →custom(V=3, 역방향) final
for d in runs/Intersection__main_md__*; do
  [ -d "$d" ] || continue
  lbl="$(name_of "$d")_$(stamp_of "$d")"
  run_eval "$OUT/eval_md__$lbl.json" --run-dir "$d" --target metadrive --episodes 30 --seed $EVAL_SEED
  run_eval "$OUT/eval_cu__$lbl.json" --ckpt "$d/ckpt/final.pt" --target custom --episodes 64 --seed $EVAL_SEED --n-vehicles 3
done

# (곡선) V=3 본판: →MetaDrive 전 ckpt + →custom(V=3, in-domain) final
for d in runs/Intersection__final_custom__*; do
  [ -d "$d" ] || continue
  lbl="final_custom_s$(seed_of "$d")"
  run_eval "$OUT/eval_md__$lbl.json" --run-dir "$d" --target metadrive --episodes 30 --seed $EVAL_SEED
  run_eval "$OUT/eval_cu__$lbl.json" --ckpt "$d/ckpt/final.pt" --target custom --episodes 64 --seed $EVAL_SEED --n-vehicles 3
done

# (막대) V=2 병리: →MetaDrive final + 마스킹 구제 + §5(a) 소거 실험 두 열
#   in-domain(V=2 평가)과 지지집합 위반(V=3 평가) — evaluate.py 의 --n-vehicles 로 구분.
#   V 표기를 파일명에 넣는다 (없으면 두 열이 구분 불가).
for d in runs/Intersection__main_custom__*; do
  [ -d "$d" ] || continue
  lbl="$(name_of "$d")_$(stamp_of "$d")"; sd="$(seed_of "$d")"
  run_eval "$OUT/eval_md__$lbl.json"        --ckpt "$d/ckpt/final.pt" --target metadrive --episodes 30 --seed $EVAL_SEED
  run_eval "$OUT/evalmask_md__custom_s$sd.json" --ckpt "$d/ckpt/final.pt" --target metadrive --episodes 30 --seed $EVAL_SEED --mask-degenerate
  run_eval "$OUT/eval_cuV2__custom_s$sd.json" --ckpt "$d/ckpt/final.pt" --target custom --episodes 64 --seed $EVAL_SEED --n-vehicles 2
  run_eval "$OUT/eval_cuV3__custom_s$sd.json" --ckpt "$d/ckpt/final.pt" --target custom --episodes 64 --seed $EVAL_SEED --n-vehicles 3
done

# (확장 곡선) 3h 런: →MetaDrive 전 ckpt
for d in runs/Intersection__ext3h_custom__*; do
  [ -d "$d" ] || continue
  run_eval "$OUT/eval_md__ext3h.json" --run-dir "$d" --target metadrive --episodes 30 --seed $EVAL_SEED
done

# ── 3) 그림 ──────────────────────────────────────────────────────────────────
# plot 로그는 분리한다 — eval.log 에 섞이면 트레이스백이 수천 줄에 묻힌다.
# DONE_ALL 은 plot 이 성공했을 때만 찍는다. 실패해도 찍히면 "성공처럼 보이는 실패"가 된다.
step "plot_curves"
PYRUN bench/plot_curves.py > "$OUT/plot.log" 2>&1 \
  && date > "$OUT/DONE_ALL" \
  || echo "!! plot_curves 실패 — $OUT/plot.log 확인. DONE_ALL 미기록."

step "BATCH END"
