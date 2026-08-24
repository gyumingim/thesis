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
if ax.lines:                              # 데이터 0건이면 git 추적 그림을 빈 축으로 덮지 않는다
    fig.tight_layout(); fig.savefig("figs/fig_learning_curves.png")
    print("fig_learning_curves.png 저장")
else:
    print("[skip] fig_learning_curves: 파일럿 런 없음 (기존 그림 보존)")
plt.close(fig)

# ── 그림 2: 교차 평가(→MetaDrive) 성공률·이탈률 라운드별 ──
fig, ax = plt.subplots(figsize=(7, 4.2), dpi=140)
evals = sorted(glob.glob("bench_results/eval_md__pilot*_custom_s1.json"))
names = {"pilot7": "R6", "pilot6": "R5", "pilot5": "R4", "pilot4": "R3", "pilot3": "R2", "pilot2": "R1", "pilot_": "R0"}
xs, suc, oor, ret = [], [], [], []
for f in evals:
    rows = json.load(open(f))
    fin = [r for r in rows if r["ckpt"] == "final.pt"]
    if not fin:
        continue
    r = fin[0]
    key = next((k for k in names if k in f), f)
    xs.append(names.get(key, key)); suc.append(r["success_rate"]); oor.append(r["out_of_road_rate"]); ret.append(r["mean_return"])
order = np.argsort(xs)                    # R0..R6 순 정렬
xs = [xs[i] for i in order]; suc = [suc[i] for i in order]
oor = [oor[i] for i in order]; ret = [ret[i] for i in order]
x = np.arange(len(xs))
ax.bar(x - 0.2, suc, 0.35, label="success rate")
ax.bar(x + 0.2, oor, 0.35, label="out-of-road rate")
ax2 = ax.twinx(); ax2.plot(x, ret, "ko--", ms=4, label="mean return")
ax.set_xticks(x); ax.set_xticklabels(xs); ax.set_ylim(0, 1.05)
ax.set_ylabel("rate"); ax2.set_ylabel("mean return (raw)")
ax.set_title("Transfer to MetaDrive across alignment rounds")
ax.legend(loc="upper left", fontsize=8); ax.grid(alpha=0.3)
if xs:
    fig.tight_layout(); fig.savefig("figs/fig_transfer.png")
    print("fig_transfer.png 저장 (라운드:", xs, ")")
else:
    print("[skip] fig_transfer: 파일럿 평가 없음 (기존 그림 보존)")
plt.close(fig)

# ── 그림 3: 본판 — 전이 성공률 vs 벽시계 (시드 평균 ± 범위) ──
# MD s3은 워커 스톨로 final 이 벽시계 12,857s → 3,600s 초과 항목 제외 (PAPER 부록 A)
MAIN = {
    "MetaDrive (native)": "bench_results/main/eval_md__main_md__*.json",
    "lightweight V=3": "bench_results/main/eval_md__final_custom_s*.json",
}
grid = np.arange(300, 3601, 300)
fig, ax = plt.subplots(figsize=(7, 4.2), dpi=140)
for label, pat in MAIN.items():
    files = sorted(glob.glob(pat))
    if not files:
        print(f"[skip] {label}: 파일 없음 ({pat})")
        continue
    curves = []
    for f in files:
        rows = [r for r in json.load(open(f)) if r["elapsed_s"] <= 3660]
        rows.sort(key=lambda r: r["elapsed_s"])
        if len(rows) < 2:
            continue
        t = np.array([r["elapsed_s"] for r in rows])
        s = np.array([r["success_rate"] for r in rows])
        curves.append(np.interp(grid, t, s))
    if not curves:
        continue
    c = np.array(curves)
    m = c.mean(0)
    ax.plot(grid / 60, m, lw=1.8, label=f"{label} (n={len(curves)})")
    ax.fill_between(grid / 60, c.min(0), c.max(0), alpha=0.18)
ext = glob.glob("bench_results/main/eval_md__ext3h.json")
if ext:
    rows = sorted(json.load(open(ext[0])), key=lambda r: r["elapsed_s"])
    te = np.array([r["elapsed_s"] for r in rows])
    se = np.array([r["success_rate"] for r in rows])
    ax.plot(te / 60, se, lw=1.4, ls="--", label="lightweight V=3, 3h budget (n=1)")
ax.set_xlabel("wall-clock training time (min)")
ax.set_ylabel("success rate on MetaDrive (30 ep, deterministic)")
ax.set_title("Zero-shot transfer vs. wall-clock budget (same GPU)")
ax.set_ylim(0, 1.0); ax.legend(fontsize=9); ax.grid(alpha=0.3)
fig.tight_layout(); fig.savefig("figs/fig_main_transfer_curve.png")
print("fig_main_transfer_curve.png 저장")

