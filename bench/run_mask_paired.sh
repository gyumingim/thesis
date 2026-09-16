#!/bin/bash
# §5.2 검증 (b) 의 **기제 분해** — 마스킹이 무엇을 고치는지 시나리오 단위로 짝지어 본다.
#
# 논문은 마스킹 구제(5%→55%)를 보고하면서 기제를 두 층위로 가설만 세워 뒀다:
#   (i)  분포외 z-score 주입에 의한 정책 폭주 — 마스킹으로 제거 가능
#   (ii) 정보 자체의 미학습 — 마스킹된 정책은 셋째 차를 «없는 셈» 치므로 그 차가
#        실제로 위협일 때 실패한다
# 그리고 "본 자료로는 (ii)가 검증되지 않는다" 고 적었다.
#
# 그런데 보관된 원자료의 **실패 구성**이 이미 갈린다(이탈 58.3%→15.0%, 충돌 36.7%→30.0%).
# 확인하려면 시나리오 단위 짝이 필요한데 구판 JSON 에는 per_episode 가 없다(그 뒤에 추가됨).
# 재학습은 필요 없다 — 같은 final.pt 를 같은 30 시나리오(seed 500000)에서 다시 평가한다.
#
# 원자료를 덮지 않는다: 새 디렉터리에 쓰고, 총계가 구판과 일치하는지부터 확인한다.
# 정숙 조건 — UE·CARLA 와 동시에 돌리지 않는다.
source "$(dirname "${BASH_SOURCE[0]}")/env.sh"

OUT=bench_results/mask_paired
mkdir -p "$OUT"
for d in runs/Intersection__sup2_custom__*; do
  [ -d "$d" ] || continue
  s=$(basename "$d" | grep -oE '__[0-9]+__' | tr -d '_')
  for mode in plain mask; do
    f="$OUT/eval_md__sup2${mode}_s$s.json"
    [ -f "$f" ] && { echo "skip $mode s$s"; continue; }
    EXTRA=""
    [ "$mode" = mask ] && EXTRA="--mask-degenerate"
    $PY bench/evaluate.py --ckpt "$d/ckpt/final.pt" --target metadrive --episodes 30 \
      --seed 500000 $EXTRA --out "$f" >> "$OUT/eval.log" 2>&1 \
      && echo "OK $mode s$s" || echo "FAIL $mode s$s"
  done
done
echo "MASKPAIRED_DONE $(date +%H:%M:%S)"
