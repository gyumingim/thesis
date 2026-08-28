#!/bin/bash
# CARLA 폐루프 자율 진화 루프 v3 (2026-08-28 야간).
# 조건별 배치를 순회하며 결과를 누적한다. 액터 재사용 + 서버 자동 재기동.
# ★ 배치는 순차 실행 — 동시 실행 시 두 클라이언트가 같은 서버를 tick 해 결과가 오염된다(실측).
set -u
LOG=/c/carla/evolve5.log
RES=/c/carla/evolve5
PY="py -3.12"
mkdir -p $RES
alive() { $PY -c "
import carla,sys
try:
    c=carla.Client('127.0.0.1',2000); c.set_timeout(6.0); c.get_world().get_map()
except Exception: sys.exit(1)" 2>/dev/null; }
ensure() {
  alive && return 0
  echo "[$(date +%H:%M)] 서버 재기동" >> $LOG
  powershell -NoProfile -Command "Get-Process CarlaUnreal* -ErrorAction SilentlyContinue | Stop-Process -Force" 2>/dev/null
  sleep 6
  powershell -NoProfile -Command "Start-Process -FilePath 'C:\carla\Carla-0.10.0-Win64-Shipping\CarlaUnreal.exe' -ArgumentList '-RenderOffScreen','-nosound' -WindowStyle Hidden" 2>/dev/null
  for i in $(seq 30); do sleep 10; alive && return 0; done
  return 1
}
round=0
while [ $round -lt 40 ]; do
  round=$((round+1))
  # 조건: (회전종류, NPC수, 거버너) — 거버너 0 조건을 섞어 절제 데이터도 함께 쌓는다
  # 조건: 회전종류 NPC 거버너 마스킹 — 2x2 절제로 처방 기여도를 분리한다
  for cond in "전체 3 0.8 mask" "전체 3 0.8 nomask" "전체 3 0 mask" "전체 3 0 nomask" "우회전 3 0.8 mask" "좌회전 3 0.8 mask" "전체 8 0.8 mask" "우회전 3 0 nomask"; do
    set -- $cond
    kind=$1; npc=$2; gov=$3; msk=$4
    MFLAG=""; [ "$msk" = "mask" ] && MFLAG="--mask-degen"
    ensure || { echo "[$(date +%H:%M)] 서버 복구 실패" >> $LOG; sleep 60; continue; }
    tag="v4_r${round}_${kind}_npc${npc}_g${gov}_${msk}"
    echo "[$(date +%H:%M)] R$round $kind NPC$npc gov$gov" >> $LOG
    PYTHONUTF8=1 $PY /c/Users/a3162/thesis/carla_drive.py --policy C:/ue/policy.npz \
      --episodes 20 --max-steps 500 --turn-kind "$kind" --npc "$npc" --governor "$gov" $MFLAG \
      --out "$RES/$tag.json" > $RES/$tag.log 2>&1
    grep -E "=== 전체" $RES/$tag.log | sed "s/^/  [$tag] /" >> $LOG 2>/dev/null
  done
  echo "EVOLVE_ROUND_DONE $round $(date +%H:%M)" >> $LOG
done
echo "EVOLVE_ALL_DONE $(date +%H:%M)" >> $LOG
