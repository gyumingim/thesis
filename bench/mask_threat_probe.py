"""마스킹 뒤에 **남은 충돌**이 «없는 셈 친 차» 때문인가 — §5.2 (ii) 의 직접 시험.

`tools/mask_mechanism.py` 는 마스킹 구제가 거의 전부 **이탈 감소**이고 충돌은 거의 그대로
남는다는 것을 보였다(회복 +50.0%p 중 이탈 −43.3%p, 충돌 −6.7%p). 이는 (ii)와 **양립**
하지만 (ii)의 **시험**은 아니다. (ii)가 맞다면 남은 충돌은 아무 데나 흩어져 있지 않고,
V=2 정책이 학습한 적 없는 **셋째 이상의 차가 실제로 곁에 있을 때** 몰려야 한다.

그래서 에피소드마다 «셋째 차에 얼마나 노출됐는가»를 재고 그것으로 층화해 충돌률을 본다.

★ 첫 판은 **종료 시점**의 이웃 거리로 층화했는데 그것은 순환이다 — 충돌한 순간에는
  들이받은 차가 정의상 가까이 있다. 실제로 «셋째 차 15 m 안» 층의 충돌률이 두 정책 모두
  100% 로 나왔다. 노출은 **종료 직전 구간을 뺀** 앞부분에서 재야 한다(TAIL 스텝 제외).

교란 하나를 반드시 통제해야 한다: **차가 많은 에피소드는 누구에게나 어렵다.** 그래서
같은 층화를 **V=3 로 학습한 정책**(clean_custom)에도 적용한다. V=3 정책에서는 층별 차이가
작은데 마스킹 V=2 정책에서만 크다면, 그 차이는 난이도가 아니라 «없는 셈 침» 에서 온다.

실행: .venv/Scripts/python.exe bench/mask_threat_probe.py --out bench_results/mask_paired/threat.json
"""
import argparse
import glob
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import torch

import evaluate as EV

OTHER_BASE, OTHER_DIM, N_OTHERS, DR = 19, 4, 8, 50.0
THREAT_M = 30.0          # «곁에 있다» 의 기준. 감도는 아래에서 함께 보고한다.
TAIL = 10                # 종료 직전 이 스텝 수는 노출 계산에서 뺀다 (순환 방지)
HEAD = 20                # **고정 길이** 앞구간. 에피소드 길이와 얽히지 않는다


def neighbors(obs):
    """정규화 관측 1개 → (점유 슬롯 수, 거리 오름차순 리스트[m])."""
    ds = []
    for s in range(N_OTHERS):
        b = OTHER_BASE + s * OTHER_DIM
        if not np.any(obs[b:b + OTHER_DIM] != 0.0):
            continue
        fwd = (2.0 * obs[b + 0] - 1.0) * DR
        lat = (2.0 * obs[b + 1] - 1.0) * DR
        ds.append(float(np.hypot(fwd, lat)))
    return len(ds), sorted(ds)


def run(ckpt, mask, episodes, seed, device):
    from md_env import MetaDriveGT
    EV.MASK_DEGENERATE = mask
    EV.MIRROR_LATERAL = False
    agent, mean, std, _ = EV.load_agent(ckpt, device)
    env = MetaDriveGT(seed=seed, density=0.1, num_scenarios=episodes)
    rows = []
    for ep in range(episodes):
        obs, _ = env.reset(seed=seed + ep)
        near3, slots, last = [], [], obs
        while True:
            a = EV._act(agent, obs[None, :], mean, std, device)[0]
            last = obs
            obs, r, tm, tr, info = env.step(a)
            n, d = neighbors(last)
            slots.append(n)
            near3.append(1 if (len(d) >= 3 and d[2] <= THREAT_M) else 0)
            if tm or tr:
                flag = 3 if info.get("arrive_dest") else (
                    1 if info.get("crash") else (2 if info.get("out_of_road") else 4))
                head = near3[:-TAIL] if len(near3) > TAIL else []
                fixed = near3[:HEAD] if len(near3) >= HEAD else None
                _, d_end = neighbors(last)
                rows.append(dict(scenario=int(seed + ep), flag=flag,
                                 steps=len(near3), head_steps=len(head),
                                 exposure=(sum(head) / len(head)) if head else None,
                                 head_fixed=(sum(fixed) / HEAD) if fixed else None,
                                 max_slots=int(max(slots)),
                                 end_dists=[round(x, 1) for x in d_end[:4]]))
                break
    env.close()
    return rows


def stratify_end(rows, thr_m, k=3):
    """1판(순환) — 종료 시점에 셋째 차가 thr_m 안이었는가. 기록용으로만 남긴다."""
    out = {}
    for lab, hi in (("노출 높음", True), ("노출 낮음", False)):
        sel = [r for r in rows
               if (len(r["end_dists"]) >= k and r["end_dists"][k - 1] <= thr_m) == hi]
        n = len(sel)
        out[lab] = (n,
                    sum(r["flag"] == 1 for r in sel) / n if n else float("nan"),
                    sum(r["flag"] == 3 for r in sel) / n if n else float("nan"))
    out["_drop"] = 0
    return out


