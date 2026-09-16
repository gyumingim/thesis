"""인지 오차 주입이 **정책을 실제로 움직이는가** — 학습 승인 전에 재는 사전 감도.

§8 향후 연구 (9) 의 실험은 «인지 오차를 넣고 학습하면 전이가 개선되는가» 를 묻고,
답을 얻으려면 다중 시간의 재학습이 필요하다. 그 전에 **공짜로 답할 수 있는 선행 질문**이
있다: 주입이 정책의 행동을 바꾸기는 하는가. 바꾸지 못하면 어떤 결과가 나와도 해석이
서지 않는다 — 「노이즈가 무해했다」와 「개입이 닿지 않았다」가 구분되지 않기 때문이다.

이 우려는 근거가 있다. `obs_noise._realtest` 가 실제 관측에서 잰 **슬롯 점유율은 7.4%**다
(V=3, 슬롯 8개, 대부분 검출 반경 밖). 개입이 관측의 작은 부분에만 닿는다.

두 가지를 잰다. 재학습은 없고 보관된 final.pt 만 쓴다.

  (A) 행동 민감도 — 궤적은 **깨끗한 관측**으로 굴리고, 매 스텝 주입판 관측으로도 행동을
      한 번 더 계산해 |Δ행동| 을 잰다. 궤적이 배율 간 동일하므로 비교가 깨끗하다.
      잣대 둘을 나란히 둔다. (1) 정책 **자신의 탐색 표준편차** exp(actor_logstd) —
      학습 내내 이만큼의 행동 잡음을 겪으며 수렴했으므로, 그 아래라면 정책이 이미
      무시하도록 배운 크기다. (2) 같은 정책의 **스텝간 변화** |a_t - a_(t-1)|.

  (B) 제로샷 저하 — 주입된 관측을 정책이 **실제로 받아** 굴렸을 때 성공률이 떨어지는가.
      떨어지지 않으면 이 과제에서 종방향 거리 오차는 애초에 성능과 무관한 입력이다.

정숙 조건: UE·CARLA 와 동시에 돌리지 않는다.
실행: .venv/Scripts/python.exe bench/noise_sensitivity.py --episodes 128
"""
import argparse, glob, itertools, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import torch

from evaluate import load_agent, _act
from obs_noise import inject, OTHER_BASE, OTHER_DIM, N_OTHERS, EPS

SCALES = (0.5, 1.0, 2.0, 4.0)


def _occ_frac(obs):
    """주입 가능한(점유 & 비포화) 슬롯 비율 — 개입이 닿는 면적."""
    n = ok = 0
    for s in range(N_OTHERS):
        b = OTHER_BASE + s * OTHER_DIM
        o = np.any(obs[:, b:b + OTHER_DIM] != 0.0, axis=1)
        f = obs[:, b + 0]
        n += obs.shape[0]
        ok += int((o & (f > EPS) & (f < 1.0 - EPS)).sum())
    return ok, n


def sensitivity(agent, mean, std, device, steps, envs, n_vehicles, seed,
                scales=SCALES):
    """(A) 궤적은 깨끗하게, 행동만 두 번 계산."""
    from env_numba import IntersectionEnv
    env = IntersectionEnv(envs, n_vehicles, seed=seed)
    rng = np.random.default_rng(12345)
    obs = env.obs.copy()
    prev = None
    d = {s: [] for s in scales}
    step_delta = []
    occ = tot = 0
    for _ in range(steps):
        a = _act(agent, obs, mean, std, device)
        o_, n_ = _occ_frac(obs)
        occ += o_
        tot += n_
        for s in scales:
            a_n = _act(agent, inject(obs, rng, 50.0, scale=s), mean, std, device)
            d[s].append(np.abs(a_n - a))
        if prev is not None:
            step_delta.append(np.abs(a - prev))
        prev = a
        obs = env.step(a)[0].copy()
    out = {s: np.concatenate(d[s]).reshape(-1, 2) for s in scales}
    return out, np.concatenate(step_delta).reshape(-1, 2), occ / max(tot, 1)


def policy_std(agent):
    """정책이 학습 내내 겪은 행동 잡음의 크기 — «무시하도록 배운» 잣대."""
    with torch.no_grad():
        return torch.exp(agent.actor_logstd).cpu().numpy().reshape(-1)


