"""병렬 시뮬레이션 격자 시각화 — "한 화면에서 N개 환경이 동시에 도는" 그림/애니메이션.

경량 시뮬(env_numba)의 대량 병렬성을 그대로 보여준다: 1,024개를 돌리면서 그중 N개를
격자로 그린다. 정책 체크포인트를 주면 그 정책이, 없으면 무작위 정책이 주행한다.
결과별 테두리색: 진행 중=회색, 성공=초록, 충돌=빨강, 이탈=주황.

사용:
  python bench/render_grid.py --envs 1024 --show 64 --steps 260 --out figs/grid_custom \
      --ckpt runs/Intersection__dt_custom__1__*/ckpt/final.pt --gif
"""
import argparse
import glob
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import env_numba as EN  # noqa: E402

FLAG_COLOR = {0: "#9aa0a6", 1: "#d93025", 2: "#e8710a", 3: "#188038", 4: "#5f6368"}
FLAG_NAME = {0: "진행", 1: "충돌", 2: "이탈", 3: "성공", 4: "시간초과"}


def act_fn(ckpt):
    """체크포인트가 있으면 결정론 정책, 없으면 무작위."""
    if not ckpt:
        return lambda obs: np.random.uniform(-1, 1, (len(obs), 2)).astype(np.float32), "무작위 정책"
    import torch
    from evaluate import _act, load_agent
    agent, mean, std, _ = load_agent(ckpt, "cpu")
    return (lambda obs: _act(agent, obs, mean, std, "cpu")), "학습 정책"


# 도로 폴리라인 (36 경로) — 좌표계가 원점 중심이 아니므로 waypoint 로부터 직접 구성
_ROUTES = [EN._WPS[r, :EN._NWP[r]] for r in range(len(EN._NWP))]
# 차선 점선은 직선 구간에만 (교차로 안에서 곡선 경로들이 뒤엉키는 것 방지)
def _straight(rt):
    d = rt[-1] - rt[0]
    n = np.linalg.norm(d)
    if n < 1:
        return False
    u = d / n
    dev = np.abs((rt - rt[0]) @ np.array([-u[1], u[0]]))
    return float(dev.max()) < 2.0
_LANES = [r for r in _ROUTES if _straight(r)]
CAR_L, CAR_W = 4.6, 2.0          # 차체 치수 (m) — spec 의 HALF_LEN*2 근사


def _car(ax, x, y, h, color, z=3, alpha=1.0):
    """차량을 진행 방향에 맞춘 사각형으로 그린다."""
    from matplotlib.patches import Polygon
    c, s_ = np.cos(h), np.sin(h)
    hl, hw = CAR_L / 2, CAR_W / 2
    pts = np.array([[hl, hw], [hl, -hw], [-hl, -hw], [-hl, hw]])
    R = np.array([[c, -s_], [s_, c]])
    ax.add_patch(Polygon(pts @ R.T + [x, y], closed=True, fc=color, ec="none",
                         zorder=z, alpha=alpha))


