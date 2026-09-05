"""판정의 **실행 간 변동**을 재고, 그보다 작은 차이를 쫓지 않게 한다.

계기(2026-09-06): 생성기 기하를 한 글자도 바꾸지 않고 노면 재질만 교체했는데 소실점
판정이 7.0% → 10.8% 로 움직였다. 그 순간 «판정값의 변동이 내가 쫓는 효과와 비슷한
크기» 라는 의심이 생겼고, 같은 코드로 시드만 바꿔 3회 렌더해 확인했다.

결과는 그 의심이 옳았음을 보여준다 — 최대 과노출의 표준편차가 2.3%p 인데 판정 임계가
5% 다. 단일 실행의 통과/실패는 임계 근처에서 사실상 동전 던지기이고, **«4.85% 통과 →
5.11% 실패» 같은 비교는 아무 의미가 없었다.**

그래서 이 도구가 하는 일은 둘이다.
  (1) 여러 시드의 렌더를 받아 판정 지표별 평균과 표준편차를 낸다.
  (2) 표준편차가 임계까지의 여유보다 크면 **«단일 실행으로 판정 불가»** 를 표시한다.

실행: python ue/audit_noise.py C:/ue/noise_90000 C:/ue/noise_91000 C:/ue/noise_92000
"""
import contextlib
import importlib.util
import io
import os
import statistics
import sys

# 판정 임계 — render_audit 과 같은 값을 쓴다.
# 실사 교정 임계 (ue/real_baseline.py) — render_audit 과 같은 값·같은 통계량.
THRESH = {"소실점 공허 중앙": 6.1, "과노출 중앙": 10.9}


def load_audit():
    here = os.path.dirname(os.path.abspath(__file__))
    spec = importlib.util.spec_from_file_location(
        "render_audit", os.path.join(here, "render_audit.py"))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def main():
    roots = sys.argv[1:]
    if len(roots) < 2:
        print("두 개 이상의 렌더 디렉터리를 주어야 변동을 잴 수 있다.")
        return 2
    ra = load_audit()
    res = {}
    for r in roots:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            res[r] = ra.report(r)
        if not res[r]:
            print("렌더 없음:", r)
            return 2

    keys = ["하늘 B−R 맑음", "하늘 B−R 흐림", "노면 대비 맑음", "노면 대비 흐림",
            "소실점 공허 중앙", "소실점 공허 최대", "과노출 중앙", "최대 과노출"]
    print("실행 %d회의 판정 지표 변동" % len(roots))
    print("  %-16s %s | %8s %8s %8s" %
          ("지표", " ".join("%9s" % os.path.basename(r)[-5:] for r in roots),
           "평균", "표준편차", "임계여유"))
    for k in keys:
        v = [res[r][k] for r in roots]
        mu, sd = statistics.mean(v), statistics.stdev(v)
        th = THRESH.get(k)
        margin = abs(mu - th) if th is not None else float("nan")
        flag = ""
        if th is not None:
            flag = "  ← 단일 실행 판정 불가(σ ≥ 여유)" if sd >= margin else ""
        print("  %-16s %s | %8.3f %8.3f %8s%s" %
              (k, " ".join("%9.3f" % x for x in v), mu, sd,
               ("%.3f" % margin) if th is not None else "-", flag))

    print()
    print("  하늘 색 분리 (맑음 − 흐림; 양수여야 통과)")
    gaps = [res[r]["하늘 B−R 맑음"] - res[r]["하늘 B−R 흐림"] for r in roots]
    for r, g in zip(roots, gaps):
        print("    %-22s %+.3f  %s" % (os.path.basename(r), g, "통과" if g > 0 else "실패"))
    mu, sd = statistics.mean(gaps), statistics.stdev(gaps)
    n_fail = sum(g <= 0 for g in gaps)
    print("    평균 %+.3f · 표준편차 %.3f · %d/%d 실행에서 실패" % (mu, sd, n_fail, len(gaps)))
    if n_fail == len(gaps):
        # ★ 부호가 전부 같다고 «확립» 은 아니다. n=3 의 부호검정은 p=0.25 이고,
        #   평균/표준오차로 봐도 t=%.2f 수준이다. 방향은 일관되나 근거는 약하다 —
        #   더 강하게 말하려면 실행 수를 늘려야 한다.
        t = mu / (sd / len(gaps) ** 0.5) if sd else float("inf")
        print("    → 방향은 %d/%d 일관되나 **확립된 것은 아니다** "
              "(부호검정 p=%.2f, t=%.2f, n=%d)."
              % (len(gaps), len(gaps), 2.0 ** -(len(gaps) - 1), t, len(gaps)))
        print("       실행을 더 늘리기 전에는 «일관된 방향» 까지만 말한다.")
    elif n_fail == 0:
        print("    → 전 실행 통과.")
    else:
        print("    → 실행마다 갈린다. 단일 실행으로 판정하지 마라.")

    print()
    print("  읽는 법: 표준편차가 임계까지의 여유보다 크면 그 판정은 실행 하나로 가릴 수 없다.")
    print("  생성기를 고친 뒤 «좋아졌다/나빠졌다» 를 말하려면 그 차이가 위 표준편차보다")
    print("  커야 한다. 작으면 아무것도 말하지 않은 것이다.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