def zero_shot(agent, mean, std, device, episodes, envs, n_vehicles, seed, scale):
    """(B) 주입된 관측을 정책이 실제로 받는다."""
    from env_numba import IntersectionEnv
    E = min(envs, episodes)
    env = IntersectionEnv(E, n_vehicles, seed=seed)
    rng = np.random.default_rng(777)
    obs = env.obs.copy()
    done = succ = 0
    while done < episodes:
        fed = obs if scale == 0.0 else inject(obs, rng, 50.0, scale=scale)
        o, r, tm, tr, fl = env.step(_act(agent, fed, mean, std, device))
        for e in np.nonzero(tm | tr)[0]:
            if done < episodes:
                done += 1
                succ += int(fl[e] == 3)
        obs = o.copy()
    return succ / done


def sign_perm_p(diffs):
    """짝지은 차이의 정확 부호순열 양측 p (n 작음 — 전수)."""
    d = np.asarray(diffs, float)
    n = len(d)
    obs = abs(d.mean())
    cnt = 0
    for signs in itertools.product((1, -1), repeat=n):
        if abs((d * np.array(signs)).mean()) >= obs - 1e-12:
            cnt += 1
    return cnt / 2 ** n


def sweep(args, device):
    """수렴 전에도 무감각했는가 — final.pt 하나로는 답할 수 없는 반론을 막는다.

    학습이 끝난 정책이 주입에 무감각하다는 것과, «학습 내내» 무감각했다는 것은 다르다.
    후자가 아니면 주입 학습이 초반에 경로를 바꿀 여지가 남는다. 체크포인트 시계열로 잰다.
    """
    print("\n(C) 체크포인트 시계열 — 배율 1.0 (실측값) 에서의 |Δ조향| ÷ 탐색표준편차")
    seeds = [int(x) for x in args.seeds.split(",")]
    tags, acc = None, {}
    for sd in seeds:
        dirs = sorted(glob.glob("runs/Intersection__%s__%d__*" % (args.arm, sd)))
        if not dirs:
            continue
        cks = sorted(glob.glob(os.path.join(dirs[0], "ckpt", "t*.pt")))
        cks.append(os.path.join(dirs[0], "ckpt", "final.pt"))
        names = [os.path.basename(c)[:-3] for c in cks]
        if tags is None:
            tags = names
        for c, nm in zip(cks, names):
            if not os.path.exists(c):
                continue
            ag, mn, st, _ = load_agent(c, device)
            dl, stp, _ = sensitivity(ag, mn, st, device, args.sweep_steps, args.envs,
                                     args.vehicles, seed=1000 + sd, scales=(1.0,))
            ps = policy_std(ag)
            acc.setdefault(nm, []).append((dl[1.0].mean(0)[0], ps[0], stp.mean(0)[0]))
        print("  시드 %d 완료" % sd, flush=True)
    print("  %-10s %10s %10s %8s %10s" % ("체크포인트", "|Δ조향|", "탐색σ", "비율", "스텝간"))
    for nm in (tags or []):
        v = acc.get(nm)
        if not v:
            continue
        a = np.array(v)
        print("  %-10s %10.4f %10.4f %8.2f %10.4f"
              % (nm, a[:, 0].mean(), a[:, 1].mean(),
                 a[:, 0].mean() / max(a[:, 1].mean(), 1e-9), a[:, 2].mean()))
    print("  비율이 학습 전 구간에서 1 을 넘지 않으면, 주입은 어느 시점에도 정책이")
    print("  겪는 행동 잡음보다 작았다 — 경로를 바꿀 힘이 없었다는 뜻이다.")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--episodes", type=int, default=128)
    ap.add_argument("--steps", type=int, default=200)
    ap.add_argument("--envs", type=int, default=64)
    ap.add_argument("--vehicles", type=int, default=3)
    ap.add_argument("--seeds", default="1,2,3,4,5")
    ap.add_argument("--arm", default="clean_custom")
    ap.add_argument("--sweep", action="store_true",
                    help="체크포인트 시계열로 민감도를 만든다 (C)")
    ap.add_argument("--sweep-steps", type=int, default=150)
    args = ap.parse_args()
    device = torch.device("cpu")

    rows_sens, rows_zs, occs = [], [], []
    for s in [int(x) for x in args.seeds.split(",")]:
        pat = "runs/Intersection__%s__%d__*" % (args.arm, s)
        dirs = sorted(glob.glob(pat))
        if not dirs:
            print("  시드 %d: 체크포인트 없음 (%s)" % (s, pat))
            continue
        ck = os.path.join(dirs[0], "ckpt", "final.pt")
        if not os.path.exists(ck):
            print("  시드 %d: final.pt 없음" % s)
            continue
        agent, mean, std, _ = load_agent(ck, device)
        dl, sd, occ = sensitivity(agent, mean, std, device, args.steps,
                                  args.envs, args.vehicles, seed=1000 + s)
        occs.append(occ)
        rows_sens.append((s, {k: v.mean(0) for k, v in dl.items()}, sd.mean(0),
                          policy_std(agent)))
        zs = {0.0: zero_shot(agent, mean, std, device, args.episodes, args.envs,
                             args.vehicles, 2000 + s, 0.0)}
        for sc in SCALES:
            zs[sc] = zero_shot(agent, mean, std, device, args.episodes, args.envs,
                               args.vehicles, 2000 + s, sc)
        rows_zs.append((s, zs))
        print("  시드 %d 완료 (점유·비포화 %.1f%%)" % (s, 100 * occ), flush=True)

    if not rows_sens:
        print("체크포인트를 하나도 찾지 못했다.")
        return 1

    print("\n(A) 행동 민감도 — 궤적은 깨끗한 관측, 행동만 두 번 계산 "
          "(%d스텝 × %d환경 × %d시드)" % (args.steps, args.envs, len(rows_sens)))
    print("  주입이 닿는 슬롯(점유·비포화) 비율 평균 %.1f%%" % (100 * np.mean(occs)))
    step = np.mean([r[2] for r in rows_sens], axis=0)
    pstd = np.mean([r[3] for r in rows_sens], axis=0)
    print("  잣대 1  정책 탐색 표준편차 exp(actor_logstd): 조향 %.4f  가속 %.4f"
          % (pstd[0], pstd[1]))
    print("  잣대 2  스텝간 행동 변화 |a_t - a_(t-1)|:     조향 %.4f  가속 %.4f"
          % (step[0], step[1]))
    print("  %-6s %10s %8s %8s | %10s %8s %8s"
          % ("배율", "|Δ조향|", "÷잣대1", "÷잣대2", "|Δ가속|", "÷잣대1", "÷잣대2"))
    for sc in SCALES:
        m = np.mean([r[1][sc] for r in rows_sens], axis=0)
        print("  %-6.1f %10.4f %8.2f %8.2f | %10.4f %8.2f %8.2f"
              % (sc, m[0], m[0] / max(pstd[0], 1e-9), m[0] / max(step[0], 1e-9),
                 m[1], m[1] / max(pstd[1], 1e-9), m[1] / max(step[1], 1e-9)))
    print("  잣대 1 보다 훨씬 작으면 정책이 학습 중 이미 무시하도록 배운 크기다.")

    print("\n(B) 제로샷 저하 — 주입된 관측을 정책이 실제로 받는다 (%d에피소드/시드)"
          % args.episodes)
    print("  %-8s %10s %10s %10s" % ("배율", "성공률", "Δ(%p)", "부호순열 p"))
    b = np.array([r[1][0.0] for r in rows_zs])
    print("  %-8s %9.1f%% %10s %10s" % ("0 (무주입)", 100 * b.mean(), "—", "—"))
    for sc in SCALES:
        v = np.array([r[1][sc] for r in rows_zs])
        d = v - b
        p = sign_perm_p(d) if len(d) >= 2 else float("nan")
        print("  %-8.1f %9.1f%% %+10.1f %10.4f" % (sc, 100 * v.mean(), 100 * d.mean(), p))
    print("  시드별 무주입 성공률: " + " ".join("%.0f%%" % (100 * x) for x in b))
    if args.sweep:
        sweep(args, device)
    return 0


if __name__ == "__main__":
    sys.exit(main())
