"""시나리오 난이도의 급내 상관 ρ 를 **실측**한다 — §7 (5) 오라클 편향 널의 가정 해소.

§7 (5) 는 「체크포인트 선택의 겉보기 이득(+15.4%p)은 대부분 평가 잡음」이라는 판정을
방어하면서, 체크포인트끼리 **같은 30 시나리오**를 본다는 사실 때문에 평가가 독립이
아님을 인정하고 ρ 를 **가정한 격자**(0 / 0.1 / … / 0.7)로 감도 분석했다. 그런데 ρ 는
잴 수 있는 값이다 — 장면별 성공/실패가 체크포인트 간에 얼마나 함께 움직이는지 세면 된다.

**잠재 프로빗 척도로 잰다.** `oracle_bias.py` 의 널이 잠재 정규 모형을 쓰므로, 이진
관측의 ANOVA ICC 가 아니라 **사분상관(tetrachoric)** 이 맞는 대응물이다. 체크포인트 쌍
(c, c′) 마다 30장면의 2×2 표를 만들고, 주변 확률을 고정한 채 이변량 정규의 상관 r 을
역산한다. 0 칸이 있으면 |r|=1 로 발산하므로 각 칸에 0.5 를 더한다(연속성 보정).

★ 비교용으로 이진 척도의 ANOVA ICC 도 함께 찍는다. 둘은 **다른 양**이다 — 이진 ICC 는
  잠재 상관보다 작게 나온다(이분화가 정보를 버린다). 널에 넣어야 하는 것은 잠재 쪽이다.

실행: .venv/Scripts/python.exe tools/scenario_icc.py
"""
import glob
import io
import json
import os
import sys

import numpy as np
from scipy import optimize, stats

ROOT = "bench_results/clean_perep"
OLD = "bench_results/clean"


def load_seed(path):
    rows = json.load(io.open(path, encoding="utf-8"))
    rows = [r for r in rows if "per_episode" in r]
    if not rows:
        return None, None
    scen = sorted({e["scenario"] for e in rows[0]["per_episode"]})
    Y = np.zeros((len(rows), len(scen)), dtype=float)
    for i, r in enumerate(rows):
        m = {e["scenario"]: e["success"] for e in r["per_episode"]}
        for j, s in enumerate(scen):
            Y[i, j] = m[s]
    return Y, [r["ckpt"] for r in rows]


def tetrachoric(a, b, c, d):
    """2×2 (both1, x1y0, x0y1, both0) → 사분상관. 각 칸에 0.5 를 더해 발산을 막는다."""
    a, b, c, d = a + 0.5, b + 0.5, c + 0.5, d + 0.5
    n = a + b + c + d
    p1 = (a + b) / n
    p2 = (a + c) / n
    p11 = a / n
    t1 = stats.norm.ppf(1.0 - p1)
    t2 = stats.norm.ppf(1.0 - p2)

    def f(r):
        return stats.multivariate_normal.cdf([-t1, -t2], mean=[0.0, 0.0],
                                             cov=[[1.0, r], [r, 1.0]]) - p11
    lo, hi = -0.995, 0.995
    if f(lo) * f(hi) > 0:
        return float("nan")
    return float(optimize.brentq(f, lo, hi, xtol=1e-6))


def anova_icc(Y):
    """이진 관측의 ANOVA 기반 ICC(1) — 장면이 군집, 체크포인트가 반복."""
    k, m = Y.shape                      # k 체크포인트 × m 장면
    grand = Y.mean()
    msb = k * np.mean((Y.mean(axis=0) - grand) ** 2) * m / (m - 1)
    msw = np.mean(np.var(Y, axis=0, ddof=1)) if k > 1 else 0.0
    return (msb - msw) / (msb + (k - 1) * msw) if (msb + (k - 1) * msw) else float("nan")


def measure():
    """(시드내 ρ 목록, 이진 ICC 목록, 시드간 ρ 평균, 재현 불일치 수) — 감시도 이걸 쓴다.

    출력 함수와 계산을 분리해 둔다. 감시(tools/paper_numbers_check.py)가 print 를 파싱하게
    두면 형식을 건드릴 때마다 감시가 조용히 죽는다.
    """
    fs = sorted(glob.glob(os.path.join(ROOT, "eval_md__clean_s*.json")))
    tet, icc, mats = [], [], []
    bad = 0
    for f in fs:
        o = os.path.join(OLD, os.path.basename(f))
        if os.path.exists(o):
            new = {r["ckpt"]: r["success_rate"]
                   for r in json.load(io.open(f, encoding="utf-8"))}
            old = {r["ckpt"]: r["success_rate"]
                   for r in json.load(io.open(o, encoding="utf-8"))}
            bad += sum(1 for c in old if abs(old[c] - new.get(c, -1)) > 1e-9)
        Y, _ = load_seed(f)
        if Y is None:
            continue
        mats.append(Y)
        rs = []
        for a in range(Y.shape[0]):
            for b in range(a + 1, Y.shape[0]):
                r = _tet_pair(Y[a], Y[b])
                if not np.isnan(r):
                    rs.append(r)
        tet.append(float(np.mean(rs)))
        icc.append(anova_icc(Y))
    cross = []
    for a in range(len(mats)):
        for b in range(a + 1, len(mats)):
            for i2 in range(mats[a].shape[0]):
                for j2 in range(mats[b].shape[0]):
                    r = _tet_pair(mats[a][i2], mats[b][j2])
                    if not np.isnan(r):
                        cross.append(r)
    return tet, icc, (float(np.mean(cross)) if cross else float("nan")), bad, len(cross)


