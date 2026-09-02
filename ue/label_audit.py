"""생성된 장면 라벨의 기하 감사 — 렌더를 보기 전에 수치로 먼저 잡는다.

`scene_*.json` 만 읽고 (1) 우측통행, (2) 차로 정렬, (3) 역주행, (4) 근경 분포,
(5) 가시도·ignore 정합, (6) 박스 화면 범위를 점검한다.

**좌표 되돌림 주의 (2026-09-02 실패 기록).** 라벨의 `relative_position_m` 은 카메라
좌표다. 세계 좌표로 되돌릴 때 카메라 요각을 빼먹고 `world_y = rel_y + cam_y` 로 더하면
거리 110 m 에서 최대 11 m 가 틀어진다(요각 지터 ±6°) — 차로 두세 개를 건너뛰는 크기다.
그 오류로 «차로 위 차량의 8.5% 가 역주행» 이라는 없는 결함을 보고하고 생성기를 고쳤다가
되돌렸다. 아래 `to_world` 가 `scene_build_cs.cam_basis` 의 역변환이며, 이 파일을 고칠
때는 **수정 전 자료에서도 같은 지표가 나오는지** 반드시 대조하라.

실행: python ue/label_audit.py C:/ue/verify10 [비교할_이전_디렉터리]
"""
import glob
import io
import json
import math
import os
import sys

LANE_CTRS = (-8.75, -5.25, -1.75, 1.75, 5.25, 8.75)
HALF_LANE = 1.75
W, H = 1280, 720


def cam_basis(roll, pitch, yaw):
    """scene_build_cs 와 동일 — UE Rotator 의 회전행렬(pitch 양수 = 기수 상향)."""
    cr, sr = math.cos(math.radians(roll)), math.sin(math.radians(roll))
    cp, sp = math.cos(math.radians(pitch)), math.sin(math.radians(pitch))
    cy, sy = math.cos(math.radians(yaw)), math.sin(math.radians(yaw))
    rz = ((cy, -sy, 0.0), (sy, cy, 0.0), (0.0, 0.0, 1.0))
    ry = ((cp, 0.0, -sp), (0.0, 1.0, 0.0), (sp, 0.0, cp))
    rx = ((1.0, 0.0, 0.0), (0.0, cr, -sr), (0.0, sr, cr))

    def mm(a, b):
        return tuple(tuple(sum(a[i][k] * b[k][j] for k in range(3)) for j in range(3))
                     for i in range(3))
    return mm(mm(rz, ry), rx)


def to_world(rel, cam, R):
    """p_world = R · p_cam + cam. cam_basis 의 역변환이다."""
    return tuple(sum(R[i][k] * rel[k] for k in range(3)) + cam[i] for i in range(3))


def aligned(yaw, tol=20.0):
    a = abs(((yaw + 180) % 360) - 180)
    return min(a, abs(a - 180)) < tol


def audit(root):
    fs = sorted(glob.glob(os.path.join(root, "scene_*.json")))
    if not fs:
        return None
    rec = []
    for f in fs:
        s = json.load(io.open(f, encoding="utf-8"))
        c = s["camera"]
        R = cam_basis(c["roll_deg"], c["pitch_deg"], c["yaw_deg"])
        cam = (0.0, c["y_m"], c["z_m"])
        for lb in s["vehicles"]:
            p = lb["relative_position_m"]
            wx, wy, _ = to_world((p["x"], p["y"], p["z"]), cam, R)
            wyaw = ((lb["relative_yaw_deg"] + c["yaw_deg"] + 180) % 360) - 180
            near = min(LANE_CTRS, key=lambda t: abs(t - wy))
            rec.append(dict(f=os.path.basename(f), wx=wx, wy=wy, wyaw=wyaw,
                            near=near, off=abs(wy - near), lb=lb, cam=c))
    return rec, len(fs)


