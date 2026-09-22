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


def mutate(obs, mode, rng):
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


def run(agent, mean, std, device, episodes, envs, n_vehicles, seed, mode):
    from env_numba import IntersectionEnv
    E = min(envs, episodes)
    env = IntersectionEnv(E, n_vehicles, seed=seed)
    rng = np.random.default_rng(4242)
    obs = env.obs.copy()
    done = succ = crash = 0
    while done < episodes:
        o, r, tm, tr, fl = env.step(_act(agent, mutate(obs, mode, rng), mean, std, device))
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
    res = {m: [] for m in ("keep", "zero", "rand")}
    crashes = {m: [] for m in ("keep", "zero", "rand")}
    for s in [int(x) for x in a.seeds.split(",")]:
        d = sorted(glob.glob("runs/Intersection__%s__%d__*" % (a.arm, s)))
        if not d:
            continue
        ck = os.path.join(d[0], "ckpt", "final.pt")
        if not os.path.exists(ck):
            continue
        agent, mean, std, _ = load_agent(ck, device)
        for m in ("keep", "zero", "rand"):
            sr, cr = run(agent, mean, std, device, a.episodes, a.envs,
                         a.vehicles, 3000 + s, m)
            res[m].append(sr)
            crashes[m].append(cr)
        print("  시드 %d 완료" % s, flush=True)

    print("\n주변차 슬롯 제거·파괴 (V=%d, %d에피소드/시드, n=%d시드)"
          % (a.vehicles, a.episodes, len(res["keep"])))
    print("  %-12s %10s %10s %10s %10s"
          % ("조건", "성공률", "Δ(%p)", "충돌률", "부호순열 p"))
    base = np.array(res["keep"])
    for m, lab in (("keep", "원본"), ("zero", "슬롯 제거(전부 0)"),
                   ("rand", "슬롯 무작위")):
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
    print("판정: 슬롯을 통째로 지웠을 때 %+.1f%%p." % dz)
    if abs(dz) < 5:
        print("  → **과제가 주변차 상태를 거의 쓰지 않는다**(위 (가)). 인지 오차가 무해한")
        print("    것은 당연하며, 이 과제에서 「노이즈 주입」은 물을 것이 없다.")
    else:
        print("  → 정책은 주변차 정보를 **실제로 쓴다**(위 (나)). 그렇다면 §8 (9) 의 결론은")
        print("    「이 정도 크기의 오차로는」 이라는 단서와 함께 읽어야 한다.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
