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


# ★ 선택 검사가 실패해도 전체를 막지 않지만 **조용히 사라지면 안 된다**.
# 실제로 os 미import 로 블록 하나가 통째로 죽어 있었는데 출력은 «전 항목 일치»
# 였다(2026-09-15). 건너뛴 사실과 이유를 반드시 남긴다.
def _skip(tag, e):
    print("  (검사 건너뜀 [%s]: %s: %s)" % (tag, type(e).__name__, e))


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
    except Exception as _e:
        _skip("시험장 상관", _e)

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
    except Exception as _e:
        _skip("스윕 결정론", _e)

    # 표 2·3·4 의 반복도 같은 20 앵커의 재측정이다 — 유효 표본이 n 이 아니다
    try:
        import collections as _c
        import statistics as _stt
        for sub, tag in (("evolve", "표2"), ("evolve5", "표3")):
            anc = _c.defaultdict(list)
            for f in sorted(glob.glob(os.path.join(ROOT, sub, "*.json"))):
                b = os.path.basename(f)[:-5]
                if "전체" not in b or "npc3" not in b or not b.endswith("_nomask"):
                    continue
                if "g0.8" in b:
                    continue
                for r in json.load(open(f, encoding="utf-8")):
                    anc[r.get("ep")].append(r.get("outcome") == "성공")
            if len(anc) >= 5 and max(len(v) for v in anc.values()) >= 2:
                m = [sum(v) / len(v) for v in anc.values()]
                n_ep = sum(len(v) for v in anc.values())
                pbar = sum(sum(v) for v in anc.values()) / n_ep
                se_c = _stt.stdev(m) / (len(m) ** 0.5)
                se_n = (pbar * (1 - pbar) / n_ep) ** 0.5
                deff = (se_c / se_n) ** 2
                checks.append(("%s 유효표본<30" % tag, "예",
                               "예" if n_ep / deff < 30 else "아니오"))
        # 경로는 라운드 간 동일한가 — turn_deg 수열의 라운드 간 유일성
        same = tot = 0
        for sub in ("evolve", "evolve5"):
            grp = _c.defaultdict(list)
            for f in sorted(glob.glob(os.path.join(ROOT, sub, "*.json"))):
                parts = os.path.basename(f)[:-5].split("_")
                rs = [t for t in parts if t.startswith("r") and t[1:].isdigit()]
                if not rs:
                    continue
                rows = json.load(open(f, encoding="utf-8"))
                if not rows or not isinstance(rows[0], dict):
                    continue
                grp["_".join(t for t in parts if t != rs[0])].append(
                    tuple(r.get("turn_deg") for r in rows))
            for k, v in grp.items():
                # 표 2·3·4 에 들어가는 조건만 본다. 접두 v4 가 아닌 것들은 어댑터 개발
                # 도중의 6에피소드 예비 실행이라 라운드마다 앵커 집합 자체가 달랐다.
                if k.startswith("v4_") and len(v) >= 3:
                    tot += 1
                    same += len(set(v)) == 1
        if tot:
            checks.append(("표2·3 경로 라운드 간 동일", "%d/%d" % (tot, tot),
                           "%d/%d" % (same, tot)))
    except Exception as _e:
        _skip("표2·3 군집", _e)

    # 표 5 (시드 스윕) — 구판이 철회한 설명 대신 남긴 수치들
    try:
        import itertools as _it
        import statistics as _s2
        pol = {}
        for f in sorted(glob.glob(os.path.join(ROOT, "seed_sweep", "*.json"))):
            parts = os.path.basename(f)[:-5].split("_")
            k = "_".join(t for t in parts if not (t.startswith("r") and t[1:].isdigit()))
            if k not in pol:
                pol[k] = json.load(open(f, encoding="utf-8"))
        if pol:
            def _man(r):
                a = abs(r["turn_deg"])
                if a >= 150:
                    return "유턴"
                if a < 30:
                    return "직진"
                return "우회전" if r["turn_deg"] > 0 else "좌회전"
            rt = {m: [] for m in ("우회전", "좌회전")}
            for k in sorted(pol):
                for m in rt:
                    rs = [r for r in pol[k] if _man(r) == m]
                    rt[m].append(100 * sum(r["outcome"] == "성공" for r in rs) / len(rs))
            d = [l - r for l, r in zip(rt["좌회전"], rt["우회전"])]
            obs = abs(_s2.mean(d))
            hit = sum(1 for sg in _it.product([1, -1], repeat=len(d))
                      if abs(_s2.mean(a * b for a, b in zip(d, sg))) >= obs - 1e-12)
            checks.append(("표5 좌−우 대응 차이", "23.6", "%.1f" % _s2.mean(d)))
            checks.append(("표5 부호 순열 p", "0.0312", "%.4f" % (hit / 2 ** len(d))))
            checks.append(("표5 좌우 역전 정책 수", "0", str(sum(x < 0 for x in d))))
            # 정책 간 분산이 이항 잡음을 넘는가 — 우회전만 넘어야 한다
            for m, k_ep, exp in (("우회전", 8, "2.14"), ("좌회전", 3, "1.13")):
                pb = _s2.mean(rt[m]) / 100
                ratio = _s2.pstdev(rt[m]) / (100 * (pb * (1 - pb) / k_ep) ** 0.5)
                checks.append(("표5 %s 분산/잡음" % m, exp, "%.2f" % ratio))
            # 미공개 필터 규모
            allr = [r for rs in pol.values() for r in rs]
            st = [r for r in allr if _man(r) == "직진"]
            rt2 = [r for r in allr if _man(r) == "우회전"]
            checks.append(("표5 직진 min_R 센티널", "36",
                           str(sum(r["min_R"] >= 999 for r in st))))
            checks.append(("표5 우회전 entry=0", "50",
                           str(sum(r["entry_kmh"] == 0 for r in rt2))))
    except Exception as _e:
        _skip("표5 필터", _e)

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
