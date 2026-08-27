#!/bin/bash
# 번호판 흰-패스 야간 배치: white 일괄 적용 -> 360장 렌더 -> revert 원복
set -u
LOCK=/c/ue/out_cs2/whitepass.lockdir
if ! mkdir "$LOCK" 2>/dev/null; then echo "already running" >> /c/ue/whitepass.log; exit 1; fi
trap 'rmdir "$LOCK" 2>/dev/null' EXIT
UE="/c/Program Files/Epic Games/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe"
PROJ="C:/Users/a3162/Documents/Unreal Projects/CitySample/CitySample.uproject"
LOG=/c/ue/whitepass.log
echo "=== whitepass $(date +%H:%M) ===" >> $LOG
MSYS_NO_PATHCONV=1 "$UE" "$PROJ" -run=pythonscript -script="C:/Users/a3162/thesis/ue/plate_swap.py white 200 559" -unattended -nosplash -abslog=C:/ue/wp_apply.log > /dev/null 2>&1
grep -q "WHITE_DONE" /c/ue/wp_apply.log && echo "white 적용 OK" >> $LOG || { echo "WHITEPASS_ABORT apply실패" >> $LOG; exit 2; }
mkdir -p /c/ue/out_wp
CONSEC=0
for i in $(seq 200 559); do
  [ -f /c/ue/out_wp/white_$i.png ] && continue
  for try in 1 2 3; do
    SHOT_LEVEL="/Game/GenScenes/gen_$i" SHOT_OUT="C:/ue/out_wp/white_$i" MSYS_NO_PATHCONV=1 timeout -k 30 240 "$UE" "$PROJ" "/Game/GenScenes/gen_$i" -game -RenderOffscreen -unattended -nosplash -ResX=1280 -ResY=720 -ExecCmds="py C:/ue/scripts/shot_once.py" -abslog="C:/ue/out_wp/r_$i.log" > /dev/null 2>&1
    taskkill //F //IM UnrealEditor-Cmd.exe > /dev/null 2>&1
    [ -f /c/ue/out_wp/white_$i.png ] && break
  done
  if [ -f /c/ue/out_wp/white_$i.png ]; then echo "OK $i $(date +%H:%M)" >> $LOG; CONSEC=0
  else echo "FAIL $i" >> $LOG; CONSEC=$((CONSEC+1)); [ $CONSEC -ge 5 ] && { echo "WHITEPASS_ABORT" >> $LOG; break; }; fi
done
MSYS_NO_PATHCONV=1 "$UE" "$PROJ" -run=pythonscript -script="C:/Users/a3162/thesis/ue/plate_swap.py revert 180 559" -unattended -nosplash -abslog=C:/ue/wp_revert.log > /dev/null 2>&1
grep -q "REVERT_DONE" /c/ue/wp_revert.log && echo "revert OK" >> $LOG || echo "REVERT_FAIL — 수동 원복 필요" >> $LOG
echo "WHITEPASS_DONE $(date +%H:%M)" >> $LOG
