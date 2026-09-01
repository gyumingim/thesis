#!/bin/bash
# 자산 탐색 전용 빌드 — 장면 1개만 만들고 probe_assets 로그를 수확한다(렌더 없음).
set -u
UE="/c/Program Files/Epic Games/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe"
PROJ="C:/Users/a3162/Documents/Unreal Projects/CitySample/CitySample.uproject"
OUT=/c/ue/probe; mkdir -p "$OUT"
MSYS_NO_PATHCONV=1 CS_OUT="C:/ue/probe" timeout -k 60 900 "$UE" "$PROJ" \
  -run=pythonscript -script="C:/Users/a3162/thesis/ue/scene_build_cs.py 1 seed=77000" \
  -unattended -nosplash -abslog="C:/ue/probe/build.log" > /dev/null 2>&1
echo "rc=$?"
grep "cs_build2" "C:/ue/probe/build.log" | sed 's/.*LogPython: //'
