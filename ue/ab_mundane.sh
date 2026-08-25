#!/bin/bash
# mundane vs default 프롬프트 A/B (렌더 완료 후 실행, GPU 필요)
# 10 표본 → hist-only 전처리 → 두 프리셋 정제(strength 0.3) → ISP → KID/KDD + sKVD
set -eu
S="200 236 272 308 344 380 416 452 488 524"
mkdir -p /c/ue/out_ab/src
for i in $S; do cp /c/ue/out_cs2/scene_$i.png /c/ue/out_ab/src/ 2>/dev/null || echo "누락 $i"; done
PY=/c/Users/a3162/thesis/.venv/Scripts/python.exe; export PYTHONUTF8=1   # CUDA torch (스토어 python 은 CPU 전용 함정)
$PY ue/isp_post.py "C:/ue/out_ab/src/*.png" C:/ue/out_ab/hist "C:/ue/ref_all/*.jpg" --hist-only
for P in default mundane; do
  $PY ue/neural_refine.py --src "C:/ue/out_ab/hist/*.jpg" --out /c/ue/out_ab/nr_$P --strength 0.3 --cn 0.6 --preset $P
  $PY ue/isp_post.py "C:/ue/out_ab/nr_$P/*.jpg" C:/ue/out_ab/fin_$P
  echo "== $P =="
  $PY ue/realism_metric.py --fake "C:/ue/out_ab/fin_$P/*.jpg" --real "C:/ue/ref_all/*.jpg" || echo "metric-fail realism $P"
  $PY ue/skvd_metric.py --fake "C:/ue/out_ab/fin_$P/*.jpg" --real "C:/ue/ref_all/*.jpg" || echo "metric-fail skvd $P"
done
echo AB_DONE