def _tet_pair(x, y):
    return tetrachoric(float(np.sum((x == 1) & (y == 1))),
                       float(np.sum((x == 1) & (y == 0))),
                       float(np.sum((x == 0) & (y == 1))),
                       float(np.sum((x == 0) & (y == 0))))


def main():
    fs = sorted(glob.glob(os.path.join(ROOT, "eval_md__clean_s*.json")))
    if not fs:
        print("원자료 없음 — bash bench/run_ckpt_perep.sh 를 먼저 돌려라.")
        return 2

    print("재현 확인 — 새 평가가 구판(bench_results/clean)의 체크포인트별 성공률을 재현하는가")
    bad = 0
    for f in fs:
        tag = os.path.basename(f)
        o = os.path.join(OLD, tag)
        if not os.path.exists(o):
            print("  %s: 구판 없음" % tag)
            continue
        new = {r["ckpt"]: r["success_rate"] for r in json.load(io.open(f, encoding="utf-8"))}
        old = {r["ckpt"]: r["success_rate"] for r in json.load(io.open(o, encoding="utf-8"))}
        diff = [c for c in old if abs(old[c] - new.get(c, -1)) > 1e-9]
        bad += len(diff)
        print("  %-24s 체크포인트 %2d개 중 불일치 %d개%s"
              % (tag, len(old), len(diff), (" " + ",".join(diff)) if diff else ""))
    if bad:
        print("  ★ 결정론 평가가 재현되지 않았다. 아래 ρ 를 신뢰하지 마라.")

    print("\n급내 상관 ρ — 장면 난이도가 체크포인트 간에 얼마나 공유되는가")
    print("  %-8s %6s %6s %12s %12s" % ("시드", "ckpt", "장면", "사분상관 ρ", "이진 ICC"))
    tet_all, icc_all = [], []
    for f in fs:
        Y, names = load_seed(f)
        if Y is None:
            continue
        k, m = Y.shape
        rs = []
        for i in range(k):
            for j in range(i + 1, k):
                x, y = Y[i], Y[j]
                a = float(np.sum((x == 1) & (y == 1)))
                b = float(np.sum((x == 1) & (y == 0)))
                c = float(np.sum((x == 0) & (y == 1)))
                d = float(np.sum((x == 0) & (y == 0)))
                r = tetrachoric(a, b, c, d)
                if not np.isnan(r):
                    rs.append(r)
        tet = float(np.mean(rs))
        icc = anova_icc(Y)
        tet_all.append(tet)
        icc_all.append(icc)
        print("  %-8s %6d %6d %12.3f %12.3f"
              % (os.path.basename(f).split("__")[1][:-5], k, m, tet, icc))
    tm, im = float(np.mean(tet_all)), float(np.mean(icc_all))
    print("  %-8s %6s %6s %12.3f %12.3f" % ("평균", "", "", tm, im))
    print("  시드 간 범위: 사분상관 %.3f~%.3f, 이진 ICC %.3f~%.3f"
          % (min(tet_all), max(tet_all), min(icc_all), max(icc_all)))
    print("\n  → oracle_bias.py 의 ρ 격자에 **실측값 %.2f** 를 넣어 판정을 다시 읽으면 된다."
          % tm)
    print("  가정이던 것이 측정이 된다. (격자의 0.3 과 0.5 사이에 있는지부터 보라.)")

    # 널은 «모든 시드·체크포인트가 같은 장면 난이도 u 를 공유한다» 고 가정한다.
    # 그 가정의 강도도 잰다 — **다른 시드**의 체크포인트끼리도 같은 값이 나오는가.
    mats = [load_seed(f)[0] for f in fs]
    mats = [m for m in mats if m is not None]
    cross = []
    for a in range(len(mats)):
        for b in range(a + 1, len(mats)):
            for i2 in range(mats[a].shape[0]):
                for j2 in range(mats[b].shape[0]):
                    x, y = mats[a][i2], mats[b][j2]
                    r = tetrachoric(float(np.sum((x == 1) & (y == 1))),
                                    float(np.sum((x == 1) & (y == 0))),
                                    float(np.sum((x == 0) & (y == 1))),
                                    float(np.sum((x == 0) & (y == 0))))
                    if not np.isnan(r):
                        cross.append(r)
    cm = float(np.mean(cross))
    print("")
    print("  시드 내 쌍 ρ %.3f  대  **시드 간** 쌍 ρ %.3f (쌍 %d개)" % (tm, cm, len(cross)))
    print("  널은 전 시드·전 체크포인트가 같은 장면 난이도를 공유한다고 본다. 시드 간 ρ 가")
    print("  시드 내보다 뚜렷이 낮으면 그 가정이 과하다는 뜻이고, 널에 넣을 값은 낮은 쪽에")
    print("  가깝다 — 그만큼 **편향 몫은 커진다**(즉 판정은 더 안전해진다).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
