#!/bin/bash
# 배치 스크립트 공통 실행 환경 — OS 분기를 여기 한 곳에만 둔다.
# 이유: run_main*.sh 가 각자 `cd /home/karma/thesis` + `.venv/bin/python` 을 하드코딩해
#       장비를 옮길 때마다 5벌을 고쳐야 했다. 분기점을 1벌로 줄인다.
# 사용:  source "$(dirname "${BASH_SOURCE[0]}")/env.sh"
set -u

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

if [ -x .venv/Scripts/python.exe ]; then
  PY=".venv/Scripts/python.exe"      # Windows (Git Bash)
elif [ -x .venv/bin/python ]; then
  PY=".venv/bin/python"              # Linux
else
  echo "env.sh: .venv 가 없다 ($ROOT)" >&2; exit 1
fi

# PYTHONUTF8=1 필수: 한국어 윈도우 콘솔 기본 코덱이 cp949 라 스크립트의 유니코드 출력
# (체크표시·한글 진단문)이 UnicodeEncodeError 로 죽는다. 로그도 UTF-8 로 통일된다.
# 경량(numba) 커널을 쓰는 실행 — 학습·평가 모두 8스레드로 고정.
PYRUN()    { env -u PYTHONPATH PYTHONUTF8=1 NUMBA_NUM_THREADS=8 "$PY" "$@"; }
# MetaDrive 학습 전용 — 원 배치(run_main.sh)와 동일하게 NUMBA_NUM_THREADS 를 두지 않는다.
PYRUN_MD() { env -u PYTHONPATH PYTHONUTF8=1 "$PY" "$@"; }
