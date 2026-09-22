"""논문 수치 회귀 검사 — PAPER.md 의 핵심 수치를 원자료에서 다시 계산해 대조한다.

이 논문은 같은 실험을 세 조건(오류판 / GPU 경합 정정판 / 정숙 확정판)에서 돌렸고,
세 조건의 수치가 본문 900줄에 흩어져 있다. 개정 과정에서 한 조건의 통계가 다른 조건의
문장에 섞여 들어가는 사고가 실제로 여러 번 났다(예: 정숙 조건 문단에 경합 조건의
이탈률이 실려 있었다). 그래서 헤드라인 수치는 사람이 아니라 이 스크립트가 지킨다.

실행: python tools/paper_numbers_check.py     (불일치가 있으면 비영 종료)
"""
import glob
import json
import re
import sys

import numpy as np

PAPER = "PAPER.md"


def curve(pattern):
    """시드별 체크포인트 곡선 → {ckpt: [시드별 성공률%]}"""
    per = {}
    for f in sorted(glob.glob(pattern)):
        for r in json.load(open(f)):
            per.setdefault(r["ckpt"], []).append(100 * r["success_rate"])
    return per


def finals(pattern, key="success_rate"):
    out = []
    for f in sorted(glob.glob(pattern)):
        fin = [r for r in json.load(open(f)) if r["ckpt"] == "final.pt"]
        if fin:
            out.append(100 * fin[0][key])
    return out


# ★ 선택 검사가 실패해도 전체를 막지 않지만 **조용히 사라지면 안 된다**.
# 실제로 os 미import 로 블록 하나가 통째로 죽어 있었는데 출력은 «전 항목 일치»
# 였다(2026-09-15). 건너뛴 사실과 이유를 반드시 남긴다.
def _skip(tag, e):
    print("  (검사 건너뜀 [%s]: %s: %s)" % (tag, type(e).__name__, e))
    if isinstance(e, ImportError):
        print("     → 의존 모듈이 없다. **.venv/Scripts/python.exe 로 실행하라** —")
        print("       시스템 파이썬으로 돌리면 이 검사가 조용히 빠진다.")