def draw(ax, env, e, trail=None, span=38.0):
    """환경 e 를 ego 추적 시점으로 그린다 (도로 + 궤적 + NPC + ego + 결과 테두리)."""
    from matplotlib.collections import LineCollection
    x, y, h = float(env.ego[e, 0]), float(env.ego[e, 1]), float(env.ego[e, 2])
    ax.add_collection(LineCollection(_ROUTES, colors="#aeb6c2", linewidths=11,
                                     zorder=0, capstyle="round"))
    ax.add_collection(LineCollection(_LANES, colors="#ffffff", linewidths=1.1,
                                     zorder=1, linestyles=(0, (5, 7)), alpha=0.8))
    if trail is not None and len(trail) > 1:
        tr = np.asarray(trail)
        ax.plot(tr[:, 0], tr[:, 1], color="#0b57d0", lw=2.0, alpha=0.7, zorder=2)
    npc = env.npc[e]
    live = np.abs(npc[:, 0]) + np.abs(npc[:, 1]) > 1e-3
    for k in np.nonzero(live)[0]:
        _car(ax, float(npc[k, 0]), float(npc[k, 1]), float(npc[k, 2]), "#374151", z=3)
    _car(ax, x, y, h, "#0b57d0", z=4)
    ax.scatter([x], [y], s=90, facecolors="none", edgecolors="#0b57d0", lw=1.2, alpha=0.5, zorder=4)
    ax.set_xlim(x - span, x + span); ax.set_ylim(y - span, y + span)
    ax.set_xticks([]); ax.set_yticks([]); ax.set_aspect("equal")
    ax.set_facecolor("#eef1f5")
    for sp in ax.spines.values():
        sp.set_color(FLAG_COLOR[int(env.flags[e])]); sp.set_linewidth(2.6)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--envs", type=int, default=1024, help="동시 실행 환경 수")
    ap.add_argument("--show", type=int, default=64, help="격자에 그릴 환경 수 (제곱수 권장)")
    ap.add_argument("--steps", type=int, default=260)
    ap.add_argument("--vehicles", type=int, default=3)
    ap.add_argument("--seed", type=int, default=500000)
    ap.add_argument("--ckpt", default="")
    ap.add_argument("--out", default="figs/grid_custom")
    ap.add_argument("--frames", type=int, default=6, help="필름스트립에 담을 시점 수")
    ap.add_argument("--gif", action="store_true")
    a = ap.parse_args()
    ck = sorted(glob.glob(a.ckpt))[0] if a.ckpt and glob.glob(a.ckpt) else ""
    policy, tag = act_fn(ck)

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib import font_manager
    try:
        font_manager.fontManager.addfont("C:/Windows/Fonts/malgun.ttf")
        plt.rcParams["font.family"] = "Malgun Gothic"
    except Exception:
        pass
    plt.rcParams["axes.unicode_minus"] = False

    env = EN.IntersectionEnv(a.envs, a.vehicles, seed=a.seed)
    obs = env.reset()
    side = int(np.sqrt(a.show))
    snap_at = set(np.linspace(10, a.steps - 1, a.frames).astype(int).tolist())
    shots, gif_frames = [], []
    os.makedirs(os.path.dirname(a.out) or ".", exist_ok=True)

    import time
    t0, done_counts = time.time(), np.zeros(5, int)
    trails = [[] for _ in range(a.show)]
    for t in range(a.steps):
        obs, *_ = env.step(policy(obs))
        for f in range(1, 5):
            done_counts[f] += int((env.flags == f).sum())
        for k in range(a.show):                       # 궤적 잔상(에피소드 종료 시 초기화)
            if env.flags[k] != 0 or env.t[k] <= 1:
                trails[k] = []
            trails[k].append((float(env.ego[k, 0]), float(env.ego[k, 1])))
            if len(trails[k]) > 90:
                trails[k].pop(0)
        if t in snap_at or (a.gif and t % 4 == 0):
            fig, axes = plt.subplots(side, side, figsize=(side * 1.5, side * 1.5))
            for k, ax in enumerate(np.array(axes).ravel()):
                draw(ax, env, k, trails[k])
            sps = int(a.envs * (t + 1) / max(time.time() - t0, 1e-6))
            tot = max(int(done_counts[1:].sum()), 1)
            done_txt = (f"누적 종료 {done_counts[1:].sum():,}건 중 "
                        f"성공 {done_counts[3] / tot:.0%} · 충돌 {done_counts[1] / tot:.0%} · "
                        f"이탈 {done_counts[2] / tot:.0%}")
            head = f"경량 시뮬 {a.envs:,}개 환경 동시 실행 · {tag} · t={t}"
            fig.suptitle(head + chr(10) + done_txt, fontsize=11, y=0.995)
            fig.tight_layout(rect=(0, 0, 1, 0.955))
            fig.canvas.draw()
            fig.set_dpi(150)
            fig.canvas.draw()
            arr = np.asarray(fig.canvas.buffer_rgba())[..., :3].copy()
            if t in snap_at:
                shots.append((t, arr))
            if a.gif:
                gif_frames.append(arr)
            plt.close(fig)

    from PIL import Image
    if shots:
        Image.fromarray(shots[-1][1]).save(a.out + ".png")
        print("저장:", a.out + ".png")
        strip = [Image.fromarray(s).resize((520, 520)) for _, s in shots[:4]]
        sheet = Image.new("RGB", (520 * len(strip) + 8 * (len(strip) - 1), 520), (255, 255, 255))
        for j, im in enumerate(strip):
            sheet.paste(im, (j * 528, 0))
        sheet.save(a.out + "_strip.png")
        print("저장:", a.out + "_strip.png")
    if a.gif and gif_frames:
        ims = [Image.fromarray(f).resize((640, 640)) for f in gif_frames]
        ims[0].save(a.out + ".gif", save_all=True, append_images=ims[1:], duration=90, loop=0)
        print("저장:", a.out + ".gif", len(ims), "프레임")
    tot = done_counts.sum()
    if tot:
        print("종료 분포:", {FLAG_NAME[f]: f"{done_counts[f] / tot:.0%}" for f in (1, 2, 3, 4)})


if __name__ == "__main__":
    main()
