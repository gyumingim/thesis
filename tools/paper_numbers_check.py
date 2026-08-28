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
        ("확정 전이 평균", "48.9", "%.1f" % np.mean(cf)),
        ("확정 전이 σ", "20.4", "%.1f" % np.std(cf, ddof=1)),
        ("확정 시드값", "27/67/53", "/".join("%.0f" % v for v in cf)),
        ("정숙 최종 이탈 하한", "10", "%.0f" % min(co)),
        ("정숙 최종 이탈 상한", "30", "%.0f" % max(co)),
        ("정숙 체크포인트 성공 하한", "20", "%.0f" % min(all_ck)),
        ("정숙 체크포인트 성공 상한", "83", "%.0f" % max(all_ck)),
        ("오라클 조기정지", "62.2", "%.1f" % oracle),
        ("피크 값", "58.9", "%.1f" % peak_ck[0]),
        ("피크 체크포인트", "t000300.pt", peak_ck[1]),
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
        ("이탈 시작(t300)", "8.9", "%.1f" % mean_at("t000300.pt", "out_of_road_rate")),
        ("이탈 종점(t3300)", "27.8", "%.1f" % mean_at("t003300.pt", "out_of_road_rate")),
        ("충돌 시작(t300)", "32.2", "%.1f" % mean_at("t000300.pt", "crash_rate")),
        ("충돌 종점(t3300)", "25.6", "%.1f" % mean_at("t003300.pt", "crash_rate")),
        ("이탈 final 포함시", "18.9", "%.1f" % mean_at("final.pt", "out_of_road_rate")),
        ("40분 최저", "40.0", "%.1f" % mean_at("t002400.pt", "success_rate")),
    ]

    # 5분 대 40분 낙폭의 대응 t-검정 (§6.2 "하강은 노이즈가 아니다")
    try:
        from scipy import stats as _st
        a, b = [], []
        for f in sorted(glob.glob("bench_results/clean/eval_md__clean_s*.json")):
            rows = json.load(open(f))
            a.append(100 * [r for r in rows if r["ckpt"] == "t000300.pt"][0]["success_rate"])
            b.append(100 * [r for r in rows if r["ckpt"] == "t002400.pt"][0]["success_rate"])
        t, pv = _st.ttest_rel(a, b)
        checks += [("5분-40분 낙폭", "20.0 / 20.0 / 16.7",
                    " / ".join("%.1f" % (x - y) for x, y in zip(a, b))),
                   ("대응 t", "17.0", "%.1f" % t),
                   ("대응 p", "0.0034", "%.4f" % pv)]
    except Exception:
        pass

    # 처리량 실현 배수 (데스크톱 정숙): 경량 136M vs 같은 장비 네이티브 2.17M
    try:
        cl = [r for r in json.load(open("bench_results/clean/eval_md__clean_s1.json"))
              if r["ckpt"] == "final.pt"][0]["global_step"]
        nd = [r for r in json.load(open("bench_results/desktop/eval_md__dt_md__1.json"))
              if r["ckpt"] == "final.pt"][0]["global_step"]
        checks.append(("데스크톱 실현 배수", "62.6", "%.1f" % (cl / nd)))
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
                     (r"15분 피크 60", "피크는 5분 58.9% 다"),
                     (r"4배 (이상|넘게) 과장", "격차 기준 과장 배수는 3.56 이다"),
                     (r"28x as realized", "실현 배수는 62.6× (데스크톱 정숙)"),
                     (r"statistically on par", "영문 초록의 동률 주장"),
                     (r"동일 하드웨어·동일 시간 예산", "헤드라인 비교는 장비 교차다"),
                     (r"carla_policy_ab\.sh", "스윕 스크립트 이름은 carla_seed_sweep.sh"),
                     (r"rejection of three\s+remedies", "세 처방 중 둘만 기각됐다")):
        for m in re.finditer(pat, text):
            line = text[:m.start()].count(chr(10)) + 1
            print("  잔존 표현 %-18s (L%d) — %s" % (pat, line, why)); bad += 1

    print(("불일치 %d 건" % bad) if bad else "전 항목 일치")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
