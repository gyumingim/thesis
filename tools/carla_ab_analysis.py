"""CARLA 배치 결과 집계 — 조건별 성공률과 95% 신뢰구간, 기동별 분해.

carla_drive.py 가 남기는 에피소드 JSON 들을 파일명 태그로 묶어 집계한다.
파일명 규약: <접두>_r<라운드>_<조건...>.json — 라운드 토큰만 제거하면 조건 키가 된다.

실행: python tools/carla_ab_analysis.py C:/carla/seed_sweep
"""
import collections
import glob
import json
import math
import os
import sys


def wilson(k, n, z=1.96):
    """이항 비율의 Wilson 신뢰구간 — n 이 작고 비율이 0/1 에 붙어도 무너지지 않는다."""
    if n == 0:
        return 0.0, 0.0
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return max(0.0, c - h), min(1.0, c + h)


def maneuver(r):
    """앵커 라벨이 아니라 **실행된 경로의 총 회전각**으로 기동을 정한다.

    경로계획기가 회전 앵커에서도 직진·유턴 경로를 내놓는 일이 있어, 앵커 라벨로 집계하면
    통계가 오염된다(carla_drive.py 의 재라벨 규약과 동일: |각| ≥ 150 은 유턴, < 30 은 직진).

    **방향(좌/우)은 실행 경로로 가르지 않는다.** 2026-08-29 이전에 수집된 기록의
    `turn_deg` 는 abs() 를 씌워 저장돼 부호가 없다(전수 확인: 732건 모두 ≥ 0). 부호가
    있는 기록에서는 CARLA 좌수 좌표계 규약대로 **양수 = 우회전**이다 — 스폰 라벨과 같다.
    부호가 없으면 방향을 "회전"으로 뭉갠다. 앵커 라벨로 되돌아가면 애초에 재라벨한 이유가
    사라지므로, 방향별 통계가 필요하면 부호를 보존하는 현행 코드로 재수집해야 한다.
    """
    td = r.get("turn_deg")
    if td is None:
        return r.get("kind") or "미상"
    a = abs(td)
    if a >= 150:
        return "유턴"
    if a < 30:
        return "직진"
    if td == a:                      # 부호가 없는(구판) 기록 — 방향 판정 보류
        return "회전"
    return "우회전" if td > 0 else "좌회전"


def main():
    root = sys.argv[1] if len(sys.argv) > 1 else "C:/carla/seed_sweep"
    cells = collections.defaultdict(lambda: [0, 0])
    by_man = collections.defaultdict(lambda: collections.defaultdict(lambda: [0, 0]))
    for f in sorted(glob.glob(os.path.join(root, "*.json"))):
        parts = os.path.basename(f)[:-5].split("_")
        key = "_".join(t for t in parts[1:] if not t.startswith("r") or not t[1:].isdigit())
        try:
            rows = json.load(open(f, encoding="utf-8"))
        except Exception:
            continue
        for r in rows:
            ok = r.get("outcome") == "성공"
            cells[key][1] += 1
            cells[key][0] += ok
            m = maneuver(r)
            by_man[key][m][1] += 1
            by_man[key][m][0] += ok

    if not cells:
        print("결과 없음:", root)
        return
    print("조건별 성공률 (Wilson 95% CI)")
    for k in sorted(cells, key=lambda k: -cells[k][0] / max(1, cells[k][1])):
        ok, n = cells[k]
        lo, hi = wilson(ok, n)
        print("  %-14s %3d/%-3d = %5.1f%%  [%4.1f, %4.1f]" %
              (k, ok, n, 100 * ok / n, 100 * lo, 100 * hi))
    print()
    print("기동별 분해")
    for k in sorted(by_man):
        row = "  %-14s " % k
        for m, (ok, n) in sorted(by_man[k].items(), key=lambda x: -x[1][1]):
            row += "%s %d/%d  " % (m, ok, n)
        print(row)


if __name__ == "__main__":
    main()
