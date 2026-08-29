#!/bin/bash
# 정정판 생성기 검증 세트 10장 (2026-08-29).
# 2026-08-29 감사에서 고친 18건(좌측통행·가시비·건물 관통·인도 매몰·차로 이산화·카메라
# 자유도 등)이 실제 렌더에서 회귀 없이 반영됐는지 육안 확인용. 출하 세트(out_cs2)와
# 섞이지 않도록 CS_OUT 으로 분리한다.
set -u
# 단일 인스턴스 잠금 — 2026-08-29 실측: 앞선 렌더가 도는 중에 재실행해 UE 두 개가 동시에
# 같은 레벨을 쓰면서 산출물이 섞였다(mass_gen.sh 가 같은 이유로 이미 잠금을 쓴다).
LOCK=/c/ue/verify10.lockdir
if ! mkdir "$LOCK" 2>/dev/null; then echo "already running, abort"; exit 1; fi
trap 'rmdir "$LOCK" 2>/dev/null' EXIT
UE="/c/Program Files/Epic Games/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe"
PROJ="C:/Users/a3162/Documents/Unreal Projects/CitySample/CitySample.uproject"
OUT=/c/ue/verify10
mkdir -p "$OUT"
export CS_OUT="C:/ue/verify10"
N=${1:-10}
echo "=== build 0-$((N-1)) $(date +%H:%M) ===" >> $OUT/log
MSYS_NO_PATHCONV=1 CS_OUT="C:/ue/verify10" timeout -k 60 1800 "$UE" "$PROJ" \
  -run=pythonscript -script="C:/Users/a3162/thesis/ue/scene_build_cs.py $N seed=90000" \
  -unattended -nosplash -abslog="C:/ue/verify10/build.log" > /dev/null 2>&1
echo "build rc=$? $(date +%H:%M)" >> $OUT/log
# ★ 2026-08-29 실측: 커맨드릿이 "done 10/10" 을 찍고도 특정 umap 저장에 실패할 수 있다
#   (파일 잠금 → LogSavePackage Error). 그래도 JSON 은 써지므로 **라벨과 레벨이 조용히
#   어긋난다**. 레벨이 JSON 보다 오래된 장면을 찾아 기록하고 렌더에서 제외한다.
GEN="/c/Users/a3162/Documents/Unreal Projects/CitySample/Content/GenScenes"
STALE=""
for i in $(seq 0 $((N-1))); do
  u=$(stat -c %Y "$GEN/gen_$i.umap" 2>/dev/null || echo 0)
  j=$(stat -c %Y "$OUT/scene_$i.json" 2>/dev/null || echo 0)
  if [ "$u" = 0 ] || [ $((j-u)) -gt 60 ]; then
    STALE="$STALE $i"; echo "STALE gen_$i (레벨이 JSON 보다 오래됨 — 렌더 제외)" >> $OUT/log
  fi
done
for i in $(seq 0 $((N-1))); do
  case " $STALE " in *" $i "*) continue;; esac
  [ -f "$OUT/scene_$i.png" ] && continue
  SHOT_LEVEL="/Game/GenScenes/gen_$i" SHOT_OUT="C:/ue/verify10/scene_$i" \
  MSYS_NO_PATHCONV=1 timeout -k 30 300 "$UE" "$PROJ" "/Game/GenScenes/gen_$i" \
    -game -RenderOffscreen -unattended -nosplash -ResX=1280 -ResY=720 \
    -ExecCmds="py C:/ue/scripts/shot_once.py" -abslog="C:/ue/verify10/render_$i.log" > /dev/null 2>&1
  [ -f "$OUT/scene_$i.png" ] && echo "OK scene_$i $(date +%H:%M:%S)" >> $OUT/log \
                             || echo "FAIL scene_$i" >> $OUT/log
done
echo "VERIFY10_DONE $(date +%H:%M)" >> $OUT/log
