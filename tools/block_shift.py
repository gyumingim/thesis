"""블록별 분포 이동 × 블록별 의존도 — **어긋남이 문제가 되는 곳은 어디인가**.

두 측정이 따로 있었다. (1) §5·§7 은 소스와 타깃의 관측 분포가 어긋난다는 것을 보였고,
(2) `bench/slot_ablation.py` 는 정책이 블록마다 얼마나 의존하는지를 쟀다
(ego −77.7 > navi −58.7 > 주변차 점유 −34.3 ≫ 위치값 −2.2%p).

둘을 곱해야 의미가 선다. **크게 어긋나지만 정책이 안 읽는 블록은 무해하고, 조금
어긋나도 정책이 의존하는 블록은 치명적이다.** 주변차 위치값이 전자의 후보다.

이동의 척도: 학습 때 동결한 정규화 통계(체크포인트의 obs_mean/obs_var)로 **타깃 관측을
표준화**해 |z| 를 본다. 이것이 정책이 실제로 겪는 이동이다(평가 경로가 같은 통계를 쓴다).

주의: 주변차 슬롯은 빈 슬롯이 0 으로 채워져 있어 |z| 가 «비어 있음» 에 끌려간다.
점유 슬롯만 따로 집계한다.

실행: .venv/Scripts/python.exe tools/block_shift.py
"""
import glob
import os
import sys

import numpy as np
import torch

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "bench"))

EGO = slice(0, 9)
NAVI = slice(9, 19)
OTHER_BASE, OTHER_DIM, N_OTHERS = 19, 4, 8
# ego/navi 차원 이름 — bench/env_numba.py 의 관측 채움 코드에서 가져왔다.
# 「ego 가 중요하다」를 「어느 칸이 어긋났다」로 내리려면 이름이 있어야 한다.
EGO_NAMES = ["0 좌측 가장자리까지", "1 우측 가장자리까지", "2 차선 대비 heading",
             "3 속도", "4 직전 조향", "5 직전 조향(중복)", "6 직전 가속",
             "7 heading 변화율", "8 차선중심 횡위치"]
NAVI_NAMES = ["%d navi" % i for i in range(10)]

# bench/slot_ablation.py 실측 (2026-09-23, V=3, 5시드)
DEPEND = {"ego": 77.7, "navi": 58.7, "주변차 점유": 34.3, "주변차 위치값": 2.2}


def collect_target(agent, mean, std, device, episodes, seed):
    """MetaDrive 롤아웃의 원시 관측을 모은다 — 정책이 실제로 방문하는 영역."""
    from evaluate import _act
    from md_env import MetaDriveGT
    env = MetaDriveGT(seed=seed, density=0.1, num_scenarios=episodes)
    obs_all = []
    for ep in range(episodes):
        o, _ = env.reset(seed=seed + ep)
        while True:
            obs_all.append(o.copy())
            a = _act(agent, o[None, :], mean, std, device)[0]
            o, r, tm, tr, info = env.step(a)
            if tm or tr:
                break
    env.close()
    return np.array(obs_all, dtype=np.float64)


def collect_source(agent, mean, std, device, n_vehicles, seed, envs=64, steps=300):
    """소스 관측 — **학습된 정책으로** 굴린다.

    ★ 첫 판은 무작위 행동으로 굴렸다가 타깃(정책 주행)과 비교하고 있었다. 무작위 행동은
      일찍 죽어 빈 상태에 오래 머물기 때문에 점유율을 과소평가한다(2026-09-16 에 같은
      함정을 obs_noise 에서 겪었다: 무작위 7.4% 대 정책 20.4%). 양쪽 다 정책 주행이어야
      «정책이 실제로 겪는 이동» 을 비교하는 것이 된다.
    """
    from env_numba import IntersectionEnv
    from evaluate import _act
    env = IntersectionEnv(envs, n_vehicles, seed=seed)
    obs = env.obs.copy()
    out = [obs.copy()]
    for _ in range(steps):
        obs = env.step(_act(agent, obs, mean, std, device))[0].copy()
        out.append(obs.copy())
    return np.concatenate(out).astype(np.float64)