def stratify(rows, cut, key="head_fixed"):
    """**고정 길이 앞구간**의 노출(셋째 차가 THREAT_M 안이던 스텝 비율)로 나눈다.

    ★ 층화 기준을 두 번 갈아엎은 자리다. 기록해 둔다:
      1판 «종료 시점의 이웃 거리» — 순환이다(충돌하면 들이받은 차가 정의상 가깝다).
         두 정책 모두 근접층 충돌률 100%가 나왔다.
      2판 «종료 직전을 뺀 전 구간의 노출 비율» — 에피소드 **길이**와 얽힌다. 일찍 죽으면
         분모가 짧아 노출 비율이 낮게 나오므로, 노출이 높을수록 충돌이 **낮아지는**
         역방향 인공물이 생겼다(−18%p).
      3판(현재) 앞 HEAD 스텝 **고정 길이**. 분모가 모두 같아 길이와 얽히지 않는다.
         HEAD 보다 짧은 에피소드는 제외하고 그 수를 함께 찍는다.
    """
    out = {}
    usable = [r for r in rows if r.get(key) is not None]
    for lab, pred in (("노출 높음", lambda r: r[key] > cut),
                      ("노출 낮음", lambda r: r[key] <= cut)):
        sel = [r for r in usable if pred(r)]
        n = len(sel)
        out[lab] = (n,
                    sum(r["flag"] == 1 for r in sel) / n if n else float("nan"),
                    sum(r["flag"] == 3 for r in sel) / n if n else float("nan"))
    out["_drop"] = len(rows) - len(usable)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--episodes", type=int, default=30)
    ap.add_argument("--seed", type=int, default=500000)
    ap.add_argument("--out", default="bench_results/mask_paired/threat.json")
    ap.add_argument("--reuse", action="store_true",
                    help="저장된 threat.json 으로 집계만 다시 한다")
    a = ap.parse_args()
    device = torch.device("cpu")

    arms = []
    for s in (1, 2):
        d = sorted(glob.glob("runs/Intersection__sup2_custom__%d__*" % s))
        if d:
            arms.append(("V2마스킹 s%d" % s, os.path.join(d[0], "ckpt", "final.pt"), True))
    for s in (1, 2, 3, 4, 5):
        d = sorted(glob.glob("runs/Intersection__clean_custom__%d__*" % s))
        if d:
            arms.append(("V3 s%d" % s, os.path.join(d[0], "ckpt", "final.pt"), False))

    res = {}
    if a.reuse and os.path.exists(a.out):
        with open(a.out, encoding="utf-8") as f:
            res = json.load(f)
        print("  저장된 원자료 재사용: %s" % a.out)
        arms = []
    for tag, ck, mask in arms:
        res[tag] = run(ck, mask, a.episodes, a.seed, device)
        print("  %s 완료 (%d에피소드)" % (tag, len(res[tag])), flush=True)
    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    with open(a.out, "w", encoding="utf-8") as f:
        json.dump(res, f, ensure_ascii=False, indent=1)

    # 세 가지 층화 **정의**를 모두 찍는다. 하나를 골라 보고하면 그 선택 자체가 결과를
    # 만든다 — 실제로 정의를 바꿀 때마다 부호가 뒤집혔다. 셋을 나란히 두는 것이 정직하다.
    DEFS = (("1판 종료시점 근접(순환)", "end", 0.0),
            ("2판 전구간 노출비(길이 교란)", "exposure", 0.0),
            ("3판 앞%d스텝 고정(교란 없음)" % HEAD, "head_fixed", 0.0))
    for label, key, cut in DEFS:
        print("\n[%s] 셋째 차 %.0f m 기준" % (label, THREAT_M))
        print("  %-12s %5s %7s %7s | %5s %7s %7s"
              % ("정책", "n(고)", "충돌", "성공", "n(저)", "충돌", "성공"))
        diffs = {}
        for grp, pref in (("마스킹 V=2", "V2마스킹"), ("재학습 V=3", "V3")):
            pool = [r for t, rs in res.items() if t.startswith(pref) for r in rs]
            st = stratify_end(pool, THREAT_M) if key == "end" else stratify(pool, cut, key)
            (n1, c1, s1), (n0, c0, s0) = st["노출 높음"], st["노출 낮음"]
            print("  %-12s %5d %6s %6s | %5d %6.0f%% %6.0f%%"
                  % (grp, n1, ("%.0f%%" % (100 * c1)) if n1 else "-",
                     ("%.0f%%" % (100 * s1)) if n1 else "-", n0, 100 * c0, 100 * s0))
            if n1 and n0:
                diffs[grp] = 100 * (c1 - c0)
        if len(diffs) == 2:
            print("  충돌 차이  마스킹 %+.0f%%p  vs  재학습 %+.0f%%p  →  차이의 차이 %+.0f%%p"
                  % (diffs["마스킹 V=2"], diffs["재학습 V=3"],
                     diffs["마스킹 V=2"] - diffs["재학습 V=3"]))
        else:
            print("  한쪽 층이 비어 비교 불가 — 이 정의로는 층화가 성립하지 않는다.")
    print("\n판정: 세 정의 중 교란이 없는 3판에서는 **노출 높음 층이 아예 비어 있다**.")
    print("앞 %d스텝 안에 셋째 차가 30 m 안에 오는 에피소드가 하나도 없다 — 교차로에" % HEAD)
    print("도달해야 차가 모이고, 도달하려면 이미 실패하지 않았어야 한다. 즉 «노출» 과")
    print("«생존» 이 구조적으로 얽혀 있어 이 자료로는 (ii) 를 가릴 수 없다. 1판은 순환으로")
    print("양쪽 모두 +63~65%p 를, 2판은 길이 교란으로 −3~−18%p 의 반대 부호를 만들었다.")
    print("정의를 더 찾는 것은 유의한 것이 나올 때까지 고르는 일이므로 여기서 멈춘다.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
