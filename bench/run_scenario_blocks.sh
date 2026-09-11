#!/bin/bash
# 평가 **시나리오 축**을 복원한다 — PAPER §7 한계 / §8 향후 연구 (7).
#
# 논문의 모든 MetaDrive 전이 수치는 시나리오 500000~500029 라는 **단일 30장면 표본**에
# 조건부다. 두 팔, 12개 체크포인트, 10개 학습 시드가 전부 같은 30장면을 본다. 따라서
# 보고된 오차막대는 **학습 시드 축의 변동**이고, 시나리오 축의 변동은 한 번도 측정된 적이
# 없다. §7 에 한계로 적어 두었으나 측정은 미뤄져 있었다.
#
# 재학습은 필요 없다 — 한계는 **평가** 표본에 관한 것이므로 기존 final.pt 를 서로 다른
# 시나리오 블록에서 다시 평가하면 된다. 체크포인트가 로컬에 남아 있어 가능하다.
#
# 블록: 500000(논문 원본) · 510000 · 520000 · 530000. 각 30에피소드, 결정론.
# 정숙 조건 — UE·CARLA 와 동시에 돌리지 않는다(§6.2 의 경합 오염 사례).
source "$(dirname "${BASH_SOURCE[0]}")/env.sh"

OUT=bench_results/scenario_blocks
mkdir -p "$OUT"
BLOCKS="${BLOCKS:-500000 510000 520000 530000}"

run_one() {
  local tag="$1" dir="$2" blk="$3"
  local f="$OUT/eval_md__${tag}__b${blk}.json"
  [ -f "$f" ] && { echo "skip $tag b$blk"; return; }
  $PY bench/evaluate.py --ckpt "$dir/ckpt/final.pt" --target metadrive \
      --episodes 30 --seed "$blk" --out "$f" >> "$OUT/run.log" 2>&1 \
    && echo "OK  $tag b$blk" || echo "FAIL $tag b$blk"
}

for blk in $BLOCKS; do
  for s in 1 2 3 4 5; do
    d=$(ls -d runs/Intersection__clean_custom__${s}__* 2>/dev/null | head -1)
    [ -n "$d" ] && run_one "clean_s$s" "$d" "$blk"
  done
  for s in 2 3 4 5 6; do
    d=$(ls -d runs/Intersection__nd_md__${s}__* 2>/dev/null | head -1)
    [ -n "$d" ] && run_one "nd_s$s" "$d" "$blk"
  done
done
echo "SCENBLOCKS_DONE $(date +%H:%M:%S)"
