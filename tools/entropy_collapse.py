"""엔트로피 붕괴와 전이 하강의 동반 — §6.3 메커니즘의 정정판 재구성.

부호 오류판 위에서 §6.3 은 "소스 수익은 계속 오르는데 전이만 떨어진다"는 관측에서
과최적화-경계 착취를 주장했고, 그 전제가 아티팩트로 판명되며 절 전체가 철회됐다.
확정 정숙 조건의 학습 곡선을 다시 읽으면 전제부터 다르다 — **소스 수익도 함께 떨어진다.**

이 스크립트는 TensorBoard 이벤트에서 다섯 계열을 뽑아 시드별 Kendall τ 로 방향을 재고,
Fisher 로 결합한다. 확인 대상 가설은 "착취"가 아니라 **탐색 붕괴**다:
정책이 결정론에 가까워지면서(엔트로피 ↓) 주행선이 짧고 빨라지고(에피소드 길이 ↓),
소스에서는 미세한 손실에 그치지만 전이에서는 크게 손해 본다.

실행: python tools/entropy_collapse.py
"""
import glob
import sys

import numpy as np
from scipy import stats

TAGS = [
    ("losses/entropy", "정책 엔트로피"),
    ("charts/episodic_return", "소스 수익"),
    ("charts/episodic_length", "에피소드 길이"),
    ("losses/approx_kl", "정책 갱신 크기"),
    ("losses/explained_variance", "가치함수 설명력"),
]
BIN = 300.0            # 5분 구간 평균 — 체크포인트 격자와 같게 맞춘다
SKIP_RAMP = 1          # 첫 구간(0~5분)은 초기 상승이라 추세에서 제외한다.
# ★ 이 제외가 결론을 바꾼다: 첫 구간을 포함하면 소스 수익이 "상승"으로 보이지만,
#   그것은 학습 시작 직후의 램프이지 후반 추세가 아니다. 램프를 뺀 5~60분 구간에서는
#   소스 수익이 완만히 **감소**한다. 제외 여부를 밝히지 않으면 부호가 뒤집힌다.


def completed(run_dir):
    """1시간 예산을 완주한 런만 쓴다 — 진행 중인 런을 섞으면 추세가 뒤집힌다."""
    import os
    return os.path.exists(os.path.join(run_dir, "ckpt", "final.pt"))


def binned(run_dir, tag, horizon=3600.0):
    from tensorboard.backend.event_processing import event_accumulator
    ea = event_accumulator.EventAccumulator(run_dir, size_guidance={"scalars": 0})
    ea.Reload()
    if tag not in ea.Tags()["scalars"]:
        return None
    ev = ea.Scalars(tag)
    t0 = ev[0].wall_time
    arr = np.array([(e.wall_time - t0, e.value) for e in ev])
    out = []
    for lo in np.arange(0, horizon, BIN):
        w = arr[(arr[:, 0] >= lo) & (arr[:, 0] < lo + BIN)]
        out.append(w[:, 1].mean() if len(w) else np.nan)
    return np.array(out)


def fisher(ps):
    chi = -2 * sum(np.log(max(p, 1e-12)) for p in ps)
    return chi, stats.chi2.sf(chi, 2 * len(ps))


def main():
    runs = sorted(glob.glob("runs/Intersection__clean_custom__*"))
    runs = [r for r in runs if completed(r) and binned(r, "losses/entropy") is not None]
    if not runs:
        print("학습 곡선 없음")
        return 2
    print("확정 정숙 조건 학습 곡선 — 5분 구간 평균, 초기 램프(0~5분) 제외, 완주 시드 %d개"
          % len(runs))
    print()
    for tag, label in TAGS:
        taus, ps, firsts, lasts = [], [], [], []
        for r in runs:
            b = binned(r, tag)
            if b is None or np.isnan(b).all():
                continue
            b = b[SKIP_RAMP:]
            ok = ~np.isnan(b)
            if ok.sum() < 4:
                continue
            t, p = stats.kendalltau(np.arange(len(b))[ok], b[ok])
            taus.append(t)
            ps.append(p)
            firsts.append(b[ok][0])
            lasts.append(b[ok][-1])
        if not taus:
            continue
        chi, pf = fisher(ps)
        same = len({np.sign(t) for t in taus}) == 1
        print("  %-14s τ=%s | 부호 일치 %s | Fisher p=%.4f"
              % (label, ", ".join("%+.2f" % t for t in taus), "예" if same else "아니오", pf))
        print("  %-14s 처음 %s → 끝 %s"
              % ("", ", ".join("%.2f" % v for v in firsts),
                 ", ".join("%.2f" % v for v in lasts)))
    print()
    # 엔트로피에서 조향 표준편차를 역산 (2차원 가우시안: H = 2(logstd + 0.5 log 2πe))
    ent = [binned(r, "losses/entropy") for r in runs]
    ent = [e for e in ent if e is not None and not np.isnan(e).any()]
    if ent:
        c = 0.5 * np.log(2 * np.pi * np.e)
        s0 = np.mean([np.exp(e[SKIP_RAMP] / 2 - c) for e in ent])
        s1 = np.mean([np.exp(e[-1] / 2 - c) for e in ent])
        print("  행동 표준편차(역산): %.3f → %.3f  (%.1f배 축소)" % (s0, s1, s0 / s1))
    print()
    print("  읽는 법: 엔트로피와 소스 수익이 **함께** 내려가면 '소스를 착취하며 타깃만")
    print("  잃는다'는 해석은 성립하지 않는다. 다만 이 학습 곡선의 변화가 전이로 번역되지도")
    print("  않는다 — n=5 에서 전이 곡선은 평탄하고(§6.2) 실패 모드 구성의 시간 추세도")
    print("  부호가 갈려 성립하지 않는다. 이 결과를 전이 하강의 원인으로 연결하지 말 것.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
