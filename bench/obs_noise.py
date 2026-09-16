"""인지 오차를 경량 시뮬 관측에 주입한다 — PAPER §8 향후 연구 (9) 의 전제 장치.

**무엇을 주입하는가.** 경량 시뮬의 주변차 관측은 GT 상대위치다. 실제 시스템은 카메라
인지가 추정한 값을 쓰므로, 그 추정기의 오차를 관측에 넣어 학습시키면 전이가 개선되는지가
질문이다. 주입할 값은 §6.4 에서 **실측**했다(CARLA 500프레임 1,000건, 지면평면 접지선
추정의 잔차):

    거리 구간      평균오차      σ
    4~15 m       −0.13 m     1.10 m
    15~30 m      −0.55 m     2.82 m
    30~50 m      −1.72 m     5.10 m

두 가지가 중요하다. (1) **산포만이 아니라 편향도** 넣어야 한다 — 지면평면은 원거리에서
거리를 과소추정한다. (2) **거리에 따라 커진다** — 구판 σ(0.84/1.10/1.17)는 거리에 거의
무관했는데 그것은 «박스 중심 대 최근접 모서리» 정의 차이를 잰 값이라 무효였다.

**어디에 주입하는가.** 커널(numba/numpy/torch 3벌)을 건드리지 않고 **정규화된 관측을
되돌려** 미터 단위로 흔든 뒤 다시 정규화한다. 커널 3벌을 각각 고치면 서로 어긋날 위험이
있고(이 저장소에서 이미 겪은 종류의 사고), 관측 인코딩은 가역이라 되돌리는 편이 안전하다.

    obs[b+0] = clip01((fwd / DR + 1) / 2)   →   fwd = (2·obs − 1)·DR

주의: clip01 로 포화된 슬롯은 되돌릴 수 없으므로 건드리지 않는다. 빈 슬롯(전 4차원 0)도
제외한다 — 0 은 «차량 없음» 이라는 신호이지 «거리 −50 m» 가 아니다.

실행(자기검증): python bench/obs_noise.py
"""
import numpy as np

# §6.4 표 — (상한 m, 평균오차 m, σ m). 마지막 구간은 검출 반경까지 연장한다.
BANDS = ((15.0, -0.13, 1.10),
         (30.0, -0.55, 2.82),
         (1e9, -1.72, 5.10))
EGO_DIM, NAVI_DIM, OTHER_DIM, N_OTHERS = 9, 10, 4, 8
OTHER_BASE = EGO_DIM + NAVI_DIM          # 19
EPS = 1e-6


def band_stats(dist):
    """거리(m) 배열 → (편향, σ) 배열. 구간 경계에서 계단으로 바뀐다(측정 그대로)."""
    bias = np.zeros_like(dist)
    sd = np.zeros_like(dist)
    lo = 0.0
    for hi, b, s in BANDS:
        m = (dist >= lo) & (dist < hi)
        bias[m] = b
        sd[m] = s
        lo = hi
    return bias, sd


def inject(obs, rng, detect_radius=50.0, scale=1.0):
    """(E, 51) 정규화 관측의 주변차 **종방향** 성분에 인지 오차를 주입한다.

    scale 은 감도 분석용 배율(0 이면 무주입, 1 이면 실측값 그대로).
    원본을 바꾸지 않고 사본을 돌려준다.
    """
    out = np.array(obs, dtype=np.float32, copy=True)
    if scale == 0.0:
        return out
    for s in range(N_OTHERS):
        b = OTHER_BASE + s * OTHER_DIM
        sl = out[:, b:b + OTHER_DIM]
        occupied = np.any(sl != 0.0, axis=1)          # 빈 슬롯은 전 차원 0
        f_n = out[:, b + 0]
        l_n = out[:, b + 1]
        # 포화된 값은 되돌릴 수 없다 — 건드리지 않는다.
        ok = occupied & (f_n > EPS) & (f_n < 1.0 - EPS)
        if not np.any(ok):
            continue
        fwd = (2.0 * f_n[ok] - 1.0) * detect_radius
        lat = (2.0 * l_n[ok] - 1.0) * detect_radius
        rng_m = np.hypot(fwd, lat)                     # 추정기 오차는 «거리» 의 함수다
        bias, sd = band_stats(rng_m)
        noisy = fwd + scale * (bias + sd * rng.standard_normal(fwd.shape).astype(np.float32))
        out[np.where(ok)[0], b + 0] = np.clip(
            (noisy / detect_radius + 1.0) / 2.0, 0.0, 1.0).astype(np.float32)
    return out


