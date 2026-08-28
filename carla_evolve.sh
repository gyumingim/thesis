#!/bin/bash
# CARLA 폐루프 자율 진화 루프 v2 (2026-08-28 야간).
# 액터 재사용으로 크래시 감소, 그래도 죽으면 서버 자동 재기동. 조건별 20에피소드씩 순회.
set -u
LOG=/c/carla/evolve.log
RES=/c/carla/evolve
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
while [ $round -lt 60 ]; do
  round=$((round+1))
  for cond in "전체 3" "우회전 3" "좌회전 3" "전체 8"; do
    set -- $cond
    kind=$1; npc=$2
    ensure || { echo "[$(date +%H:%M)] 서버 복구 실패" >> $LOG; sleep 60; continue; }
    tag="r${round}_${kind}_npc${npc}"
    echo "[$(date +%H:%M)] R$round $kind NPC$npc 시작" >> $LOG
    PYTHONUTF8=1 $PY /c/Users/a3162/thesis/carla_drive.py --policy C:/ue/policy.npz \
      --episodes 20 --max-steps 400 --turn-kind "$kind" --npc "$npc" \
      --out "$RES/$tag.json" > $RES/$tag.log 2>&1
    grep -E "=== 전체|^  [가-힣]+:" $RES/$tag.log >> $LOG 2>/dev/null
  done
  echo "EVOLVE_ROUND_DONE $round $(date +%H:%M)" >> $LOG
done
echo "EVOLVE_ALL_DONE $(date +%H:%M)" >> $LOG
