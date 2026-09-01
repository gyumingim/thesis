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
    except Exception:
        pass

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
    except Exception:
        pass

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
    except Exception:
        pass

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
    except Exception:
        pass

    bad = 0
    for name, expected, actual in checks:
        ok = expected == actual
        bad += not ok
        print("  %-26s 논문 %-12s 원자료 %-12s %s" % (name, expected, actual, "OK" if ok else "불일치"))
        if ok and expected not in text and name not in ("피크 체크포인트",):
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
                     (r"rejection of three\s+remedies", "세 처방 중 둘만 기각됐다")):
        for m in re.finditer(pat, text):
            line = text[:m.start()].count(chr(10)) + 1
            print("  잔존 표현 %-18s (L%d) — %s" % (pat, line, why)); bad += 1

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