def _selftest():
    """주입된 오차가 실측 분포를 재현하는지, 그리고 건드리면 안 되는 것을 안 건드리는지."""
    rng = np.random.default_rng(0)
    DR = 50.0
    n = 200000
    obs = np.zeros((n, 51), np.float32)
    # 슬롯 0 에 거리 2~45 m 의 정면 차량을 채운다(횡방향 0).
    true_fwd = rng.uniform(2.0, 45.0, n).astype(np.float32)
    obs[:, OTHER_BASE + 0] = (true_fwd / DR + 1.0) / 2.0
    obs[:, OTHER_BASE + 1] = 0.5                       # 횡 0
    obs[:, OTHER_BASE + 2] = 0.5
    obs[:, OTHER_BASE + 3] = 0.5
    out = inject(obs, rng, DR)
    got = (2.0 * out[:, OTHER_BASE + 0] - 1.0) * DR
    err = got - true_fwd
    print("주입 오차가 §6.4 실측을 재현하는가 (n=%d, 정면 차량)" % n)
    print("  %-10s %10s %10s | %10s %10s" % ("구간", "목표 평균", "실측 평균", "목표 σ", "실측 σ"))
    lo = 0.0
    okall = True
    for hi, b, s in BANDS:
        m = (true_fwd >= lo) & (true_fwd < min(hi, 45.0))
        if m.sum() < 100:
            lo = hi
            continue
        mu, sg = err[m].mean(), err[m].std()
        good = abs(mu - b) < 0.05 and abs(sg - s) < 0.06
        okall &= good
        print("  %-10s %10.2f %10.2f | %10.2f %10.2f  %s"
              % ("%g~%g m" % (lo, min(hi, 45.0)), b, mu, s, sg, "OK" if good else "**차이**"))
        lo = hi

    # 포화 클리핑이 얼마나 무는가 — 숨기지 말고 수치로 남긴다.
    #   주입 후 거리가 음수이거나 검출 반경을 넘으면 clip 이 분포를 깎는다.
    raw = true_fwd + band_stats(true_fwd)[0] + band_stats(true_fwd)[1] * rng.standard_normal(n)
    clipped = float(np.mean((raw < 0.0) | (raw > DR)))
    print("  포화 클리핑 비율 %.2f%% (거리<0 또는 >검출반경) — 이만큼은 분포가 깎인다"
          % (100 * clipped))

    # 건드리면 안 되는 것들
    empty = np.zeros((10, 51), np.float32)
    assert np.array_equal(inject(empty, rng, DR), empty), "빈 슬롯을 건드렸다"
    keep = np.zeros((5, 51), np.float32)
    keep[:, OTHER_BASE:OTHER_BASE + 4] = [0.5, 0.5, 0.5, 0.5]
    got2 = inject(keep, rng, DR)
    assert np.array_equal(got2[:, OTHER_BASE + 1:OTHER_BASE + 4],
                          keep[:, OTHER_BASE + 1:OTHER_BASE + 4]), "횡·속도 차원을 건드렸다"
    assert np.array_equal(got2[:, :OTHER_BASE], keep[:, :OTHER_BASE]), "ego·navi 를 건드렸다"
    z = inject(keep, rng, DR, scale=0.0)
    assert np.array_equal(z, keep), "scale=0 인데 관측이 바뀌었다"
    print("  빈 슬롯·횡/속도 차원·ego/navi 불변, scale=0 무주입 — 전부 확인")
    print("종합: %s" % ("통과" if okall else "**분포 불일치**"))
    return 0 if okall else 1


