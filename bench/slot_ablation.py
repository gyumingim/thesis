"""주변차 관측을 **통째로 지우면** 어떻게 되는가 — §8 (9) 결론의 가장 강한 형태 시험.

§8 (9) 는 「이 과제·이 교통밀도에서 실제 인지 오차는 정책 행동을 바꾸지 못한다」로 닫혔다.
그 근거는 주입 섭동이 탐색 잡음 이하라는 것이었다. 그런데 그 진술에는 두 가지 다른
사정이 섞일 수 있다:

  (가) **과제가 주변차 상태를 거의 쓰지 않는다** — 그렇다면 오차가 무해한 것이 당연하고,
       「노이즈 주입」 실험은 이 과제에서 애초에 물을 것이 없다.
  (나) **쓰기는 쓰는데 실측 크기의 오차에는 강건하다** — 그렇다면 결론은 「이 정도
       오차로는」 이라는 단서가 붙고, 더 큰 오차나 다른 과제에서는 달라질 수 있다.

가르는 방법은 섭동이 아니라 **제거**다. 주변차 슬롯 8개를 전부 0 으로 만들면 정책은
「주변에 차가 없다」고 본다. 이것은 분포 밖이 아니다 — 빈 슬롯은 학습 중에도 흔하다.

세 조건을 같은 시드·같은 에피소드에서 비교한다:
  · 원본        : 그대로
  · 슬롯 제거   : 주변차 8슬롯 전부 0
  · 슬롯 무작위 : 점유 슬롯의 종·횡을 검출 반경 안 균등난수로 (정보 파괴, 점유는 유지)

제거해도 성능이 거의 그대로면 (가), 크게 떨어지면 (나)다.

실행: .venv/Scripts/python.exe bench/slot_ablation.py
"""
import argparse
import glob
import itertools
import os
import statistics as st
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import torch

from evaluate import load_agent, _act
from obs_noise import OTHER_BASE, OTHER_DIM, N_OTHERS


EGO_SLICE = slice(0, 9)
NAVI_SLICE = slice(9, 19)


def mutate(obs, mode, rng, ranges=None):
    if mode == "keep":
        return obs
    out = obs.copy()
    for s in range(N_OTHERS):
        b = OTHER_BASE + s * OTHER_DIM
        if mode == "zero":
            out[:, b:b + OTHER_DIM] = 0.0
        elif mode == "rand":
            occ = np.any(obs[:, b:b + OTHER_DIM] != 0.0, axis=1)
            n = int(occ.sum())
            if n:
                out[np.where(occ)[0], b + 0] = rng.random(n).astype(np.float32)
                out[np.where(occ)[0], b + 1] = rng.random(n).astype(np.float32)
    return out


def mutate_block(obs, sl, rng, ranges):
    """한 블록을 **관측된 범위 안** 균등난수로 — 지지집합은 지키고 정보만 파괴한다.

    ★ ego/navi 를 0 으로 만드는 것은 안 된다. 학습 중 ego 가 전부 0 인 적이 없으므로
      분포 밖 충격과 정보 제거가 섞인다(§5 가 말하는 바로 그 혼동). 차원별 최소~최대
      안에서 다시 뽑으면 주변분포는 유지되고 «정보» 만 사라진다.
    """
    out = obs.copy()
    lo, hi = ranges
    n = out.shape[0]
    cols = np.arange(sl.start, sl.stop)
    out[:, sl] = (lo[cols] + rng.random((n, len(cols))).astype(np.float32)
                  * (hi[cols] - lo[cols]))
    return out


def observed_ranges(n_vehicles, seed, envs=64, steps=300):
    """차원별 관측 범위(최소~최대) — «지지집합 안에서» 무작위화하기 위한 사전 조사."""
    from env_numba import IntersectionEnv
    env = IntersectionEnv(envs, n_vehicles, seed=seed)
    rng = np.random.default_rng(7)
    obs = env.obs.copy()
    lo = obs.min(0).copy()
    hi = obs.max(0).copy()
    for _ in range(steps):
        obs = env.step(rng.uniform(-1, 1, (envs, 2)).astype(np.float32))[0]
        lo = np.minimum(lo, obs.min(0))
        hi = np.maximum(hi, obs.max(0))
    return lo, hi


