"""정합 감사 — 관측 필드의 좌표 규약을 시뮬레이터마다 실측해 대조한다.

왜 필요한가. 본 연구에서 전이 실패의 진짜 원인은 알고리즘이 아니라 **한 관측 벡터 안에
두 개의 상반된 횡방향 규약이 공존한다**는 사실이었다(§4.7). MetaDrive 의 차선 API 는
우(+), 차량 API 는 좌(+)를 쓴다. 그런데 주석과 변수명(`ckpt_in_rhs`, "+y is the right
hand side")은 구현과 반대로 적혀 있어 소스를 읽어도 교정되지 않는다. 이 스크립트는 소스를
읽는 대신 **환경을 굴려서** 각 필드의 규약을 되짚는다.

방법(필드 단위 기하 왕복). 매 스텝
  1. 관측 벡터를 받고,
  2. 같은 시점의 자차 자세와 주변차 세계좌표를 환경 내부에서 직접 읽어
     좌(+) 기준 상대 종/횡 성분을 독립적으로 계산하고,
  3. 관측의 슬롯 0 을 자차 기준 **최근접** 차량에 맞춘 뒤(정렬은 종방향 값으로 검산),
  4. 두 규약 가설 — obs = (v/D+1)/2  (좌+) 와  obs = (−v/D+1)/2  (우+) — 의
     잔차를 비교해 어느 쪽이 맞는지 판정한다.
잔차가 부동소수 수준(<1e-3)으로 떨어지는 쪽이 그 필드의 실제 규약이다.

사용:
  python tools/align_audit.py --env md      # MetaDrive
  python tools/align_audit.py --env custom  # 경량 시뮬
  python tools/align_audit.py --env both    # 대조 (규약이 갈리면 비영 종료)
"""
import argparse
import math
import sys

import numpy as np

sys.path.insert(0, "bench")

DETECT_R = 50.0                 # spec.DETECT_RADIUS — 정규화 분모
FIELDS = [                      # (이름, obs 인덱스, 성분)  성분: "lat" | "lon"
    ("슬롯0 상대위치 종", 19, "lon"),
    ("슬롯0 상대위치 횡", 20, "lat"),
]


def local_frame(ex, ey, h, px, py):
    """세계좌표 점을 자차 국소 좌표로. 반환 (전방, **좌**)."""
    dx, dy = px - ex, py - ey
    return dx * math.cos(h) + dy * math.sin(h), -dx * math.sin(h) + dy * math.cos(h)


def fit(obs_vals, true_vals):
    """두 규약 가설의 평균 절대 잔차를 반환한다 — (좌+, 우+)."""
    o = np.asarray(obs_vals, float)
    t = np.asarray(true_vals, float) / DETECT_R
    return (float(np.mean(np.abs(o - (t + 1) / 2))),
            float(np.mean(np.abs(o - (-t + 1) / 2))))


def sample_md(n, seed=0, density=0.5):
    from md_env import MetaDriveGT
    e = MetaDriveGT(seed=seed, density=density)
    obs, _ = e.reset(seed=seed)
    inner = e._env
    rows = []
    for _ in range(n):
        obs, _r, te, tr, _i = e.step(np.array([0.0, 0.5], np.float32))
        if te or tr:
            obs, _ = e.reset(seed=seed)
            continue
        ag = inner.agent
        ex, ey = ag.position
        h = ag.heading_theta
        near = None
        for o in inner.engine.get_objects(
                lambda x: hasattr(x, "position") and x is not ag).values():
            try:
                px, py = o.position
            except Exception:
                continue
            d = math.hypot(px - ex, py - ey)
            if d <= DETECT_R and (near is None or d < near[0]):
                near = (d, ) + local_frame(ex, ey, h, px, py)
        if near is not None:
            rows.append((obs.copy(), near[1], near[2]))
    e.close()
    return rows


def sample_custom(n, seed=0):
    from env_numba import IntersectionEnv
    e = IntersectionEnv(n_envs=1, n_vehicles=8, seed=seed)
    e.reset()
    rows = []
    for _ in range(n):
        obs, _r, _te, _tr, _f = e.step(e.expert_action())
        ex, ey, h, _v = e.ego[0]
        near = None
        for v in range(e.V):
            px, py = e.npc[0, v, 0], e.npc[0, v, 1]
            if px == 0.0 and py == 0.0:
                continue
            d = math.hypot(px - ex, py - ey)
            if d <= DETECT_R and (near is None or d < near[0]):
                near = (d, ) + local_frame(ex, ey, float(h), float(px), float(py))
        if near is not None:
            rows.append((obs[0].copy(), near[1], near[2]))
    return rows


def mirror(rows):
    """정정 전 커널이 내던 거울상을 재현 — 횡 필드만 v -> 1-v (패딩 0 은 보존)."""
    out = []
    for obs, lon, lat in rows:
        o = obs.copy()
        for i in [10, 15] + [20 + 4 * k for k in range(8)] + [22 + 4 * k for k in range(8)]:
            if i < len(o) and o[i] != 0.0:
                o[i] = 1.0 - o[i]
        out.append((o, lon, lat))
    return out


def audit(name, rows):
    print("=== %s (표본 %d) ===" % (name, len(rows)))
    if not rows:
        print("  표본 없음 — 주변차가 탐지 반경 안에 들어온 스텝이 없다")
        return {}
    verdicts = {}
    for label, idx, comp in FIELDS:
        pick = 1 if comp == "lon" else 2
        keep = [(r[0][idx], r[pick]) for r in rows
                if abs(r[0][idx] - 0.5) > 1e-6]        # 빈 슬롯(패딩 0.5/0) 제외
        if len(keep) < 20:
            print("  %-16s 표본 부족(%d)" % (label, len(keep)))
            continue
        pos, neg = fit([k[0] for k in keep], [k[1] for k in keep])
        conv = "좌+" if pos < neg else "우+"
        res = min(pos, neg)
        flag = "OK" if res < 1e-3 else "의심(잔차 %.3f — 정규화 상수 불일치?)" % res
        verdicts[label] = conv
        print("  %-16s idx%-3d 규약 %s  잔차 좌+=%.5f 우+=%.5f  %s"
              % (label, idx, conv, pos, neg, flag))
    return verdicts


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--env", default="both", choices=("md", "custom", "both"))
    ap.add_argument("--steps", type=int, default=600)
    ap.add_argument("--inject-mirror", action="store_true",
                    help="횡 필드에 거울상을 주입해 감사의 검출력을 시험한다")
    a = ap.parse_args()

    def prep(rows):
        return mirror(rows) if a.inject_mirror else rows

    got = {}
    if a.env in ("md", "both"):
        got["MetaDrive"] = audit("MetaDrive", prep(sample_md(a.steps)))
    if a.env in ("custom", "both"):
        got["경량 시뮬"] = audit("경량 시뮬", prep(sample_custom(a.steps)))

    if len(got) == 2:
        (na, va), (nb, vb) = list(got.items())
        bad = [k for k in set(va) & set(vb) if va[k] != vb[k]]
        print()
        if bad:
            print("불일치: " + ", ".join(
                "%s (%s=%s vs %s=%s)" % (k, na, va[k], nb, vb[k]) for k in bad))
            print("→ 이 필드들은 거울상이다. 전이 학습 전에 커널을 고칠 것.")
            raise SystemExit(1)
        print("두 시뮬레이터의 횡방향 규약 일치 — 전이 가능.")


if __name__ == "__main__":
    main()