def main():
    text = open(PAPER, encoding="utf-8").read()
    clean = curve("bench_results/clean/eval_md__clean_s*.json")
    fixed = curve("bench_results/fixed/eval_md__fix_s*.json")
    if not clean:
        print("원자료 없음 — bench_results/clean 이 필요하다")
        return 2

    cf = finals("bench_results/clean/eval_md__clean_s*.json")
    co = finals("bench_results/clean/eval_md__clean_s*.json", "out_of_road_rate")
    all_ck = [v for vs in clean.values() for v in vs]
    oracle = np.mean([max(100 * r["success_rate"] for r in json.load(open(f)))
                      for f in sorted(glob.glob("bench_results/clean/eval_md__clean_s*.json"))])
    peak_ck = max((np.mean(v), k) for k, v in clean.items() if k != "final.pt")

    checks = [
        ("확정 전이 평균", "49.3", "%.1f" % np.mean(cf)),
        ("확정 전이 σ", "16.1", "%.1f" % np.std(cf, ddof=1)),
        ("확정 시드값", "27/67/53/40/60", "/".join("%.0f" % v for v in cf)),
        ("정숙 최종 이탈 하한", "10", "%.0f" % min(co)),
        ("정숙 최종 이탈 상한", "30", "%.0f" % max(co)),
        ("정숙 체크포인트 성공 하한", "20", "%.0f" % min(all_ck)),
        ("정숙 체크포인트 성공 상한", "83", "%.0f" % max(all_ck)),
        ("오라클 조기정지", "64.7", "%.1f" % oracle),
        ("피크 값", "55.3", "%.1f" % peak_ck[0]),
        ("피크 체크포인트", "t000600.pt", peak_ck[1]),
        ("경합 조건 전이", "67.8", "%.1f" % np.mean(finals("bench_results/fixed/eval_md__fix_s*.json"))),
    ]

    # 정숙 조건 in-domain (§4.7 통제 확인)
    ind = []
    for f in sorted(glob.glob("bench_results/clean/eval_cu__clean_s*.json")):
        d = json.load(open(f))
        d = d if isinstance(d, list) else [d]
        ind += [100 * r["success_rate"] for r in d]
    if ind:
        checks.append(("정숙 in-domain", "82.8", "%.1f" % np.mean(ind)))

    # 실패 모드 추세의 종점 (final.pt 제외 — tools/failure_mode_trend.py 와 동일 범위)
    def mean_at(ck, field):
        vals = []
        for f in sorted(glob.glob("bench_results/clean/eval_md__clean_s*.json")):
            hit = [r for r in json.load(open(f)) if r["ckpt"] == ck]
            if hit:
                vals.append(100 * hit[0][field])
        return np.mean(vals) if vals else float("nan")
    checks += [
        ("이탈 시작(t300)", "12.7", "%.1f" % mean_at("t000300.pt", "out_of_road_rate")),
        ("이탈 종점(t3300)", "22.7", "%.1f" % mean_at("t003300.pt", "out_of_road_rate")),
        ("충돌 시작(t300)", "32.7", "%.1f" % mean_at("t000300.pt", "crash_rate")),
        ("충돌 종점(t3300)", "27.3", "%.1f" % mean_at("t003300.pt", "crash_rate")),
        ("이탈 final 포함시", "20.0", "%.1f" % mean_at("final.pt", "out_of_road_rate")),
        ("25분 최저", "48.0", "%.1f" % mean_at("t001500.pt", "success_rate")),
    ]

    # 5분 대 40분 낙폭 검정은 n=5 에서 철회됐다(§6.2 정정 상자). 대신 '성공률 시간 추세의
    # 부호가 갈린다'는 사실 자체를 지킨다 — 다시 한 방향으로 몰리면 검사가 알려준다.
    try:
        from scipy import stats as _st
        signs = set()
        for f in sorted(glob.glob("bench_results/clean/eval_md__clean_s*.json")):
            rows = sorted(json.load(open(f)), key=lambda r: r["elapsed_s"])
            rows = [r for r in rows if r["ckpt"] != "final.pt"]
            t, _ = _st.kendalltau([r["elapsed_s"] for r in rows],
                                  [r["success_rate"] for r in rows])
            signs.add(int(np.sign(t)))
        checks.append(("성공률 추세 부호", "불일치", "불일치" if len(signs) > 1 else "일치"))
    except Exception as _e:
        _skip("성공률 추세 부호", _e)

    # 동일 장비 대조 (데스크톱 정숙 네이티브 3시드) — 헤드라인 판정의 근거
    def curve_mean(pattern, ckpt, field="success_rate"):
        vals = []
        for f in sorted(glob.glob(pattern)):
            hit = [r for r in json.load(open(f)) if r["ckpt"] == ckpt]
            if hit:
                vals.append(100 * hit[0][field])
        return np.mean(vals) if vals else float("nan")

    ND = "bench_results/native_desktop/eval_md__nd_s*.json"
    LT = "bench_results/clean/eval_md__clean_s*.json"
    nd_final = [100 * [r for r in json.load(open(f)) if r["ckpt"] == "final.pt"][0]["success_rate"]
                for f in sorted(glob.glob(ND))
                if [r for r in json.load(open(f)) if r["ckpt"] == "final.pt"]]
    if len(nd_final) >= 3:
        checks += [
            ("동일장비 네이티브 최종", "62.0", "%.1f" % np.mean(nd_final)),
            ("동일장비 네이티브 σ", "14.5", "%.1f" % np.std(nd_final, ddof=1)),
            ("네이티브 5분", "36.7", "%.1f" % curve_mean(ND, "t000300.pt")),
            ("네이티브 15분", "59.3", "%.1f" % curve_mean(ND, "t000900.pt")),
            ("5분 우위", "18.0", "%.1f" % (curve_mean(LT, "t000300.pt") - curve_mean(ND, "t000300.pt"))),
        ]
        # 실현 배수: 같은 장비·같은 조건의 스텝 수 비
        def steps(pattern):
            v = [[r for r in json.load(open(f)) if r["ckpt"] == "final.pt"][0]["global_step"]
                 for f in sorted(glob.glob(pattern))
                 if [r for r in json.load(open(f)) if r["ckpt"] == "final.pt"]]
            return np.mean(v)
        checks.append(("실현 배수(동일 장비 정숙)", "35.9", "%.1f" % (steps(LT) / steps(ND))))
    # 교차 구조 검정 (§6.2) — 주장의 내용이 검정되는지 지킨다
    try:
        import itertools as _it
        import numpy as _np
        def _curve(pat):
            per = {}
            for f in sorted(glob.glob(pat)):
                sd = f.split("_s")[-1][:-5]
                for r in json.load(open(f)):
                    per.setdefault(r["ckpt"], {})[sd] = 100 * r["success_rate"]
            return per
        Lc = _curve("bench_results/clean/eval_md__clean_s*.json")
        Nc = _curve("bench_results/native_desktop/eval_md__nd_s*.json")
        if Lc and Nc:
            def _d(per, a):
                sd = sorted(per["final.pt"])
                return _np.array([per["final.pt"][x] - per[a][x] for x in sd])
            dl, dn = _d(Lc, "t000300.pt"), _d(Nc, "t000300.pt")
            allv = _np.concatenate([dl, dn]); obs = dn.mean() - dl.mean()
            hit = tot = 0
            for idx in _it.combinations(range(len(allv)), len(dl)):
                m = _np.zeros(len(allv), bool); m[list(idx)] = True
                tot += 1
                hit += abs(allv[~m].mean() - allv[m].mean()) >= abs(obs) - 1e-9
            checks += [("교차 기울기 차이", "30.7", "%.1f" % obs),
                       ("교차 순열 p", "0.0079", "%.4f" % (hit / tot))]
    except Exception as _e:
        _skip("교차 구조 검정", _e)

    # 오라클 이득이 선택 편향인지 (§6.2·§7 (5)) — 널 분포 안이면 신호가 아니다
    try:
        import numpy as _np
        rng = _np.random.default_rng(0)
        fins, ors, nck = [], [], None
        for f in sorted(glob.glob("bench_results/clean/eval_md__clean_s*.json")):
            rows = json.load(open(f))
            fins.append(100 * [r for r in rows if r["ckpt"] == "final.pt"][0]["success_rate"])
            ors.append(max(100 * r["success_rate"] for r in rows))
            nck = len(rows)
        pr = _np.mean(fins) / 100.0
        null = _np.array([(rng.binomial(30, pr, size=(len(fins), nck)) / 30 * 100)
                          .max(axis=1).mean() for _ in range(4000)])
        lo, hi = _np.percentile(null, [2.5, 97.5])
        inside = lo <= _np.mean(ors) <= hi
        checks.append(("오라클 이득 = 선택 편향", "예", "예" if inside else "아니오"))
    except Exception as _e:
        _skip("오라클 편향", _e)

    # DPC 재산출 (§6.3) — tools/dpc_recompute.py 와 같은 정의로 다시 계산
    try:
        sys.path.insert(0, "tools")
        from dpc_recompute import pair_seed, stratified_tau
        import re as _re
        pr = []
        for ev in sorted(glob.glob("bench_results/clean/eval_md__clean_s*.json")):
            sd = _re.search(r"_s(\d+)\.json$", ev).group(1)
            rd = glob.glob("runs/Intersection__clean_custom__%s__*" % sd)
            if rd:
                got = pair_seed(rd[0], ev)
                if got:
                    pr.append(got)
        if len(pr) >= 3:
            e = [(L[T <= 1800], M[T <= 1800]) for L, M, T in pr]
            l = [(L[T > 1800], M[T > 1800]) for L, M, T in pr]
            checks += [("DPC 전반 τ", "0.190", "%.3f" % stratified_tau(e)),
                       ("DPC 후반 τ", "0.039", "%.3f" % stratified_tau(l))]
    except Exception as _e:
        _skip("DPC τ 재산출", _e)

    # 본문에 인용되지 **않는 것이 맞는** 항목 — 값은 지키되 누락 경고를 내지 않는다.
    # 이탈/충돌 종점은 "실패가 충돌에서 이탈로 옮겨간다" 주장이 n=5 에서 철회되면서
    # 본문에서 빠졌다(§6.2). 값 자체는 회귀 감시를 위해 계속 대조한다.
    # 시나리오 블록 측정 (§7 표 6) — 원자료에서 재계산해 대조한다
    try:
        import statistics as _sb
        _R = "bench_results/scenario_blocks"
        # ★ 블록 목록을 하드코딩하지 않는다 — 2026-09-16 에 넷에서 여덟으로
        #   늘렸는데 상수를 고치지 않으면 검사가 옛 표본을 계속 본다.
        _B = sorted({int(_f.split('__b')[1][:-5])
                     for _f in glob.glob('%s/eval_md__clean_s1__b*.json' % _R)})

        def _rt(t, b):
            rows = json.load(open("%s/eval_md__%s__b%d.json" % (_R, t, b), encoding="utf-8"))
            return 100.0 * [x for x in rows if x["ckpt"] == "final.pt"][0]["success_rate"]
        _L = ["clean_s%d" % i for i in (1, 2, 3, 4, 5)]
        _N = ["nd_s%d" % i for i in (2, 3, 4, 5, 6)]
        _g = [_sb.mean(_rt(t, b) for t in _L) - _sb.mean(_rt(t, b) for t in _N) for b in _B]
        _mk = lambda tag, v: checks.append(("블록 " + tag, v,
                                            v if v in text else "논문에 없음"))
        _mk("수", "**여덟 블록**" if len(_B) == 8 else "블록 %d개" % len(_B))
        _mk("평균 격차", "**−%.1f%%p**" % -_sb.mean(_g))
        _mk("최소 격차(논문)", "**−%.1f%%p**" % -max(_g))
        _mk("최대 격차", "−%.1f%%p" % -min(_g))
        checks.append(("블록 전부 음수", "%d/%d" % (len(_B), len(_B)),
                       "%d/%d" % (sum(x < 0 for x in _g), len(_B))))
        # 표 6 의 각 칸이 원자료와 맞는지 — 행을 통째로 만들어 본문에서 찾는다
        for _nm, _arm in (("경량", _L), ("네이티브", _N)):
            _v = [_sb.mean(_rt(t, b) for t in _arm) for b in _B]
            _row = "| %s | %s | %.1f%% |" % (
                _nm, " | ".join("%.1f%%" % x for x in _v), _sb.mean(_v))
            checks.append(("표6 %s 행" % _nm, _row,
                           _row if _row in text else "논문과 불일치"))
    except Exception as _e:
        _skip("시나리오 블록", _e)

    # §6.4 지면평면 σ 재측정 (2026-09-15) — 원자료에서 재계산
    try:
        import os                      # ★ 이 모듈은 os 를 import 하지 않는다 — 없으면
        import subprocess as _sp       #   NameError 가 except 에 먹혀 검사가 조용히 죽는다
        import re as _re2
        # ★ 상대 경로 + 슬래시를 그대로 주면 os.path.exists 는 True 인데
        #   CreateProcess 가 WinError 2 로 죽는다. 절대 경로로 정규화한다.
        _py = os.path.abspath(".venv/Scripts/python.exe")
        if not os.path.exists(_py):
            _py = os.path.abspath(".venv/bin/python")
        if os.path.exists(_py) and glob.glob("C:/carla/out/frame_*.json"):
            _o = _sp.run([_py, "bench/percept_v0.py", "C:/carla/out/frame_*.json"],
                         capture_output=True, text=True, encoding="utf-8", timeout=300).stdout
            _m = _re2.findall(r"(\d+)-(\d+)m: 평균([-+][\d.]+) σ([\d.]+)m", _o)
            if len(_m) == 3:
                for (lo, hi, mu, sd), exp_sd in zip(_m, ("1.10", "2.82", "5.10")):
                    checks.append(("지면평면 σ %s-%sm" % (lo, hi), exp_sd, "%.2f" % float(sd)))
    except Exception as _e:
        # ★ 선택 검사는 실패해도 전체를 막지 않지만, **조용히 사라지면 안 된다.**
        #   실제로 os 미import 로 이 블록이 통째로 죽어 있었는데 출력이 «전 항목 일치» 라
        #   알아채지 못했다. 건너뛴 사실과 이유를 반드시 찍는다.
        print("  (지면평면 σ 검사 건너뜀: %s: %s)" % (type(_e).__name__, _e))

    # 절 상호참조 무결성 — «§N 의 무엇무엇» 이 존재하지 않는 절을 가리키는 일이 있었다
    # (§6.4 가 «§7 의 관측 노이즈 주입 실험» 을 가리켰는데 §7 에 그런 내용이 없었다).
    # 참조가 실제 제목 번호로 풀리는지 기계적으로 확인한다.
    try:
        _have = set(re.findall(r"^#{2,3}\s+([0-9]+(?:\.[0-9]+)*)[.\s]", text, re.M))
        # 본문이 «별도 절을 두지 않았다» 고 명시한 번호는 예외로 둔다.
        _ok_missing = {"4.2", "4.6"}
        _bad = sorted({r for r in re.findall(r"§\s?([0-9]+(?:\.[0-9]+)?)", text)
                       if r not in _have and r not in _ok_missing})
        checks.append(("절 상호참조 무결", "없음", ", ".join(_bad) if _bad else "없음"))
    except Exception as _e:
        _skip("절 상호참조", _e)

    # 인용 경로·그림·표의 실재 확인 — 재현 지시가 낡으면 독자가 막힌다.
    try:
        import os as _os2
        _paths = sorted(set(re.findall(
            r"((?:tools|bench|ue|docs|figs|bench_results)/[A-Za-z0-9_./*-]+)", text)))
        # 본문이 «노트북» 자료라고 밝힌 경로는 이 장비에 없는 것이 정상이다.
        _laptop = {"bench_results/exp_boundary", "bench_results/exp_cascade"}
        _miss = [q for q in _paths if q not in _laptop
                 and not (glob.glob(q) if "*" in q else _os2.path.exists(q))]
        checks.append(("인용 경로 실재", "없음", ", ".join(_miss) if _miss else "없음"))

        _figs = sorted(set(re.findall(r"figs/([A-Za-z0-9_.-]+\.png)", text)))
        _fm = [f for f in _figs if not _os2.path.exists("figs/" + f)]
        checks.append(("그림 파일 실재", "없음", ", ".join(_fm) if _fm else "없음"))

        _def = set(re.findall(r"\*\*표 ([0-9]+)\.", text))
        _ref = set(re.findall(r"표 ([0-9]+)", text))
        _tm = sorted(_ref - _def)
        checks.append(("표 참조 무결", "없음", ", ".join(_tm) if _tm else "없음"))
    except Exception as _e:
        _skip("인용 실재", _e)

    # 한글 초록과 영문 초록의 **핵심 수치 일치** — 영문이 몇 주 뒤처져 있었다(2026-09-15:
    # 교차 검정 p=0.0079·검정력 0.19·시나리오 블록 -18.0 이 영문에 없었고, 대신 철회된
    # 틀에서 5분 우위를 «보정 안 됨» 으로만 끝내고 있었다). 국제 독자가 먼저 보는 자리다.
    try:
        _en = text[text.find("## Abstract"):]
        # ★ 맨숫자는 다른 양과 겹칠 수 있다(예: "18.0" 은 5분 우위 18.0pp 로도 나와
        #   블록 평균이 낡아도 통과한다). 겹칠 소지가 있는 것은 **단위까지** 붙여 적는다.
        _key = ("0.0079", "30.7", "0.227", "0.19", "35.9", "49.3", "62.0",
                "-19.7pp",                      # 블록 평균 격차 (구판 -18.0pp)
                # 2026-09-22 추가: 시드 10 보강과 배치 교락이 영문에 없었다
                "p = 0.020", "15.3%", "7.3%", "-19.8pp", "-9.1pp", "59%")
        _m = [k for k in _key if k not in _en]
        checks.append(("영문 초록 핵심 수치", "없음", ", ".join(_m) if _m else "없음"))
    except Exception as _e:
        _skip("영문 초록", _e)

    # 감시 표현 자기시험 — **한 번도 발동할 수 없는 감시**는 없는 것과 같다.
    # 오늘(2026-09-15) 검사 블록 하나가 조용히 죽어 있던 것을 찾았는데, 금지 표현도
    # 정규식이 틀리면 똑같이 «항상 통과» 가 된다. 각 패턴이 자기 표적을 실제로 잡는지,
    # 그리고 논문에 남아 있는 인용형은 잡지 않는지 확인한다.
    _SELFTEST = [
        (r'(?<!")실패가 충돌에서 이탈로 옮겨간다',
         "실패가 충돌에서 이탈로 옮겨간다는 것이 확인된다",
         '**"실패가 충돌에서 이탈로 옮겨간다"**고 서술했다'),
        (r'(?<!")MetaDrive 학습 분포가 경량 환경을 커버하지 못한다',
         "MetaDrive 학습 분포가 경량 환경을 커버하지 못한다.",
         '"MetaDrive 학습 분포가 경량 환경을 커버하지 못한다"는 해석을 철회'),
        (r"탐색 붕괴가 전이(를| 성능을)\s*(하강|떨어뜨|악화)",
         "탐색 붕괴가 전이를 하강시킨다", "이 인과(탐색 붕괴 → 전이 하강)를 주장했으나"),
        (r"(착취가 전이를 (파괴|무너)|과최적화 착취다)",
         "착취가 전이를 파괴한다", "구 '과최적화 착취' — 철회"),
        (r"이 하강은 노이즈가 아니다", "이 하강은 노이즈가 아니다", ""),
        (r"통계적 동률", "두 팔은 통계적 동률이다", ""),
        (r'(?<!")마스킹을 켜면 거버너가 \+13\.3pp 를 준다',
         "마스킹을 켜면 거버너가 +13.3pp 를 준다", '"마스킹을 켜면 거버너가 +13.3pp 를 준다"'),
    ]
    _st_bad = []
    for _pat, _pos, _neg in _SELFTEST:
        if not re.search(_pat, _pos):
            _st_bad.append("표적 미탐지: " + _pat[:34])
        elif _neg and re.search(_pat, _neg):
            _st_bad.append("인용형 오탐: " + _pat[:34])
    checks.append(("감시 표현 자기시험(%d개)" % len(_SELFTEST), "통과",
                   "통과" if not _st_bad else " / ".join(_st_bad)))

    NOT_CITED = ("피크 체크포인트", "이탈 종점(t3300)", "충돌 시작(t300)", "충돌 종점(t3300)")

    bad = 0
    # §7 배치 효과 (2026-09-17) — 「묶은 p=0.020 은 쓸 수 없다」의 근거.
    # 처리량 표 두 행과 배치별 격차가 근거 전부이므로 원자료에서 재계산해 본문과 맞춘다.
    try:
        import sys as _sys9
        _sys9.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        import statistics as _st9
        from batch_effect import BATCH as _BE, block_mean as _bm, msteps as _ms, welch as _we
        _mk6 = lambda tag, v: checks.append(("배치 " + tag, v,
                                             v if v in text else "논문에 없음"))
        for _arm in ("경량", "네이티브"):
            _a = [_ms(_arm, t) for t in _BE["8월"][_arm]]
            _b = [_ms(_arm, t) for t in _BE["9월"][_arm]]
            _mk6("처리량 %s 행" % _arm,
                 "| %s | %.2f ± %.2f | %.2f ± %.2f | **%+.1f%%** |"
                 % (_arm, _st9.mean(_a), _st9.stdev(_a), _st9.mean(_b), _st9.stdev(_b),
                    100 * (_st9.mean(_b) / _st9.mean(_a) - 1)))
        _g = {}
        for _bt in ("8월", "9월"):
            _L = [_bm(t) for t in _BE[_bt]["경량"]]
            _N = [_bm(t) for t in _BE[_bt]["네이티브"]]
            _d, _t9, _df9, _p9, _ci = _we(_L, _N)
            _g[_bt] = _d
            _mk6("%s 격차" % _bt,
                 ("**%s %+.1f%%p**(p=%.3f)" % (_bt, _d, _p9)).replace("-", chr(8722)))
        _mk6("상호작용", "**상호작용이 %+.1f%%p**" % (_g["9월"] - _g["8월"]))
        # 묶은 값도 본문과 맞는지 — 숨기지 않기로 했으므로 감시도 건다
        _LL = [_bm(t) for _bt in _BE for t in _BE[_bt]["경량"]]
        _NN = [_bm(t) for _bt in _BE for t in _BE[_bt]["네이티브"]]
        _d, _t9, _df9, _p9, _ci = _we(_LL, _NN)
        _mk6("묶은 값",
             ("격차 **%+.1f%%p**(Welch t=%.2f, df=%.1f, **p=%.3f**,"
              % (_d, abs(_t9), _df9, _p9)).replace("-", chr(8722)))
        # 스텝 정렬 8블록(§7) — 「처리량이 과반을 설명한다」의 근거 표 두 행.
        # 09-17 에 단일 블록판을 8블록판으로 갈아치웠다(결론이 뒤집혔다).
        from scipy import stats as _sps
        from step_aligned_analysis import measure as _sam, NAME as _SN
        _A, _F, _stp = _sam()
        for _tg in ("clean", "nd"):
            _pa = _sps.ttest_ind(_A[(_tg, "9월")], _A[(_tg, "8월")],
                                 equal_var=False).pvalue
            _pf = _sps.ttest_ind(_F[(_tg, "9월")], _F[(_tg, "8월")],
                                 equal_var=False).pvalue
            _df = _st9.mean(_F[(_tg, "9월")]) - _st9.mean(_F[(_tg, "8월")])
            _da = _st9.mean(_A[(_tg, "9월")]) - _st9.mean(_A[(_tg, "8월")])
            _bold = "**p=%.3f**" % _pf if _pf < 0.05 else "p=%.3f" % _pf
            _row = ("| %s | %+.1f%%p (%s) | %+.1f%%p (p=%.3f) | %s%.0f%%%s |"
                    % (_SN[_tg], _df, _bold, _da, _pa,
                       "**" if _tg == "clean" else "", 100 * (1 - _da / _df),
                       "**" if _tg == "clean" else ""))
            _mk6("스텝정렬 %s 행" % _SN[_tg], _row)
        # 상호작용도 정렬 전후로 건다 — 이 문단의 핵심 주장이다
        _gi = []
        for _D in (_F, _A):
            _gi.append((_st9.mean(_D[("clean", "9월")]) - _st9.mean(_D[("nd", "9월")]))
                       - (_st9.mean(_D[("clean", "8월")]) - _st9.mean(_D[("nd", "8월")])))
        _mk6("상호작용 정렬", "**%+.1f → %+.1f%%p**" % (_gi[0], _gi[1]))
    except Exception as _e:
        _skip("배치 효과", _e)

    # §2.5 분산 성분 (2026-09-16) — 「팔당 25 → 10시드」 주장의 근거.
    # 표의 네 값과, 방법 검산(논문 원래 표적에서 25시드가 재현되는가)까지 건다.
    try:
        import sys as _sys8
        _sys8.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from variance_components import table as _vt, decompose as _vd, ARMS as _VA
        from variance_components import seeds_for as _vs, ROOT as _VR, N_EP as _VN
        _bl = sorted({int(os.path.basename(_f).split("__b")[1][:-5])
                      for _f in glob.glob("%s/*.json" % _VR)})
        _mk5 = lambda tag, v: checks.append(("분산성분 " + tag, v,
                                             v if v in text else "논문에 없음"))
        _sds, _sd1 = [], []
        for _arm, _tags in _VA.items():
            _Y = _vt(_tags, _bl)
            _vp, _vb, _ve = _vd(_Y)
            _pr = _Y / 100.0
            _fl = float(np.mean(_pr * (1 - _pr)) / _VN) * 100.0 ** 2
            _mk5("표 %s 행" % _arm, "| %s | %.1f%%p | %.1f%%p | %.1f%%p | %.1f%%p |"
                 % (_arm, _vp ** 0.5, _vb ** 0.5, _ve ** 0.5, _fl ** 0.5))
            _sds.append((_vp ** 0.5, _ve ** 0.5))
            _sd1.append((float(np.mean([np.std(_Y[:, _q], ddof=1)
                                        for _q in range(_Y.shape[1])])), 0.0))
        # 몬테카를로라 ±1 시드는 흔들릴 수 있다 — 허용치를 두되 «논문과 같은 값» 을 요구한다.
        for _lab, _d, _s, _B, _exp in (("검산 25시드", 12.7, _sd1, 1, 26),
                                       ("12시드", 19.7, _sd1, 1, 12),
                                       ("10시드", 19.7, _sds, 8, 10)):
            _n = _vs(_d, _s, _B)[0]
            checks.append(("분산성분 " + _lab, "%d±1" % _exp,
                           "%d±1" % _exp if abs(_n - _exp) <= 1 else "%d (벗어남)" % _n))
        # ↑ 는 «계산이 기대와 맞는가» 만 본다. 논문 문장이 따로 흘러가는 것을 막으려면
        #   본문에 그 숫자가 실제로 적혀 있는지도 봐야 한다.
        _mk5("논문 12시드", "**팔당 12시드**")
        _mk5("논문 10시드", "**팔당 10시드**")
        _mk5("논문 26시드 검산", "26시드가 나와")
    except Exception as _e:
        _skip("분산 성분", _e)

    # §6.3 DPC 독립 재현 (2026-09-21) — 9월 배치 표 한 행. 원자료에서 다시 산출한다.
    # 서브프로세스로 부르는 이유: dpc_recompute 는 DPC_SRC 환경변수로 표본을 고르고
    # 텐서보드를 읽는다(본 프로세스에서 import 하면 기본값 표본이 캐시된다).
    try:
        import subprocess as _sp2
        _r2 = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        _o2 = _sp2.run(
            [os.path.abspath(os.path.join(_r2, ".venv/Scripts/python.exe")),
             os.path.abspath(os.path.join(_r2, "tools/dpc_recompute.py"))],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            env=dict(os.environ, PYTHONUTF8="1", DPC_SRC="sep"), cwd=_r2,
            timeout=600).stdout
        _m11 = re.search(r"전 구간 ([-+0-9.]+) \(순열 p=([0-9.]+)\)", _o2)
        _m12 = re.search(r"전반\(≤30분\) ([-+0-9.]+) \(p=([0-9.]+)\) \| "
                         r"후반\(>30분\) ([-+0-9.]+) \(p=([0-9.]+)\) \| Δτ=([-+0-9.]+)", _o2)
        if _m11 and _m12:
            _row2 = ("| **9월 (독립)** | **%s (p=%s)** | %s (p=%s) | %s (p=%s) | %s |"
                     % (_m11.group(1), _m11.group(2), _m12.group(1), _m12.group(2),
                        _m12.group(3), _m12.group(4), _m12.group(5)))
            _row2 = _row2.replace("-", chr(8722))
            checks.append(("DPC 9월 행", _row2,
                           _row2 if _row2 in text else "논문에 없음"))
        else:
            checks.append(("DPC 9월 행", "찾음", "dpc_recompute 출력 형식 불일치"))
    except Exception as _e:
        _skip("DPC 독립 재현", _e)

    # §6.3 DPC 신뢰도 (2026-09-16) — 「널이 측정 잡음의 산물이 아니다」의 근거.
    # 타깃 쪽은 여기서 다시 계산하고(1초), 소스 쪽은 텐서보드 로딩이 20초 넘어
    # 기록 파일과 대조한다. 기록이 낡았으면 **타깃 값이 어긋나** 발각된다.
    try:
        import sys as _sys7
        _sys7.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from dpc_reliability import measure_target as _mt
        _sb = [x[2] for x in _mt(300)]
        _sbm = sum(_sb) / len(_sb)
        # 몬테카를로라 정확히 같을 수 없다 — 허용오차 안이면 «일치» 로 만든다.
        _exp = "논문 0.482 ±0.02"
        checks.append(("DPC 타깃 신뢰도", _exp,
                       _exp if abs(_sbm - 0.482) < 0.02 else "%.3f (벗어남)" % _sbm))
        _mk4 = lambda tag, v: checks.append(("DPC " + tag, v,
                                             v if v in text else "논문에 없음"))
        _mk4("시드 범위", "(시드 범위 %.2f~%.2f)" % (min(_sb), max(_sb)))
        _rel = open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                                 "bench_results", "clean_perep", "reliability.txt"),
                    encoding="utf-8").read()
        # 기록 파일이 이번 계산과 같은 자료에서 나왔는지 — 타깃 평균으로 확인
        _m8 = re.search(r"평균\s+([0-9.]+)\s+([0-9.]+)\s+([0-9.]+)", _rel)
        _fresh = _m8 is not None and abs(float(_m8.group(3)) - _sbm) < 0.02
        checks.append(("DPC 기록 최신", "이번 계산과 일치",
                       "이번 계산과 일치" if _fresh else
                       "기록 %s 대 계산 %.3f — 낡았다"
                       % (_m8.group(3) if _m8 else "?", _sbm)))
        # 논문이 인용한 타깃 신뢰도도 기록과 대조한다. 기록의 최신성은 위에서 확인했으므로
        # 이 둘을 합치면 «계산 → 기록 → 논문» 사슬이 끊긴 곳이 반드시 걸린다.
        if _m8:
            _mk4("타깃 신뢰도(논문)", "보정 **%s**" % _m8.group(3))
        _m9 = re.search(r"시간 분할\(보수적\) 평균 ([0-9.]+)", _rel)
        _m10 = re.search(r"sqrt\(r_소스 × r_타깃\) = \*\*([0-9.]+)\*\*", _rel)
        if _m9:
            _mk4("소스 신뢰도(보수)", "**%s**" % _m9.group(1))
        if _m10:
            _mk4("감쇠 상한", "**%s**" % _m10.group(1))
    except Exception as _e:
        _skip("DPC 신뢰도", _e)

    # §7 (5) 급내 상관 실측 (2026-09-16) — 원자료에서 재계산해 본문과 대조.
    # 판정이 «가정한 ρ 격자» 에서 «실측 ρ» 로 바뀌었으므로, 이 수치가 근거의 전부다.
    try:
        import sys as _sys6
        _sys6.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        import subprocess
        from scenario_icc import measure as _icc_measure
        _tet, _ic, _cr, _rb, _np2 = _icc_measure()
        _mk3 = lambda tag, v: checks.append(("급내상관 " + tag, v,
                                             v if v in text else "논문에 없음"))
        _mk3("시드내 ρ_w", "**ρ_w=%.3f**" % (sum(_tet) / len(_tet)))
        _mk3("시드 범위", "(시드 범위 %.2f~%.2f)" % (min(_tet), max(_tet)))
        _mk3("시드간 ρ_b", "**ρ_b=%.3f**" % _cr)
        checks.append(("급내상관 구판 재현", "불일치 0", "불일치 %d" % _rb))
        # 방향 자체도 지킨다 — 시드 간이 시드 내보다 낮아야 «정책마다 다르다» 가 성립한다
        checks.append(("급내상관 ρ_b<ρ_w", "예",
                       "예" if _cr < sum(_tet) / len(_tet) else "아니오"))
        # oracle_bias.py 는 실측값을 **상수로** 들고 있다 — 재측정하면 어긋날 수 있으므로
        # 소스에서 읽어 대조한다. 이런 상수는 조용히 낡는 전형적인 자리다.
        _ob = open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "oracle_bias.py"), encoding="utf-8").read()
        _m6 = re.search(r"RHO_W, RHO_B = ([0-9.]+), ([0-9.]+)", _ob)
        checks.append(("급내상관 oracle_bias 상수",
                       "%.3f/%.3f" % (sum(_tet) / len(_tet), _cr),
                       "%.3f/%.3f" % (float(_m6.group(1)), float(_m6.group(2)))
                       if _m6 else "상수를 못 찾음"))
        # 실측 구조 널의 출력(60.5%[52.7,68.0], 편향 몫 73%)도 논문이 인용한다.
        # 몬테카를로지만 seed 0 고정이라 결정론이다 — 실제로 돌려서 대조한다.
        _root6 = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        _o6 = subprocess.run(
            [os.path.abspath(os.path.join(_root6, ".venv/Scripts/python.exe")),
             os.path.abspath(os.path.join(_root6, "tools/oracle_bias.py"))],
            capture_output=True, text=True, encoding="utf-8",
            env=dict(os.environ, PYTHONUTF8="1"), cwd=_root6, timeout=300).stdout
        _m7 = re.search(r"널 오라클 ([0-9.]+)%\s+95% 구간 \[([0-9.]+), ([0-9.]+)\]\s+편향 몫 [0-9.]+%p \(([0-9]+)%\)", _o6)
        if _m7:
            _mk3("널 오라클", "오라클 기대값은 %s%%[%s, %s]"
                 % (_m7.group(1), _m7.group(2), _m7.group(3)))
            _mk3("편향 몫", "편향 몫 %s%%" % _m7.group(4))
        else:
            checks.append(("급내상관 널 출력", "찾음", "oracle_bias 출력 형식 불일치"))
    except Exception as _e:
        _skip("급내 상관", _e)

    # §7 장면 난이도 (2026-09-16) — 원자료에서 재계산해 본문과 대조.
    # 주장이 «격차는 소수 장면이 아니라 분포 전체의 이동» 이므로 전멸 수와 상관이 근거다.
    try:
        import sys as _sys5
        _sys5.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from scenario_difficulty import load as _sd_load, kendall_tau_b as _sd_tau
        _dat = _sd_load()
        _sc = sorted({s for (_, s) in _dat})
        _su = {a: {s: sum(f == 3 for f in _dat.get((a, s), [])) for s in _sc}
               for a in ("경량", "네이티브")}
        _mk2 = lambda tag, v: checks.append(("난이도 " + tag, v,
                                             v if v in text else "논문에 없음"))
        _mk2("장면 수", "n=%d" % len(_sc))
        _mk2("양팔 전멸", "양 팔 전멸 %d장면"
             % sum(1 for s in _sc if _su["경량"][s] == 0 and _su["네이티브"][s] == 0))
        _mk2("경량 전멸", "경량만 전멸 %d장면(%.0f%%)"
             % (sum(1 for s in _sc if _su["경량"][s] == 0),
                100.0 * sum(1 for s in _sc if _su["경량"][s] == 0) / len(_sc)))
        _mk2("네이티브 전멸", "네이티브만 전멸 %d장면(%.0f%%)"
             % (sum(1 for s in _sc if _su["네이티브"][s] == 0),
                100.0 * sum(1 for s in _sc if _su["네이티브"][s] == 0) / len(_sc)))
        _tau = _sd_tau([_su["경량"][s] for s in _sc], [_su["네이티브"][s] for s in _sc])
        _mk2("팔 간 상관", "**+%.3f**" % _tau)
        for _nm in ("경량", "네이티브"):
            _fl = [f for (a, _), v in _dat.items() if a == _nm for f in v]
            _mk2("%s 실패구성" % _nm, "%.1f%%·이탈 %.1f%%"
                 % (100.0 * sum(f == 1 for f in _fl) / len(_fl),
                    100.0 * sum(f == 2 for f in _fl) / len(_fl)))
    except Exception as _e:
        _skip("장면 난이도", _e)

    # §5.2 마스킹 기제 분해 (2026-09-16) — 원자료에서 재계산해 논문 서술과 대조.
    # 이 항목의 주장은 «구제가 이탈에만 듣는다» 이므로, 세 비율과 전이표가 근거 전부다.
    try:
        import os as _os4
        _md = _os4.path.join(_os4.path.dirname(_os4.path.dirname(_os4.path.abspath(__file__))),
                             "bench_results", "mask_paired")
        _r = {}
        for _m in ("plain", "mask"):
            for _s in (1, 2):
                with open(_os4.path.join(_md, "eval_md__sup2%s_s%d.json" % (_m, _s)),
                          encoding="utf-8") as _f:
                    _r[(_m, _s)] = json.load(_f)[0]
        _avg = {m: [sum(_r[(m, s)][k] for s in (1, 2)) / 2.0
                    for k in ("success_rate", "crash_rate", "out_of_road_rate")]
                for m in ("plain", "mask")}

        def _pp(x):
            return "%.1f%%" % (100 * x)
        _inp = lambda tag, s: checks.append(("마스킹 " + tag, s,
                                             s if s in text else "논문에 없음"))
        _inp("무마스킹 평균", "| %s | %s | %s |" % tuple(_pp(x) for x in _avg["plain"]))
        _inp("마스킹 평균", "| %s | %s | %s |" % tuple(_pp(x) for x in _avg["mask"]))
        _d = [_avg["mask"][k] - _avg["plain"][k] for k in range(3)]
        # 논문은 식자용 마이너스(U+2212)를 쓴다 — ASCII 로 만들면 늘 «없음» 이 된다
        _inp("차이 행", ("| **%+.1f%%p** | **%+.1f%%p** | **%+.1f%%p** |"
                        % (100 * _d[0], 100 * _d[1], 100 * _d[2])).replace("-", chr(8722)))
        # 전이표·짝검정
        _T, _b, _c = {}, 0, 0
        for _s in (1, 2):
            _pe = {e["scenario"]: e for e in _r[("plain", _s)]["per_episode"]}
            _me = {e["scenario"]: e for e in _r[("mask", _s)]["per_episode"]}
            for _sc in sorted(set(_pe) & set(_me)):
                _k = (_pe[_sc]["flag"], _me[_sc]["flag"])
                _T[_k] = _T.get(_k, 0) + 1
                _b += int(_pe[_sc]["success"] and not _me[_sc]["success"])
                _c += int(_me[_sc]["success"] and not _pe[_sc]["success"])
        _out = sum(v for (a, _), v in _T.items() if a == 2)
        _cr = sum(v for (a, _), v in _T.items() if a == 1)
        _inp("이탈→성공", "이탈 %d건 중 **%d건(%.0f%%)**"
             % (_out, _T.get((2, 3), 0), 100.0 * _T.get((2, 3), 0) / _out))
        _inp("충돌→성공", "%d건 중 %d건(%.0f%%)"
             % (_cr, _T.get((1, 3), 0), 100.0 * _T.get((1, 3), 0) / _cr))
        _inp("잔존 충돌", "충돌이 %d건 남는다" % sum(v for (_, b2), v in _T.items() if b2 == 1))
        _inp("짝검정 불일치쌍", "성공→실패 %d 대 실패→성공 %d" % (_b, _c))
        # 재현: 구판 총계와 같은가 (결정론 평가가 깨지면 위 전부가 무의미하다)
        _old = {}
        for _m, _f2 in (("plain", "sup2"), ("mask", "sup2mask")):
            for _s in (1, 2):
                with open(_os4.path.join(_os4.path.dirname(_md), "support_fixed",
                                         "eval_md__%s_s%d.json" % (_f2, _s)),
                          encoding="utf-8") as _f:
                    _old[(_m, _s)] = json.load(_f)[0]["success_rate"]
        _same = all(abs(_old[k] - _r[k]["success_rate"]) < 1e-9 for k in _old)
        checks.append(("마스킹 구판 재현", "예", "예" if _same else "아니오"))
    except Exception as _e:
        _skip("마스킹 기제 분해", _e)

    # §8 (9) 인지 노이즈 사전 감도 (2026-09-16) — 원자료에서 재추출해 논문 서술과 대조.
    # 이 항목은 «실험을 안 했다» 가 아니라 «재학습 전에 재어 보니 설계가 성립하지 않는다»
    # 라는 주장이므로, 근거 수치가 논문과 어긋나면 주장 자체가 무너진다.
    try:
        import os as _os3
        _rp = _os3.path.join(_os3.path.dirname(_os3.path.dirname(_os3.path.abspath(__file__))),
                             "bench_results", "noise_sensitivity", "result.txt")
        _rt = open(_rp, encoding="utf-8").read()
        _occ = re.search(r"비율 평균 ([0-9.]+)%", _rt).group(1)
        _y1 = re.search(r"잣대 1.*?조향 ([0-9.]+)", _rt).group(1)
        _y2 = re.search(r"잣대 2.*?조향 ([0-9.]+)", _rt).group(1)
        _s1 = re.search(r"^  1\.0\s+([0-9.]+)\s+([0-9.]+)\s+([0-9.]+) \|", _rt, re.M)
        _z0 = re.search(r"0 \(무주입\)\s+([0-9.]+)%", _rt).group(1)
        _z1 = re.search(r"^  1\.0\s+([0-9.]+)%\s+([-+0-9.]+)\s+([0-9.]+)\s*$", _rt, re.M)
        _sw = re.search(r"^  t000300\s+[0-9.]+\s+([0-9.]+)\s+([0-9.]+)", _rt, re.M)
        # ★ 하드코딩 상수와 비교하면 원자료 변화만 잡고 **논문 표류는 못 잡는다.**
        #   원자료에서 뽑은 값이 PAPER 본문에 실제로 적혀 있는지를 본다 — 어느 쪽이
        #   움직여도 걸린다.
        def _inpaper(tag, s):
            checks.append(("노이즈 " + tag, s, s if s in text else "논문에 없음"))
        _inpaper("|Δ조향|(배율1)", _s1.group(1))
        _inpaper("÷탐색σ(배율1)", "**%s배**" % _s1.group(2))
        _inpaper("탐색σ final", "exp(actor_logstd)=%.3f" % float(_y1))
        _inpaper("스텝간 조향", "(%.3f)" % float(_y2))
        _inpaper("학습초 비율·σ", "%s(t=300s, 탐색 σ=%.3f)" % (_sw.group(2), float(_sw.group(1))))
        _inpaper("성공률 무주입→배율1", "%s%% → %s%%" % (_z0, _z1.group(1)))
        _inpaper("Δ성공률 배율1", "Δ %s%%p" % _z1.group(2).replace("-", chr(8722)))
        _inpaper("순열 p 배율1", "p=%.2f" % float(_z1.group(3)))
        _inpaper("점유율(학습정책)", "슬롯은 %s%%" % _occ)   # 맨숫자는 표와 충돌해 무효였다
        # «경로를 바꿀 힘이 없었다» 가 성립한다.
        _ratios = [float(m) for m in re.findall(r"^  (?:t[0-9]+|final)\s+[0-9.]+\s+[0-9.]+\s+([0-9.]+)",
                                                _rt, re.M)]
        checks.append(("노이즈 비율 최대<1", "예",
                       "예" if _ratios and max(_ratios) < 1.0 else "아니오(%r)" % _ratios))
    except Exception as _e:
        _skip("노이즈 사전 감도", _e)

    # §8 (9) V 스윕 (2026-09-22) — 「V 상향은 탈락」의 근거 표 세 행.
    # 기록 파일과 대조한다(재측정은 환경 롤아웃이라 감시에 넣기엔 무겁다).
    try:
        _vp = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                           "bench_results", "noise_sensitivity", "vsweep.txt")
        _vt = open(_vp, encoding="utf-8").read()
        _blocks = _vt.split("############ V=")[1:]
        _mk7 = lambda tag, v: checks.append(("V스윕 " + tag, v,
                                             v if v in text else "논문에 없음"))
        for _b in _blocks:
            _v = _b.split(" ")[0]
            _occ = re.search(r"비율 평균 ([0-9.]+)%", _b).group(1)
            _rat = re.search(r"^  1\.0\s+[0-9.]+\s+([0-9.]+)", _b, re.M).group(1)
            _base = re.search(r"0 \(무주입\)\s+([0-9.]+)%", _b).group(1)
            _lab = "3 (학습 조건)" if _v == "3" else _v
            _bold = "**%s%%**" % _base if float(_base) < 50 else "%s%%" % _base
            _mk7("V=%s 행" % _v,
                 "| %s | %s%% | %s | %s |" % (_lab, _occ, _rat, _bold))
    except Exception as _e:
        _skip("V 스윕", _e)

    # 배치가 둘이 된 뒤로 «각 5시드» 는 더 이상 자명하지 않다 — 어느 배치인지 말해야
    # 한다. 헤드라인·그림 캡션이 가장 먼저 읽히는 자리이므로 거기부터 건다.
    for _tag, _need in (("**핵심 실증 결과**", "8월 배치"),
                        ("**그림 5.**", "8월 배치"),
                        ("**그림 1.**", "8월 배치")):
        _pos = text.find(_tag)
        if _pos < 0:
            checks.append(("배치 명시 " + _tag, "있음", "문구를 못 찾음"))
        else:
            _seg = text[_pos:_pos + 400]
            checks.append(("배치 명시 " + _tag, _need,
                           _need if _need in _seg else "배치 미명시"))

    for name, expected, actual in checks:
        ok = expected == actual
        bad += not ok
        print("  %-26s 논문 %-12s 원자료 %-12s %s" % (name, expected, actual, "OK" if ok else "불일치"))
        # 본문은 유니코드 마이너스(U+2212)를 쓰고 계산값은 ASCII 하이픈이라 그대로
        # 비교하면 멀쩡한 값이 «누락» 으로 찍힌다. 부호만 정규화해서 찾는다.
        _alt = expected.replace("-", "−")
        if ok and expected not in text and _alt not in text and name not in NOT_CITED:
            print("      ! 이 값이 PAPER.md 본문에서 발견되지 않는다 — 반영 누락 가능")

    # 본문에 남아 있으면 안 되는 표현
    for pat, why in ((r"통계적 동률", "정정 후 동률이 아니다"),
                     (r"statistically on par", "영문 초록의 동률 주장"),
                     (r"성능 손실 없이", "처리량이 성능으로 무손실 환산된다는 주장"),
                     (r"이 하강은 노이즈가 아니다", "n=5 에서 철회됐다"),
                     (r"4배 (이상|넘게) 과장", "격차 기준 과장 배수는 3.56 이다"),
                     (r"신뢰 창 구조는 정정 후에도 실재", "n=5 에서 철회됐다"),
                     (r"28x as realized", "실현 배수는 34.7배 (동일 장비 정숙)"),
                     (r"statistically on par", "영문 초록의 동률 주장"),
                     (r"동일 하드웨어·동일 시간 예산", "헤드라인 비교는 장비 교차다"),
                     (r"carla_policy_ab\.sh", "스윕 스크립트 이름은 carla_seed_sweep.sh"),
                     (r"rejection of three\s+remedies", "세 처방 중 둘만 기각됐다"),
                     # 아래는 2026-09-02 심사 시뮬레이션에서 철회한 주장들.
                     # 인용 형태(«…» 안)로 남기는 것은 허용하되 단정형은 금지한다.
                     (r"n 을 더 늘려도 이 격차는 유의해지지 않을",
                      "사후 검정력 역추론 — 실제 사전 검정력은 0.19 다"),
                     (r"대응 설계는 순위 비교에 유리하므로", "상관의 정밀도는 정책 수 9 가 지배한다"),
                     (r"\*\*두 시험장의 순위 상관은 0 이다\*\*", "n=9 의 95% 구간은 [−0.67, +0.66] 다"),
                     (r"\*\*실패율이 경로 최소 반경을 따라간다\*\*",
                      "좌회전 14.9m 가 직진 33.1m 보다 덜 실패한다 — 단조가 아니다"),
                     (r"거버너가 겨우 버티는 구간이 우회전이다",
                      "좌회전이 0.83g 로 더 높은데 더 잘 간다 — 이 설명은 철회됐다"),
                     (r"좌회전은 아홉 정책 모두[\s\S]{0,3}2~3/3", "실제 범위는 1~3/3 이며 검출력 부재다"),
                     # 2026-09-15 보강: 논문이 «철회» 라고 적어 둔 주장 중 감시가 없던 넷.
                     # 모두 현재는 인용부호 안에만 있으므로 «따옴표 앞» 을 제외해 단정형만 잡는다.
                     (r'(?<!")실패가 충돌에서 이탈로 옮겨간다',
                      "n=5 에서 부호가 갈려 철회됐다(§6.2)"),
                     (r'(?<!")MetaDrive 학습 분포가 경량 환경을 커버하지 못한다',
                      "규약 불일치의 증거일 뿐이라 해석을 철회했다(§6.2)"),
                     (r'탐색 붕괴가 전이(를| 성능을)\s*(하강|떨어뜨|악화)',
                      "전이 하강 자체가 n=5 에서 사라져 인과 주장을 철회했다(§6.3)"),
                     (r'(착취가 전이를 (파괴|무너)|과최적화 착취다)',
                      "착취 해석은 부호 오류의 산물로 철회됐다(§4.7·§6.3)"),
                     (r'(?<!")마스킹을 켜면 거버너가 \+13\.3pp 를 준다',
                      "앵커 대응 검정에서 p=0.25 — 유지하지 않는다")):
        for m in re.finditer(pat, text):
            line = text[:m.start()].count(chr(10)) + 1
            print("  잔존 표현 %-18s (L%d) — %s" % (pat, line, why)); bad += 1
    # 「팔당 25시드」가 정정 없이 쓰이지 않았는지 — §2.5 에서 10시드로 재계산했으므로,
    # 맨숫자로 남아 있으면 그 절만 읽는 독자가 낡은 값을 가져간다. 문맥 400자 안에
    # 재계산 또는 배치 경고가 있어야 한다.
    for _m13 in re.finditer(r"팔당 25시드", text):
        _ctx = text[max(0, _m13.start() - 200):_m13.end() + 400]
        if not any(_w in _ctx for _w in ("10시드", "재계산", "배치")):
            _ln = text[:_m13.start()].count(chr(10)) + 1
            print("  정정 없는 «팔당 25시드» (L%d) — §2.5 에서 10시드로 재계산했다" % _ln)
            bad += 1

    # 묶은 p=0.020 이 **라벨 없이** 쓰이지 않았는지. 이 값은 사전 등록한 주 지표의
    # 값이라 논문에 싣지만, 두 배치의 처리량이 달라 헤드라인으로 쓸 수 없다(§7).
    # 나중에 이 절만 보고 「유의하다」로 인용하는 것이 가장 그럴듯한 사고다.
    for _m14 in re.finditer(r"p\s*=\s*0\.020", text):
        _ctx = text[max(0, _m14.start() - 400):_m14.end() + 400]
        if not any(_w in _ctx for _w in ("쓸 수 없", "교환 가능하지 않",
                                         "do not use", "not exchangeable")):
            _ln = text[:_m14.start()].count(chr(10)) + 1
            print("  라벨 없는 «p=0.020» (L%d) — 두 배치가 교환 가능하지 않다(§7)" % _ln)
            bad += 1

    # 09-17 에 하루 만에 철회한 주장 — 8블록으로 다시 재니 59%% 가 설명됐다.
    # 현재는 정정 노트 안 인용으로만 남아 있어야 한다.
    # ★ 첫 판은 앞 250자에 «정정/적었다/「» 가 있으면 통과시켰는데, 이 논문은 머리말이
    #   「정정 고지」로 시작해 **어디서든 통과**했다(음성 시험에서 발각). 인용부호 안인지를
    #   실제로 따진다 — 직전에 나온 괄호가 여는 쪽이면 인용 안이다.
    for _m15 in re.finditer(r"처리량 해석은 지지되지 않는다", text):
        _open = text.rfind("「", 0, _m15.start())
        _close = text.rfind("」", 0, _m15.start())
        if not (_open > _close):
            _ln = text[:_m15.start()].count(chr(10)) + 1
            print("  철회된 «처리량 해석은 지지되지 않는다» (L%d) — 59%% 가 설명된다" % _ln)
            bad += 1


    # 62.6배(경합 분모의 과대치)가 라벨 없이 쓰이지 않았는지 — 문맥 200자 안에 사유가 있어야 한다
    for m in re.finditer(r"62\.6", text):
        ctx = text[max(0, m.start() - 200):m.end() + 200]
        if not any(w in ctx for w in ("과대", "경합", "한때")):
            line = text[:m.start()].count(chr(10)) + 1
            print("  라벨 없는 62.6배 (L%d) — 경합 분모의 과대치다" % line)
            bad += 1


    print(("불일치 %d 건" % bad) if bad else "전 항목 일치")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
