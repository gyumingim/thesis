#!/bin/bash
# 대량 생성 — scene_200~559 (360장). 재개형: 이미 있는 PNG 는 건너뜀.
# 정제(디퓨전+ISP)는 렌더 완료 후 별도 실행 (GPU 경합 방지).
set -u
UE="/c/Program Files/Epic Games/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe"
PROJ="C:/Users/a3162/Documents/Unreal Projects/CitySample/CitySample.uproject"
LOG=/c/ue/out_cs2/massgen.log
FROM=${1:-200}; TO=${2:-559}
ONLY=$(seq -s, $FROM $TO)
echo "=== build $FROM-$TO $(date +%H:%M) ===" >> $LOG
MSYS_NO_PATHCONV=1 "$UE" "$PROJ" -run=pythonscript -script="C:/Users/a3162/thesis/ue/scene_build_cs.py $((TO+1)) only=$ONLY seed=50000" -unattended -nosplash -abslog=C:/ue/out_cs2/massbuild.log > /dev/null 2>&1
echo "build done $(date +%H:%M)" >> $LOG
for i in $(seq $FROM $TO); do
  [ -f /c/ue/out_cs2/scene_$i.png ] && continue
  for try in 1 2 3; do
    SHOT_LEVEL="/Game/GenScenes/gen_$i" SHOT_OUT="C:/ue/out_cs2/scene_$i" MSYS_NO_PATHCONV=1 timeout -k 30 240 "$UE" "$PROJ" "/Game/GenScenes/gen_$i" -game -RenderOffscreen -unattended -nosplash -ResX=1280 -ResY=720 -ExecCmds="py C:/ue/scripts/shot_once.py" -abslog="C:/ue/out_cs2/render_$i.log" > /dev/null 2>&1
    taskkill //F //IM UnrealEditor-Cmd.exe > /dev/null 2>&1
    [ -f /c/ue/out_cs2/scene_$i.png ] && break
  done
  [ -f /c/ue/out_cs2/scene_$i.png ] && echo "OK $i $(date +%H:%M)" >> $LOG || echo "FAIL $i" >> $LOG
done
echo "MASSGEN_RENDER_DONE $(date +%H:%M)" >> $LOG
