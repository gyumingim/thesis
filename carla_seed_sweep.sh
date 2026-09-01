#!/bin/bash
# CARLA 시드 정합 정책 스윕 (2026-08-29).
#
# 묻는 것. MetaDrive 전이 성능 순위가 제3 시험장(CARLA) 순위를 예측하는가?
# 그리고 표본을 7배로 늘린 확정판(136M)이 CARLA 에서도 20M 판보다 나쁜가?
#
# 앞선 1라운드 결과(20M s1 95% vs 136M s1 60%)는 **시드 품질이 교락**돼 있었다 —
# 20M s1 은 그 조건의 최고 시드(MD 83%), 136M s1 은 최저 시드(MD 27%)였다.
# 따라서 조건당 3시드를 모두 돌려 시드 평균으로 비교한다.
#
# 축: 정책 6종(fix_s1..s3 = 20M, clean_s1..s3 = 136M) + slip.
# 나머지 고정: 전체 회전, NPC 3, 슬롯 3, --mask-degen, 거버너 0.8g.
# ★ 순차 실행 — 두 클라이언트가 같은 서버를 tick 하면 결과가 오염된다(실측).
# ★ 라운드마다 --seed 를 바꾼다. 안 바꾸면 평가가 결정론이라 라운드가 전부
#   동일해진다(2026-09-01 실측: 6라운드가 바이트 단위로 같았다).
set -u
LOG=/c/carla/seed_sweep.log
RES=/c/carla/seed_sweep
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
while [ $round -lt 6 ]; do
  round=$((round+1))
  for pol in fix_s1 fix_s2 fix_s3 clean_s1 clean_s2 clean_s3 clean_s4 clean_s5 slip; do
    ensure || { echo "[$(date +%H:%M)] 서버 복구 실패" >> $LOG; sleep 60; continue; }
    tag="sw_r${round}_${pol}"
    echo "[$(date +%H:%M)] R$round $pol" >> $LOG
    PYTHONUTF8=1 $PY /c/Users/a3162/thesis/carla_drive.py --policy "C:/ue/policy_${pol}.npz" \
      --episodes 20 --max-steps 500 --turn-kind 전체 --npc 3 --governor 0.8 --mask-degen \n      --seed $round \
      --out "$RES/$tag.json" > $RES/$tag.log 2>&1
    grep -E "=== 전체" $RES/$tag.log | sed "s/^/  [$tag] /" >> $LOG 2>/dev/null
  done
  echo "SWEEP_ROUND_DONE $round $(date +%H:%M)" >> $LOG
done
echo "SWEEP_ALL_DONE $(date +%H:%M)" >> $LOG
