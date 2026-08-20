"""논문 Figure 초안: wall-clock 학습 곡선 + 교차 평가 성공률.

입력: runs/*/events(TensorBoard), bench_results/eval_md__*.json
출력: figs/fig_learning_curves.png, fig_transfer.png
"""
import glob, json, os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from tensorboard.backend.event_processing.event_accumulator import EventAccumulator

os.makedirs("figs", exist_ok=True)

# ── 그림 1: in-domain 학습 곡선 (wall-clock 축) ──
fig, ax = plt.subplots(figsize=(7, 4.2), dpi=140)
runs = {
    "custom R2 (obs/geom)": "runs/*pilot3_custom*",
    "custom R3 (dynamics)": "runs/*pilot4_custom*",
    "custom R4+5 (rules)": "runs/*pilot6_custom*",
    "MetaDrive (12 env)": "runs/*pilot_md__1*",
}
for label, pat in runs.items():
    m = sorted(glob.glob(pat))
    if not m:
        continue
    ea = EventAccumulator(m[-1]); ea.Reload()
    try:
        sc = ea.Scalars("charts/episodic_return")
    except KeyError:
        continue
    t = np.array([x.wall_time for x in sc]); t -= t[0]
    v = np.array([x.value for x in sc])
    if len(v) > 200:                      # 이동평균
        k = len(v) // 200
        v = np.convolve(v, np.ones(k) / k, "valid"); t = t[:len(v)]
    ax.plot(t / 60, v, label=label, lw=1.4)
ax.set_xlabel("wall-clock (min)"); ax.set_ylabel("episodic return")
ax.set_title("In-domain learning curves (30-min budget each)")
ax.legend(fontsize=8); ax.grid(alpha=0.3)
fig.tight_layout(); fig.savefig("figs/fig_learning_curves.png")
print("fig_learning_curves.png 저장")

# ── 그림 2: 교차 평가(→MetaDrive) 성공률·이탈률 라운드별 ──
fig, ax = plt.subplots(figsize=(7, 4.2), dpi=140)
evals = sorted(glob.glob("bench_results/eval_md__pilot*_custom_s1.json"))
names = {"pilot6": "R5", "pilot5": "R4", "pilot4": "R3", "pilot3": "R2", "pilot2": "R1", "pilot_": "R0"}
xs, suc, oor, ret = [], [], [], []
for f in evals:
    rows = json.load(open(f))
    fin = [r for r in rows if r["ckpt"] == "final.pt"]
    if not fin:
        continue
    r = fin[0]
    key = next((k for k in names if k in f), f)
    xs.append(names.get(key, key)); suc.append(r["success_rate"]); oor.append(r["out_of_road_rate"]); ret.append(r["mean_return"])
x = np.arange(len(xs))
ax.bar(x - 0.2, suc, 0.35, label="success rate")
ax.bar(x + 0.2, oor, 0.35, label="out-of-road rate")
ax2 = ax.twinx(); ax2.plot(x, ret, "ko--", ms=4, label="mean return")
ax.set_xticks(x); ax.set_xticklabels(xs); ax.set_ylim(0, 1.05)
ax.set_ylabel("rate"); ax2.set_ylabel("mean return (raw)")
ax.set_title("Transfer to MetaDrive across alignment rounds")
ax.legend(loc="upper left", fontsize=8); ax.grid(alpha=0.3)
fig.tight_layout(); fig.savefig("figs/fig_transfer.png")
print("fig_transfer.png 저장 (라운드:", xs, ")")