def report(root):
    got = audit(root)
    if not got:
        print("장면 없음:", root)
        return None
    rec, n = got
    out = {}
    print("== %s (장면 %d, 라벨 %d)" % (root, n, len(rec)))

    onc = [r for r in rec if not (abs(r["wyaw"]) < 90)]
    fwd = [r for r in rec if abs(r["wyaw"]) < 90]
    out["대향 좌측"] = 100 * sum(r["wy"] < 0 for r in onc) / len(onc) if onc else 0.0
    out["순방향 우측"] = 100 * sum(r["wy"] > 0 for r in fwd) / len(fwd) if fwd else 0.0
    print("  우측통행  대향 %d대 중 화면 왼쪽 %.1f%% | 순방향 %d대 중 오른쪽 %.1f%%"
          % (len(onc), out["대향 좌측"], len(fwd), out["순방향 우측"]))

    lane = [r for r in rec if r["off"] < 0.6 and abs(r["wy"]) <= 10.0]
    wrong = [r for r in lane if aligned(r["wyaw"])
             and ((r["wy"] > 0) == (abs(r["wyaw"]) > 90))]
    out["차로 위"] = len(lane)
    out["역주행"] = len(wrong)
    print("  차로 정렬  중심 ±0.6 m 안 %d/%d (%.1f%%) | 그중 역주행 %d"
          % (len(lane), len(rec), 100 * len(lane) / len(rec), len(wrong)))
    for r in wrong[:5]:
        print("     %s y=%+.2f (차로 %+.2f) yaw=%+.1f" % (r["f"], r["wy"], r["near"], r["wyaw"]))

    # 도색선을 밟는가 — 차로 중심에서 반 차로폭 이상 벗어난 주행차
    stray = [r for r in lane if r["off"] > HALF_LANE * 0.6]
    print("  도색 밟기  차로 중심에서 %.2f m 초과 이탈 %d" % (HALF_LANE * 0.6, len(stray)))

    xs = sorted(r["wx"] for r in rec)
    out["거리 중앙"] = xs[len(xs) // 2]
    out["25m 이내"] = 100 * sum(x <= 25 for x in xs) / len(xs)
    print("  근경 분포  거리 중앙 %.1f m | 25 m 이내 %.1f%% | 최대 %.1f m"
          % (out["거리 중앙"], out["25m 이내"], xs[-1]))

    vis = [r for r in rec if "visibility" in r["lb"]]
    z = [r for r in vis if r["lb"]["visibility"] <= 0.001]
    leak = [r for r in vis if r["lb"]["visibility"] <= 0.001 and not r["lb"].get("ignore")]
    good = [r for r in vis if r["lb"]["visibility"] > 0.1]
    out["가시0 누락"] = len(leak)
    print("  가시도    값 있는 라벨 %d | 완전 가림 %d | 그중 ignore 누락 %d | 유효(>0.1) %d (장면당 %.1f)"
          % (len(vis), len(z), len(leak), len(good), len(good) / n))

    oob = [r for r in rec if r["lb"].get("bbox2d")
           and (r["lb"]["bbox2d"][0] < -1 or r["lb"]["bbox2d"][1] < -1
                or r["lb"]["bbox2d"][2] > W + 1 or r["lb"]["bbox2d"][3] > H + 1)]
    out["박스 범위 밖"] = len(oob)
    print("  박스      화면 범위를 벗어난 상자 %d" % len(oob))
    return out


def main():
    roots = sys.argv[1:] or ["C:/ue/verify10"]
    outs = [(r, report(r)) for r in roots]
    if len(outs) > 1 and all(o for _, o in outs):
        print()
        print("== 대조 (지표가 디렉터리마다 크게 다르면 감사 코드가 아니라 자료를 의심하라;")
        print("   반대로 **이전 자료의 값까지 달라지면 감사 코드를 의심하라**)")
        keys = list(outs[0][1])
        print("  %-12s %s" % ("지표", " ".join("%14s" % os.path.basename(r) for r, _ in outs)))
        for k in keys:
            print("  %-12s %s" % (k, " ".join("%14.2f" % o[k] for _, o in outs)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
