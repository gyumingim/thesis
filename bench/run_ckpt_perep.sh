#!/bin/bash
# 오라클 편향 널의 **가정을 측정으로 바꾸기 위한** 재평가 — §7 (5).
#
# §7 (5) 는 「체크포인트 선택의 겉보기 이득은 대부분 평가 잡음」이라는 판정을, 시나리오
# 난이도의 급내 상관 ρ 를 **가정한 격자**(0 / 0.3 / 0.7)로 감도 분석해 방어했다. ρ 는
# 실제로는 잴 수 있는 값이다 — 12개 체크포인트가 **같은 30 시나리오**를 보므로, 장면별
# 성공/실패가 체크포인트 간에 얼마나 함께 움직이는지를 세면 된다.
#
# 문제는 구판 JSON 에 per_episode 가 없다는 것뿐이다(그 뒤에 추가된 필드). 재학습은
# 필요 없고, 같은 체크포인트를 같은 시드·같은 30 시나리오에서 다시 평가하면 된다.
# 결정론이므로 총계가 구판과 일치해야 한다 — 일치 여부부터 확인한다.
#
# 정숙 조건 — UE·CARLA 와 동시에 돌리지 않는다.
source "$(dirname "${BASH_SOURCE[0]}")/env.sh"

OUT=bench_results/clean_perep
mkdir -p "$OUT"
for d in runs/Intersection__clean_custom__*; do
  [ -d "$d" ] || continue
  s=$(basename "$d" | grep -oE '__[0-9]+__' | tr -d '_')
  f="$OUT/eval_md__clean_s$s.json"
  [ -f "$f" ] && { echo "skip s$s"; continue; }
  $PY bench/evaluate.py --run-dir "$d" --target metadrive --episodes 30 --seed 500000 \
    --out "$f" >> "$OUT/eval.log" 2>&1 && echo "OK s$s" || echo "FAIL s$s"
done
echo "CKPTPEREP_DONE $(date +%H:%M:%S)"
