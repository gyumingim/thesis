"""MetaDrive X맵 실측 차선 네트워크 기반 기하 (geometry v3).

md_map_export.json = 설치된 MetaDrive 0.4.3 map="X" 의 66개 차선 폴리라인 원본.
우리 환경은 이 좌표계를 그대로 사용한다 — 전이 시 좌표 변환이 없다.

경로 36개 = 진입 4팔 x 기동 3 x 차선 3. 인덱스 = arm*9 + m*3 + lane.
lane 0 = 황색선 쪽(좌측), 2 = 백색선 쪽(우측). m: 0=우회전, 1=직진, 2=좌회전.
검증: 남팔 9경로 전 지점이 MetaDrive 물리 스텝에서 생존 (2026-08-20 프로브).
"""
import json
import os
import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
WP_STEP = 2.0
LANE_W = 3.5


def _load():
    d = json.load(open(os.path.join(_HERE, "md_map_export.json")))
    E = {(e["a"], e["b"]): e for e in d["edges"]}
    succ = {}
    for (a, b) in E:
        succ.setdefault(a, []).append(b)
    return E, succ


def _turn_dir(pts):
    p = np.array(pts)
    v0 = p[1] - p[0]
    v1 = p[-1] - p[-2]
    cr = v0[0] * v1[1] - v0[1] * v1[0]
    if abs(cr) < 1e-3 * (np.linalg.norm(v0) * np.linalg.norm(v1)):
        return 0
    return 1 if cr > 0 else -1


def build_routes_md():
    """[(arm, m_idx, lane, pts(np), secs[(끝s, kind, r, dir)])] 36개 + 엣지 dict."""
    E, succ = _load()
    starts = [(0, [(">", ">>"), (">>", ">>>")], ">>>"),
              (1, [("-1X0_1_", "-1X0_0_")], "-1X0_0_"),
              (2, [("-1X1_1_", "-1X1_0_")], "-1X1_0_"),
              (3, [("-1X2_1_", "-1X2_0_")], "-1X2_0_")]
    routes = []
    for arm, pre_edges, branch in starts:
        for nxt in succ.get(branch, []):
            conn = E[(branch, nxt)]
            chain = pre_edges + [(branch, nxt)]
            exits = succ.get(nxt, [])
            if exits:
                chain.append((nxt, exits[0]))
            m = _turn_dir(conn["lanes"][0]["pts"])
            m_idx = {-1: 0, 0: 1, 1: 2}[m]
            for lane in range(3):
                pts, secs, acc = [], [], 0.0
                for (a, b) in chain:
                    rec = E[(a, b)]["lanes"][lane]
                    lp = rec["pts"]
                    if pts and np.hypot(pts[-1][0] - lp[0][0], pts[-1][1] - lp[0][1]) < 0.5:
                        lp = lp[1:]
                    pts.extend(lp)
                    acc += rec["length"]
                    r = rec["length"] / (np.pi / 2) if rec["kind"] == "CircularLane" else 0.0
                    d = _turn_dir(rec["pts"]) if rec["kind"] == "CircularLane" else 0
                    secs.append((acc, rec["kind"], r, d))
                routes.append((arm, m_idx, lane, np.array(pts, np.float32), secs))
    routes.sort(key=lambda r: r[0] * 9 + r[1] * 3 + r[2])
    return routes, E


def pack_routes():
    """env_numba 용: (wps, n_wp, cum, tang, length, lane_offs)."""
    routes, _ = build_routes_md()
    n = len(routes)
    polys = []
    for (_a, _m, _l, p, _s) in routes:
        s = np.concatenate([[0], np.cumsum(np.linalg.norm(np.diff(p, axis=0), axis=1))])
        ss = np.append(np.arange(0, s[-1], WP_STEP), s[-1])
        polys.append(np.stack([np.interp(ss, s, p[:, 0]),
                               np.interp(ss, s, p[:, 1])], -1).astype(np.float32))
    max_wp = max(len(p) for p in polys)
    wps = np.zeros((n, max_wp, 2), np.float32)
    n_wp = np.zeros(n, np.int32)
    cum = np.zeros((n, max_wp), np.float32)
    tang = np.zeros((n, max_wp, 2), np.float32)
    for i, p in enumerate(polys):
        k = len(p)
        wps[i, :k] = p
        n_wp[i] = k
        seg = np.diff(p, axis=0)
        L = np.linalg.norm(seg, axis=1)
        cum[i, 1:k] = np.cumsum(L)
        t = seg / np.maximum(L[:, None], 1e-9)
        tang[i, :k - 1] = t
        tang[i, k - 1] = t[-1]
        wps[i, k:] = p[-1]
        cum[i, k:] = cum[i, k - 1]
        tang[i, k:] = t[-1]
    length = cum[np.arange(n), n_wp - 1]
    # MD 실측: 우측차선(lane2) 스폰 시 dist_left(황색까지)=8.75 → LOFF = 1.75 + 3.5*lane
    lane_offs = np.array([1.75 + 3.5 * lane for (_a, _m, lane, _p, _s) in routes], np.float32)
    return wps, n_wp, cum, tang, length.astype(np.float32), lane_offs