# ── 그림 4: 본판 막대 — 최종(1h) 성공률, 시드 점 표시 ──
def _finals(pat, ckpt="final.pt"):
    out = []
    for f in sorted(glob.glob(pat)):
        rows = json.load(open(f))
        fin = [r for r in rows if r["ckpt"] == ckpt]
        if fin:
            out.append(fin[0]["success_rate"])
    return out

md = []
for f in sorted(glob.glob("bench_results/main/eval_md__main_md__*.json")):
    rows = json.load(open(f))
    fin = next((r for r in rows if r["ckpt"] == "final.pt"), None)
    if fin is None:                        # 반쪽 런/빈 JSON — 크래시 대신 건너뛴다
        print(f"[skip] {f}: final.pt 행 없음")
        continue
    if fin["elapsed_s"] > 3660:            # 워커 스톨 → 예산 3600s 이내 마지막 ckpt 로 대체 (부록 A)
        inb = [r for r in rows if r["elapsed_s"] <= 3660 and r["ckpt"] != "final.pt"]
        if not inb:
            print(f"[skip] {f}: 3660s 이내 ckpt 없음")
            continue
        fin = max(inb, key=lambda r: r["elapsed_s"])
    md.append(fin["success_rate"])
bars = [("MetaDrive\n(native)", md),
        ("V=2\n(defective)", _finals("bench_results/main/eval_md__main_custom__*.json")),
        ("V=2\n+mask", _finals("bench_results/main/evalmask_md__custom_s*.json")),
        ("V=3\n(fixed)", _finals("bench_results/main/eval_md__final_custom_s*.json"))]
fig, ax = plt.subplots(figsize=(6.4, 4.2), dpi=140)
for i, (name, vals) in enumerate(bars):
    if not vals:
        ax.text(i, 0.03, "[pending]", ha="center", fontsize=8, rotation=90)
        continue
    ax.bar(i, np.mean(vals), 0.6, alpha=0.85)
    ax.scatter([i] * len(vals), vals, c="k", s=14, zorder=3)
ax.set_xticks(range(len(bars))); ax.set_xticklabels([b[0] for b in bars], fontsize=9)
ax.set_ylabel("success rate on MetaDrive (final, 1h budget)")
ax.set_ylim(0, 1.0); ax.grid(alpha=0.3, axis="y")
ax.set_title("Main comparison: equal wall-clock, transfer to MetaDrive")
fig.tight_layout(); fig.savefig("figs/fig_main_bars.png")
print("fig_main_bars.png 저장:", {b[0].replace(chr(10), ' '): [round(v, 2) for v in b[1]] for b in bars})

# ── 그림 5: 예산확장 — V=3 을 3시간까지 (1h 본판 곡선 위에 연장점) ──
ext = sorted(glob.glob("bench_results/main/eval_md__ext3h.json"))
if ext:
    fig, ax = plt.subplots(figsize=(7, 4.2), dpi=140)
    # 본판 V=3 (1h, 3시드) 평균을 배경으로
    curves = []
    for f in sorted(glob.glob("bench_results/main/eval_md__final_custom_s*.json")):
        rows = sorted((r for r in json.load(open(f)) if r["elapsed_s"] <= 3660),
                      key=lambda r: r["elapsed_s"])
        if len(rows) >= 2:
            curves.append(np.interp(grid, [r["elapsed_s"] for r in rows],
                                    [r["success_rate"] for r in rows]))
    if curves:
        c = np.array(curves)
        ax.plot(grid / 60, c.mean(0), lw=1.6, label=f"V=3 1h (n={len(curves)})")
        ax.fill_between(grid / 60, c.min(0), c.max(0), alpha=0.15)
    rows = sorted(json.load(open(ext[0])), key=lambda r: r["elapsed_s"])
    t = np.array([r["elapsed_s"] for r in rows]); v = np.array([r["success_rate"] for r in rows])
    ax.plot(t / 60, v, "o-", ms=3.5, lw=1.6, label="V=3 3h (seed 7)")
    ax.set_xlabel("wall-clock training time (min)")
    ax.set_ylabel("success rate on MetaDrive (30 ep, deterministic)")
    ax.set_title("Budget extension: does more wall-clock help?")
    ax.set_ylim(0, 1.0); ax.legend(fontsize=9); ax.grid(alpha=0.3)
    fig.tight_layout(); fig.savefig("figs/fig_budget_ext.png")
    print("fig_budget_ext.png 저장")
else:
    print("[skip] fig_budget_ext: eval_md__ext3h.json 없음")
