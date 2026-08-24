#!/bin/bash
# CitySample 장면 렌더 드라이버 — 장면마다 -game 프로세스 1회 (부팅 ~35s + 수렴 25s).
# 전제: scene_build_cs.py 가 /Game/GenScenes/gen_<i> 와 C:\ue\out_cs2\scene_<i>.json 생성 완료.
# 사용: bash ue/cs_render.sh <장면수>
# 산출: C:\ue\out_cs2\scene_<i>.png (HighResShot filename= — 결정적 이름, 자동 넘버링 미사용)
set -u
N=${1:?장면수}
UE="/c/Program Files/Epic Games/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe"
PROJ="C:/Users/a3162/Documents/Unreal Projects/CitySample/CitySample.uproject"
OUT=/c/ue/out_cs2
mkdir -p "$OUT"
for i in $(seq 0 $((N-1))); do
  [ -f "$OUT/scene_$i.png" ] && { echo "skip scene_$i"; continue; }
  echo "=== render scene_$i $(date +%H:%M:%S) ==="
  SHOT_LEVEL="/Game/GenScenes/gen_$i" SHOT_OUT="C:/ue/out_cs2/scene_$i" \
  MSYS_NO_PATHCONV=1 timeout -k 30 300 "$UE" "$PROJ" "/Game/GenScenes/gen_$i" \
    -game -RenderOffscreen -unattended -nosplash -ResX=1280 -ResY=720 \
    -ExecCmds="py C:/ue/scripts/shot_once.py" -abslog="$OUT/render_$i.log" > /dev/null 2>&1
  [ -f "$OUT/scene_$i.png" ] && echo "  OK scene_$i.png" || echo "  !! scene_$i 실패 (render_$i.log)"
done
echo "RENDER_ALL_DONE $(date +%H:%M:%S)"