def build_sections_md(max_secs=4):
    """(n,4) 섹션끝 s / 끝좌표 / (bend01, dir01, angle01) — MD navi 정규화 동일
    (분모 60+3x3.5=70.5, 각도 90/135, dir: 시계(우회전)=1)."""
    routes, _ = build_routes_md()
    n = len(routes)
    DENOM, a90 = 60.0 + 3 * LANE_W, (90.0 / 135.0 + 1) / 2
    ses = np.zeros((n, max_secs), np.float32)
    sxy = np.zeros((n, max_secs, 2), np.float32)
    sinfo = np.zeros((n, max_secs, 3), np.float32)
    for i, (_a, _m, _l, p, secs) in enumerate(routes):
        s_arr = np.concatenate([[0], np.cumsum(np.linalg.norm(np.diff(p, axis=0), axis=1))])
        for j in range(max_secs):
            end, kind, r, d = secs[min(j, len(secs) - 1)]
            ses[i, j] = end
            idx = min(int(np.searchsorted(s_arr, min(end, s_arr[-1]))), len(p) - 1)
            sxy[i, j] = p[idx]
            sinfo[i, j] = (min(r / DENOM, 1.0), 1.0 if d < 0 else 0.0, a90) \
                if kind == "CircularLane" else (0.0, 0.5, 0.5)
    return ses, sxy, sinfo


def build_rules(cell=0.5):
    """종료 규칙 데이터.

    rects (R,5) = (a0, a1, lo, hi, axis): 직선 로드웨이. axis 0 = 도로가 x방향(횡=y).
    lo/hi = 로드웨이를 감싸는 연속선(황·백) 좌표. 접촉 판정은 커널.
    내부 그리드 D = 교차로 박스 안 '아무 차선 중심선까지 거리' (on_lane 근사).
    """
    E, _ = _load()
    straights, conns = [], []
    for e in E.values():
        if e["lanes"][0]["kind"] == "StraightLane":
            straights.append(e)
        else:
            conns.append(e)
    allc = np.concatenate([np.array(l["pts"]) for e in conns for l in e["lanes"]], 0)
    box = (float(allc[:, 0].min() - 2), float(allc[:, 0].max() + 2),
           float(allc[:, 1].min() - 2), float(allc[:, 1].max() + 2))

    rects = []
    interior_pts = [allc]
    for e in straights:
        pts0 = np.array(e["lanes"][0]["pts"])
        span = np.abs(pts0[-1] - pts0[0])
        axis = 0 if span[0] > span[1] else 1
        centers = np.array([l["pts"][0] for l in e["lanes"]] + [l["pts"][-1] for l in e["lanes"]])
        latc = centers[:, 1 - axis]
        a = np.array([pts0[0][axis], pts0[-1][axis]])
        rects.append((float(a.min()), float(a.max()),
                      float(latc.min() - LANE_W / 2), float(latc.max() + LANE_W / 2), float(axis)))
        for l in e["lanes"]:
            q = np.array(l["pts"])
            m = (q[:, 0] > box[0]) & (q[:, 0] < box[1]) & (q[:, 1] > box[2]) & (q[:, 1] < box[3])
            if m.any():
                interior_pts.append(q[m])

    P = np.concatenate(interior_pts, 0)
    xs = np.arange(box[0], box[1] + cell, cell)
    ys = np.arange(box[2], box[3] + cell, cell)
    GX, GY = np.meshgrid(xs, ys, indexing="ij")
    D = np.full(GX.shape, 1e9, np.float32)
    for k in range(0, len(P), 400):
        c = P[k:k + 400]
        d = np.sqrt((GX[..., None] - c[:, 0]) ** 2 + (GY[..., None] - c[:, 1]) ** 2).min(-1)
        D = np.minimum(D, d.astype(np.float32))
    return (np.array(rects, np.float32), np.array(box, np.float32),
            np.float32(cell), D)


if __name__ == "__main__":
    wps, n_wp, cum, tang, length, loff = pack_routes()
    print("routes:", wps.shape, "길이", np.round([length.min(), length.max()], 1), "LOFF", sorted(set(loff.tolist())))
    ses, sxy, si = build_sections_md()
    print("직진 lane2(rid5) 섹션:", np.round(ses[5], 1))
    rects, box, cell, D = build_rules()
    print("rects", rects.shape, "박스", np.round(box, 1), "그리드", D.shape, f"D {D.min():.2f}~{D.max():.1f}")
