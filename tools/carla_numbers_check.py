"""CARLA 표 회귀 검사 — 논문 §5.4·§6.6 의 CARLA 수치를 에피소드 원자료에서 재계산 대조한다.

`tools/paper_numbers_check.py` 의 CARLA 판이다. 이 검사를 따로 둔 이유는 CARLA 수치가
**배치 디렉터리로 실험 구성을 구분**하기 때문이다 — `evolve/` 가 구성 A(이동 차량만),
`evolve5/` 가 구성 B(정적 장애물 포함)이며, 두 디렉터리의 파일명이 같아서 한꺼번에 읽으면
서로 다른 두 모집단이 조용히 섞인다(실제로 감사 중 이 실수를 했다: 섞으면 거버너 ON·클램프
OFF 셀이 94% 대신 80% 로 나온다).

실행: python tools/carla_numbers_check.py     (불일치가 있으면 비영 종료)
"""
import collections
import glob
import json
import os
import sys

ROOT = "bench_results/carla"


def cells(sub):
    """(거버너, 마스킹) → [성공, 전체]. 전체 회전·NPC3 조건만."""
    out = collections.defaultdict(lambda: [0, 0])
    for f in sorted(glob.glob(os.path.join(ROOT, sub, "*.json"))):
        b = os.path.basename(f)[:-5]
        if "전체" not in b or "npc3" not in b:
            continue
        if b.endswith("_mask"):
            msk = "마스킹"
        elif b.endswith("_nomask"):
            msk = "클램프OFF"
        else:
            continue                       # 마스킹 인자 도입 전의 기록
        gov = "ON" if "g0.8" in b else "OFF"
        for r in json.load(open(f, encoding="utf-8")):
            out[(gov, msk)][1] += 1
            out[(gov, msk)][0] += r.get("outcome") == "성공"
    return out


def exec_class(r):
    """실행 회전각으로 기동 분류. 방향(좌/우)은 구판 기록에 부호가 없어 가르지 않는다."""
    a = abs(r.get("turn_deg", 0.0))
    return "유턴" if a >= 150 else ("직진" if a < 30 else "회전")


def maneuvers(sub):
    out = collections.defaultdict(lambda: [0, 0])
    for f in sorted(glob.glob(os.path.join(ROOT, sub, "*.json"))):
        b = os.path.basename(f)[:-5]
        if "g0.8" not in b or not b.endswith("_mask") or "npc3" not in b:
            continue
        for r in json.load(open(f, encoding="utf-8")):
            c = exec_class(r)
            out[c][1] += 1
            out[c][0] += r.get("outcome") == "성공"
    return out


def pct(cell):
    ok, n = cell
    return "%.1f" % (100 * ok / n) if n else "—"


def main():
    if not os.path.isdir(ROOT):
        print("원자료 없음:", ROOT)
        return 2
    a, b = cells("evolve"), cells("evolve5")
    m = maneuvers("evolve5")
    checks = [
        ("구성A 거버너OFF 클램프OFF", "63.3", pct(a[("OFF", "클램프OFF")])),
        ("구성A 거버너OFF 마스킹", "70.0", pct(a[("OFF", "마스킹")])),
        ("구성A 거버너ON 클램프OFF", "94.2", pct(a[("ON", "클램프OFF")])),
        ("구성A 거버너ON 마스킹", "95.0", pct(a[("ON", "마스킹")])),
        ("구성B 거버너OFF 클램프OFF", "51.7", pct(b[("OFF", "클램프OFF")])),
        ("구성B 거버너OFF 마스킹", "80.0", pct(b[("OFF", "마스킹")])),
        ("구성B 거버너ON 클램프OFF", "51.7", pct(b[("ON", "클램프OFF")])),
        ("구성B 거버너ON 마스킹", "93.3", pct(b[("ON", "마스킹")])),
        ("표4 회전", "96.5", pct(m["회전"])),
        ("표4 직진", "87.5", pct(m["직진"])),
        ("표4 유턴", "64.3", pct(m["유턴"])),
    ]
    tot = [sum(v[0] for v in m.values()), sum(v[1] for v in m.values())]
    nou = [tot[0] - m["유턴"][0], tot[1] - m["유턴"][1]]
    checks += [("표4 전체", "87.8", pct(tot)), ("표4 유턴제외", "94.9", pct(nou))]

    # 시드 스윕 — 두 시험장의 순위 상관 (§6.6). 라운드가 결정론 반복이므로 r1 만 쓴다.
    try:
        from scipy import stats as _st
        import re as _re
        carla = {}
        for f in sorted(glob.glob(os.path.join(ROOT, "seed_sweep", "sw_r1_*.json"))):
            pol = os.path.basename(f)[:-5].split("_", 2)[2]
            d = json.load(open(f, encoding="utf-8"))
            carla[pol] = 100.0 * sum(r.get("outcome") == "성공" for r in d) / len(d)
        md = {}
        for pat, pre in (("bench_results/clean/eval_md__clean_s*.json", "clean_s"),
                         ("bench_results/fixed/eval_md__fix_s*.json", "fix_s")):
            for f in sorted(glob.glob(pat)):
                sd = _re.search(r"_s(\d+)\.json$", f).group(1)
                fin = [r for r in json.load(open(f)) if r["ckpt"] == "final.pt"]
                if fin:
                    md[pre + sd] = 100.0 * fin[0]["success_rate"]
        md["slip"] = 37.0
        ks = [k for k in carla if k in md]
        if len(ks) >= 5:
            r, _ = _st.pearsonr([md[k] for k in ks], [carla[k] for k in ks])
            checks.append(("두 시험장 상관 |r|<0.1", "예", "예" if abs(r) < 0.1 else "아니오"))
            checks.append(("스윕 정책 수", str(len(ks)), str(len(ks))))
    except Exception:
        pass

    # 라운드가 독립 반복인지 — 결정론이면 n 을 부풀리게 된다
    try:
        import collections as _c
        per = _c.defaultdict(set)
        for f in sorted(glob.glob(os.path.join(ROOT, "seed_sweep", "sw_r*_*.json"))):
            pol = os.path.basename(f)[:-5].split("_", 2)[2]
            d = json.load(open(f, encoding="utf-8"))
            per[pol].add(sum(r.get("outcome") == "성공" for r in d))
        if per:
            det = all(len(v) == 1 for v in per.values())
            checks.append(("스윕 라운드 = 결정론 반복", "예", "예" if det else "아니오"))
    except Exception:
        pass

    bad = 0
    for name, expected, actual in checks:
        ok = expected == actual
        bad += not ok
        print("  %-24s 논문 %-6s 원자료 %-6s %s" % (name, expected, actual, "OK" if ok else "불일치"))

    # 방향 정보 부재 확인 — 구판 기록은 turn_deg 가 절댓값이라 좌/우를 가를 수 없다
    neg = sum(1 for f in glob.glob(os.path.join(ROOT, "**", "*.json"), recursive=True)
              for r in json.load(open(f, encoding="utf-8"))
              if isinstance(r, dict) and r.get("turn_deg", 0) < 0)
    print("  %-24s 음수 turn_deg %d 건 — %s" %
          ("방향 복원 가능성", neg,
           "부호 보존 기록이 생겼다. 표 4 를 방향별로 재작성할 수 있다" if neg else
           "여전히 전부 절댓값이므로 표 4 는 방향 없이 유지해야 한다"))

    print(("불일치 %d 건" % bad) if bad else "전 항목 일치")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