def run(agent, mean, std, device, episodes, envs, n_vehicles, seed, mode, ranges=None):
    from env_numba import IntersectionEnv
    E = min(envs, episodes)
    env = IntersectionEnv(E, n_vehicles, seed=seed)
    rng = np.random.default_rng(4242)
    obs = env.obs.copy()
    done = succ = crash = 0
    while done < episodes:
        if mode == "ego":
            fed = mutate_block(obs, EGO_SLICE, rng, ranges)
        elif mode == "navi":
            fed = mutate_block(obs, NAVI_SLICE, rng, ranges)
        else:
            fed = mutate(obs, mode, rng)
        o, r, tm, tr, fl = env.step(_act(agent, fed, mean, std, device))
        for e in np.nonzero(tm | tr)[0]:
            if done < episodes:
                done += 1
                succ += int(fl[e] == 3)
                crash += int(fl[e] == 1)
        obs = o.copy()
    return succ / done, crash / done


def sign_perm_p(d):
    d = np.asarray(d, float)
    obs = abs(d.mean())
    hit = sum(1 for s in itertools.product((1, -1), repeat=len(d))
              if abs((d * np.array(s)).mean()) >= obs - 1e-12)
    return hit / 2 ** len(d)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--episodes", type=int, default=256)
    ap.add_argument("--envs", type=int, default=64)
    ap.add_argument("--vehicles", type=int, default=3)
    ap.add_argument("--seeds", default="1,2,3,4,5")
    ap.add_argument("--arm", default="clean_custom")
    a = ap.parse_args()
    device = torch.device("cpu")
    MODES = ("keep", "zero", "rand", "navi", "ego")
    res = {m: [] for m in MODES}
    crashes = {m: [] for m in MODES}
    ranges = observed_ranges(a.vehicles, 3000)
    for s in [int(x) for x in a.seeds.split(",")]:
        d = sorted(glob.glob("runs/Intersection__%s__%d__*" % (a.arm, s)))
        if not d:
            continue
        ck = os.path.join(d[0], "ckpt", "final.pt")
        if not os.path.exists(ck):
            continue
        agent, mean, std, _ = load_agent(ck, device)
        for m in MODES:
            sr, cr = run(agent, mean, std, device, a.episodes, a.envs,
                         a.vehicles, 3000 + s, m, ranges)
            res[m].append(sr)
            crashes[m].append(cr)
        print("  시드 %d 완료" % s, flush=True)

    print("\n주변차 슬롯 제거·파괴 (V=%d, %d에피소드/시드, n=%d시드)"
          % (a.vehicles, a.episodes, len(res["keep"])))
    print("  %-12s %10s %10s %10s %10s"
          % ("조건", "성공률", "Δ(%p)", "충돌률", "부호순열 p"))
    base = np.array(res["keep"])
    for m, lab in (("keep", "원본"), ("zero", "슬롯 제거(전부 0)"),
                   ("rand", "슬롯 무작위"), ("navi", "navi 무작위"),
                   ("ego", "ego 무작위")):
        v = np.array(res[m])
        c = np.array(crashes[m])
        if m == "keep":
            print("  %-12s %9.1f%% %10s %9.1f%% %10s"
                  % (lab, 100 * v.mean(), "—", 100 * c.mean(), "—"))
        else:
            d = v - base
            print("  %-12s %9.1f%% %+10.1f %9.1f%% %10.4f"
                  % (lab, 100 * v.mean(), 100 * d.mean(), 100 * c.mean(),
                     sign_perm_p(d)))
    print("  시드별 원본 성공률: " + " ".join("%.0f%%" % (100 * x) for x in base))
    print("")
    dz = 100 * (np.array(res["zero"]) - base).mean()
    dr = 100 * (np.array(res["rand"]) - base).mean()
    dn = 100 * (np.array(res["navi"]) - base).mean()
    de = 100 * (np.array(res["ego"]) - base).mean()
    print("정책이 무엇을 읽는가 (클수록 의존이 크다)")
    for lab, d in (("ego (자기 상태)", de), ("navi (경로)", dn),
                   ("주변차 **점유**", dz), ("주변차 **위치값**", dr)):
        print("  %-18s %+7.1f%%p" % (lab, d))
    print("  → 주변차는 «있는가» 가 «어디에 있는가» 보다 %.0f배 중요하다."
          % (abs(dz) / max(abs(dr), 1e-9)))
    print("")
    print("읽을 때의 단서 셋:")
    print("  (1) 개입 크기가 서로 다르다 — ego 9차원·navi 10차원·주변차 32차원이다.")
    print("      «블록을 파괴했을 때의 피해» 순서이지 정규화된 중요도가 아니다.")
    print("  (2) 범위 안 무작위화는 **주변분포는 지키되 차원 간 상관을 깬다.** 잡음 주입")
    print("      보다 강한 개입이며, 그래서 상한으로만 읽어야 한다.")
    print("  (3) 범위는 무작위 행동으로 굴려 조사했다. 학습된 정책이 실제로 지나는")
    print("      영역보다 넓을 수 있고, 그만큼 개입이 과해진다.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