def _realtest(steps=300, envs=64, n_vehicles=3, seed=7):
    """**실제 환경 관측**에 대고 확인한다 — 합성 관측만으로는 두 가정이 검증되지 않는다:
    (a) «빈 슬롯은 전 차원 0» 이라는 점유 판정이 실제로 맞는가,
    (b) 포화되어 되돌릴 수 없는 슬롯이 실제로 얼마나 되는가.
    """
    import os
    import sys
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from env_numba import IntersectionEnv

    env = IntersectionEnv(envs, n_vehicles, seed=seed)
    rng = np.random.default_rng(0)
    occ = sat = tot = 0
    errs, dists = [], []
    obs = env.obs.copy()
    for _ in range(steps):
        for s in range(N_OTHERS):
            b = OTHER_BASE + s * OTHER_DIM
            o = np.any(obs[:, b:b + OTHER_DIM] != 0.0, axis=1)
            f = obs[:, b + 0]
            tot += envs
            occ += int(o.sum())
            sat += int((o & ((f <= EPS) | (f >= 1.0 - EPS))).sum())
        out = inject(obs, rng, 50.0)
        for s in range(N_OTHERS):
            b = OTHER_BASE + s * OTHER_DIM
            m = obs[:, b + 0] != out[:, b + 0]
            if m.any():
                d0 = (2 * obs[m, b + 0] - 1) * 50.0
                d1 = (2 * out[m, b + 0] - 1) * 50.0
                errs.append(d1 - d0)
                dists.append(np.hypot(d0, (2 * obs[m, b + 1] - 1) * 50.0))
        obs = env.step(rng.uniform(-1, 1, (envs, 2)).astype(np.float32))[0].copy()
    errs = np.concatenate(errs)
    dists = np.concatenate(dists)
    print("실제 관측 %d스텝 × %d환경 × %d슬롯 (V=%d)" % (steps, envs, N_OTHERS, n_vehicles))
    print("  슬롯 점유율 %.1f%% | 그중 포화(주입 불가) %.2f%%"
          % (100 * occ / tot, 100 * sat / max(occ, 1)))
    print("  → 점유율이 낮다는 것은 **주입이 관측의 작은 부분에만 닿는다**는 뜻이다.")
    print("    V=%d 에 슬롯 8개이므로 상한이 %.0f%% 이고, 검출 반경 밖이 대부분이다."
          % (n_vehicles, 100.0 * n_vehicles / N_OTHERS))
    print("    ★ 이 점유율은 **무작위 행동**으로 굴린 값이다. 학습된 정책으로 굴리면")
    print("      20.4%가 된다(bench/noise_sensitivity.py) — 정책은 도로를 따라 달려")
    print("      이웃 차량 곁에 머무르기 때문이다. 설계에 쓸 값은 후자다.")
    print("    실험을 설계할 때 개입의 세기를 이 비율과 함께 읽어야 한다.")
    print("  실제로 주입된 표본 %d건" % len(errs))
    for lo, hi in ((0, 15), (15, 30), (30, 50)):
        m = (dists >= lo) & (dists < hi)
        if m.sum() > 50:
            print("    %2d~%2d m: 평균 %+.2f σ %.2f (n=%d)"
                  % (lo, hi, errs[m].mean(), errs[m].std(), m.sum()))
    print("  (원거리 σ 가 목표보다 조금 작은 것은 검출 반경에서의 클리핑 때문이다.)")
    return 0


if __name__ == "__main__":
    import sys
    rc = _selftest()
    print()
    if "--real" in sys.argv:
        rc |= _realtest()
    else:
        print("실제 환경 검증은 --real 로 함께 돌린다.")
    sys.exit(rc)