def occupied_mask(O):
    """(N,51) → 슬롯별 점유 불리언 (N, 8)."""
    return np.stack([np.any(O[:, OTHER_BASE + s * OTHER_DIM:
                              OTHER_BASE + (s + 1) * OTHER_DIM] != 0.0, axis=1)
                     for s in range(N_OTHERS)], axis=1)


def main():
    from evaluate import load_agent
    device = torch.device("cpu")
    d = sorted(glob.glob(os.path.join(ROOT, "runs", "Intersection__clean_custom__1__*")))
    if not d:
        print("체크포인트를 찾지 못했다")
        return 2
    agent, mean, std, _ = load_agent(os.path.join(d[0], "ckpt", "final.pt"), device)
    tgt = collect_target(agent, mean, std, device, episodes=30, seed=500000)
    src = collect_source(agent, mean, std, device, 3, 3000)
    print("타깃(MetaDrive) 관측 %d스텝 · 소스(경량) 관측 %d스텝" % (len(tgt), len(src)))

    z = np.abs((tgt - mean) / std)
    occ_t = occupied_mask(tgt)
    occ_s = occupied_mask(src)

    def block_z(sl):
        return float(np.mean(z[:, sl]))

    slot_cols = [OTHER_BASE + s * OTHER_DIM + j
                 for s in range(N_OTHERS) for j in range(OTHER_DIM)]
    zz = z[:, slot_cols].reshape(len(z), N_OTHERS, OTHER_DIM)
    occ_z = float(np.mean(zz[occ_t])) if occ_t.any() else float("nan")

    print("")
    print("블록별 이동(|z|, 동결 통계 기준)과 의존도(파괴 시 성공률 하락)")
    print("  %-16s %10s %12s %12s" % ("블록", "평균 |z|", "의존 Δ(%p)", "이동×의존"))
    rows = [("ego", block_z(EGO), DEPEND["ego"]),
            ("navi", block_z(NAVI), DEPEND["navi"]),
            ("주변차(점유 슬롯)", occ_z, DEPEND["주변차 위치값"])]
    for name, zv, dep in rows:
        print("  %-16s %10.2f %12.1f %12.1f" % (name, zv, dep, zv * dep))
    print("")
    print("ego 차원별 이동 — 「어느 칸이 어긋났는가」")
    zc = z.mean(axis=0)
    order = np.argsort(-zc[EGO])
    for i in order:
        bar = "#" * int(round(zc[i] * 20))
        print("  %-22s %6.2f  %s" % (EGO_NAMES[i], zc[i], bar))
    print("  ※ 같은 블록 안에서도 칸마다 다르다. 위쪽 두세 칸이 ego 이동을 지배하면")
    print("    정합의 표적은 «ego» 가 아니라 **그 칸들**이다.")

    print("")
    print("점유율 — 「있는가」 채널 자체의 이동")
    print("  소스 %.1f%% · 타깃 %.1f%% (차이 %+.1f%%p, 의존 Δ %.1f%%p)"
          % (100 * occ_s.mean(), 100 * occ_t.mean(),
             100 * (occ_t.mean() - occ_s.mean()), DEPEND["주변차 점유"]))
    print("")
    print("읽는 법: |z| 가 커도 의존이 낮으면 무해하다. 주변차 **위치값**이 그 자리이며")
    print("  (의존 2.2%p), 반대로 ego·navi 는 조금만 어긋나도 크게 작용한다.")
    print("  ※ 이 표는 **상관이 아니라 곱**이다. 인과를 주장하지 않으며, 정합 노력을")
    print("    어디에 쓸지 고르는 **우선순위 눈금**으로만 쓴다.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
