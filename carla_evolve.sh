#!/bin/bash
# CARLA 폐루프 자율 진화 루프 (2026-08-28 야간).
# 서버 크래시 자동 복구 + 조건별 배치 반복 + 결과 누적. 각 라운드 결과는 JSON 으로 남겨
# 다음 개선의 근거로 쓴다.
set -u
LOG=/c/carla/evolve.log
PY="py -3.12"
RES=/c/carla/evolve
mkdir -p $RES
ensure_server() {
  local n=$(powershell -NoProfile -Command "(Get-Process CarlaUnreal* -ErrorAction SilentlyContinue).Count" 2>/dev/null | tr -d '\r')
  if ! $PY -c "
import carla,sys
try:
    c=carla.Client('127.0.0.1',2000); c.set_timeout(6.0); c.get_world().get_map()
except Exception: sys.exit(1)" 2>/dev/null; then
    echo "[$(date +%H:%M)] 서버 재기동" >> $LOG
    powershell -NoProfile -Command "Get-Process CarlaUnreal* -ErrorAction SilentlyContinue | Stop-Process -Force" 2>/dev/null
    sleep 5
    powershell -NoProfile -Command "Start-Process -FilePath 'C:\carla\Carla-0.10.0-Win64-Shipping\CarlaUnreal.exe' -ArgumentList '-RenderOffScreen','-nosound' -WindowStyle Hidden" 2>/dev/null
    for i in $(seq 30); do
      sleep 10
      $PY -c "
import carla,sys
try:
    c=carla.Client('127.0.0.1',2000); c.set_timeout(6.0); c.get_world().get_map()
except Exception: sys.exit(1)" 2>/dev/null && break
    done
  fi
}
round=0
while [ $round -lt 40 ]; do
  round=$((round+1))
  for cond in "직진 3" "우회전 3" "좌회전 3" "직진 6"; do
    set -- $cond
    kind=$1; npc=$2
    ensure_server
    tag="r${round}_${kind}_npc${npc}"
    echo "[$(date +%H:%M)] 라운드 $round · $kind · NPC $npc" >> $LOG
    PYTHONUTF8=1 $PY /c/Users/a3162/thesis/carla_drive.py --policy C:/ue/policy.npz \
      --episodes 8 --max-steps 400 --turn-kind "$kind" --npc "$npc" \
      > $RES/$tag.log 2>&1
    grep -E "^  (직진|좌회전|우회전):|=== 전체" $RES/$tag.log >> $LOG 2>/dev/null
    cp /c/carla/drive_results.json $RES/$tag.json 2>/dev/null || cp ./drive_results.json $RES/$tag.json 2>/dev/null
  done
  echo "EVOLVE_ROUND_DONE $round $(date +%H:%M)" >> $LOG
done
echo "EVOLVE_ALL_DONE $(date +%H:%M)" >> $LOG
