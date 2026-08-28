#!/bin/bash
# CARLA 정책 x 거버너 절제 (2026-08-29).
#
# 두 가지를 동시에 묻는다.
#  (1) MetaDrive 전이에서 관측한 하강(20M 67.8% → 136M 48.9%)이 제3 시험장에서도
#      재현되는가? 재현되면 표본을 늘릴수록 실제로 일반화가 나빠진 것이고,
#      재현되지 않으면 MetaDrive 특유의 현상이다.
#  (2) 커널 내부 마찰 한계(MU_LAT)로 학습한 정책이 외부 속도 거버너를 대체하는가?
#      §6.6 에 향후 과제로 남겨둔 칸이다.
#
# 축: 정책 {fix20M, clean136M, slip} x 거버너 {0.8, off}. 나머지는 고정
# (전체 회전, NPC 3, 슬롯 3, --mask-degen). 배치는 반드시 순차 — 두 클라이언트가
# 같은 서버를 tick 하면 결과가 오염된다(실측).
set -u
LOG=/c/carla/policy_ab.log
RES=/c/carla/policy_ab
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
while [ $round -lt 12 ]; do
  round=$((round+1))
  for cond in "fix20M C:/ue/policy.npz 0.8" "clean136M C:/ue/policy_clean_s1.npz 0.8" \
              "slip C:/ue/policy_slip.npz 0.8" "fix20M C:/ue/policy.npz 0" \
              "clean136M C:/ue/policy_clean_s1.npz 0" "slip C:/ue/policy_slip.npz 0"; do
    set -- $cond
    pol=$1; path=$2; gov=$3
    ensure || { echo "[$(date +%H:%M)] 서버 복구 실패" >> $LOG; sleep 60; continue; }
    tag="ab_r${round}_${pol}_g${gov}"
    echo "[$(date +%H:%M)] R$round $pol gov$gov" >> $LOG
    PYTHONUTF8=1 $PY /c/Users/a3162/thesis/carla_drive.py --policy "$path" \
      --episodes 20 --max-steps 500 --turn-kind 전체 --npc 3 --governor "$gov" --mask-degen \
      --out "$RES/$tag.json" > $RES/$tag.log 2>&1
    grep -E "=== 전체" $RES/$tag.log | sed "s/^/  [$tag] /" >> $LOG 2>/dev/null
  done
  echo "AB_ROUND_DONE $round $(date +%H:%M)" >> $LOG
done
echo "AB_ALL_DONE $(date +%H:%M)" >> $LOG
