#!/bin/bash
# 360장 프로덕션 정제 — A/B 승자(default) 파이프라인: 색정합 -> 디퓨전 0.3 -> ISP
# 산출 2팔: fin_refined(전체 체인) / fin_plain(ISP만 — 디퓨전 기여 분리용). 원본은 out_cs2 보존.
set -eu
V=/c/Users/a3162/thesis/.venv/Scripts/python.exe; export PYTHONUTF8=1
LOG=/c/ue/out_prod/prod.log
mkdir -p /c/ue/out_prod
$V ue/isp_post.py "C:/ue/out_cs2/scene_[2345][0-9][0-9].png" C:/ue/out_prod/hist "C:/ue/ref_all/*.jpg" --hist-only >> $LOG 2>&1
echo "hist done $(date +%H:%M)" >> $LOG
$V ue/neural_refine.py --src "C:/ue/out_prod/hist/*.jpg" --out /c/ue/out_prod/nr --strength 0.3 --cn 0.6 --preset default >> $LOG 2>&1
echo "refine done $(date +%H:%M)" >> $LOG
$V ue/isp_post.py "C:/ue/out_prod/nr/*.jpg" C:/ue/out_prod/fin_refined >> $LOG 2>&1
$V ue/isp_post.py "C:/ue/out_cs2/scene_[2345][0-9][0-9].png" C:/ue/out_prod/fin_plain >> $LOG 2>&1
echo "PROD_DONE $(date +%H:%M)" >> $LOG
