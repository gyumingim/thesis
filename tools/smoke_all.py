"""분석 도구가 **아직도 도는가** — 재현성의 가장 싼 점검.

논문은 수치마다 도구 경로를 인용한다(`tools/…`). 심사자가 가장 먼저 하는 일이 그걸
그대로 돌려 보는 것인데, 이번 달에만 여러 도구에 플래그·환경변수를 붙였고(ARM_SEEDS,
DPC_SRC, --fast, --reuse, --plan-only) 시드 목록 기본값도 한 번 바꿨다 되돌렸다.
**하나라도 죽어 있으면 그 자리에서 재현이 막힌다.**

인자 없이 돌려 종료 코드를 본다. 오래 걸리거나 외부 서비스가 필요한 것, **파일을 쓰는
것**은 제외한다(그림을 다시 만들어 커밋된 산출물을 흔들면 점검이 부작용을 낳는다).

실행: .venv/Scripts/python.exe tools/smoke_all.py
"""
import io
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PY_EXE = os.path.join(ROOT, ".venv", "Scripts", "python.exe")
TIMEOUT = 150
# 느린 것은 «고장» 이 아니다. 실제로 재 보고 개별 예산을 준다 — 제외하면 점검에서
# 빠지지만 여기 두면 계속 «도는지» 를 확인받는다.
SLOW = {"entropy_collapse.py": 420}      # 실측 293s (2026-09-22)

SKIP = {
    "smoke_all.py": "자기 자신",
    "export_policy.py": "인자 필요 + npz 를 쓴다",
    "percept_run.py": "CARLA 서버 필요",
    "percept_prep.py": "원자료 준비 단계 — 파일을 쓴다",
    "plate_composite.py": "이미지를 쓴다",
    "tesla_dashboard.py": "그림을 쓴다(figs/ 를 흔든다)",
    "viz_dashboard.py": "그림을 쓴다(figs/ 를 흔든다)",
    # 인자 없이 돌긴 하지만 오래 걸린다. 점검의 목적은 «죽었는가» 이지
    # «빠른가» 가 아니므로, 소요를 적어 두고 제외한다.
    "percept_ft.py": "미세조정 — 소요 미측정(추정만으로 제외한다고 적어 둔다)",
}


def sh_lint():
    """셸 스크립트의 **줄 중간 리터럴 backslash-n** 을 잡는다.

    2026-09-22 실측: `carla_seed_sweep.sh` 의 줄바꿈 이음이 리터럴 «backslash n» 으로
    망가져 있었다(heredoc 편집 사고로 추정). bash 는 그것을 **낱말 `n`** 으로 읽으므로
    argparse 가 「unrecognized arguments: n」 으로 죽는다 — 즉 그 스크립트는 망가진
    2026-09-01 이후 **한 번도 돌지 않았다**(결과 파일이 전부 08-29 자다).
    `bash -n` 은 문법이 맞으므로 잡지 못한다. 그래서 따로 본다.
    """
    import glob
    BS = chr(92)
    bad = []
    for f in sorted(glob.glob(os.path.join(ROOT, "**", "*.sh"), recursive=True)):
        if ".venv" in f:
            continue
        for i, line in enumerate(io.open(f, encoding="utf-8", errors="replace"), 1):
            t = line.rstrip(chr(10))
            j = t.find(BS + "n")
            if j >= 0 and j != len(t) - 2:      # 줄 끝 «\» 는 정상 이음
                bad.append((os.path.relpath(f, ROOT), i, t.strip()[:90]))
    if bad:
        print("셸 스크립트 줄 중간 리터럴 backslash-n — bash 가 낱말 n 으로 읽는다:")
        for f, i, t in bad:
            print("  %s:%d  %s" % (f, i, t))
    else:
        print("셸 스크립트 줄 중간 리터럴 backslash-n: 없음")
    return len(bad)


def main():
    n_sh = sh_lint()
    print("")
    files = sorted(os.path.basename(f) for f in glob.glob(os.path.join(ROOT, "tools", "*.py")))
    ok = fail = skipped = 0
    bad = []
    for f in files:
        if f in SKIP:
            print("  %-28s 건너뜀 — %s" % (f, SKIP[f]))
            skipped += 1
            continue
        try:
            r = subprocess.run([PY_EXE, os.path.join(ROOT, "tools", f)],
                               cwd=ROOT, capture_output=True, text=True,
                               encoding="utf-8", errors="replace",
                               env=dict(os.environ, PYTHONUTF8="1"),
                               timeout=SLOW.get(f, TIMEOUT))
            rc = r.returncode
        except subprocess.TimeoutExpired:
            rc, r = -9, None
        # 인자가 필요한 도구는 «사용법을 찍고 rc=2» 가 정상이다. 그것까지 확인하면
        # SKIP 으로 빼는 것보다 낫다 — 빼면 그 도구는 점검에서 사라지지만, 이렇게
        # 두면 «죽지 않고 안내한다» 를 매번 확인받는다.
        _txt = "" if r is None else ((r.stdout or "") + (r.stderr or ""))
        # argparse 는 영어 "usage:" 를, 손으로 적은 안내는 "사용:" 을 찍는다
        _usage = rc == 2 and ("사용:" in _txt or "usage:" in _txt)
        if rc == 0 or _usage:
            ok += 1
            print("  %-28s OK%s" % (f, " (인자 필요 — 사용법 출력)" if _usage else ""))
        else:
            fail += 1
            tail = ""
            if r is not None:
                lines = [x for x in (r.stderr or "").strip().split(chr(10)) if x.strip()]
                tail = lines[-1][:110] if lines else (r.stdout or "").strip()[-110:]
            else:
                tail = "시간 초과 %ds" % SLOW.get(f, TIMEOUT)
            bad.append((f, rc, tail))
            print("  %-28s **실패 rc=%s** %s" % (f, rc, tail))
    print("")
    print("성공 %d · 실패 %d · 건너뜀 %d (전체 %d)" % (ok, fail, skipped, len(files)))
    if bad:
        print("")
        print("실패 목록 — 논문이 인용하는 경로라면 재현이 그 자리에서 막힌다:")
        for f, rc, tail in bad:
            print("  %-28s rc=%-4s %s" % (f, rc, tail))
        print("")
        print("※ 인자가 꼭 필요한 도구라면 SKIP 에 이유와 함께 넣는다. 그냥 두면")
        print("  다음 점검에서 또 «실패» 로 뜨고, 진짜 고장과 구분이 안 된다.")
    return 1 if (bad or n_sh) else 0


if __name__ == "__main__":
    sys.exit(main())
