"""렌더와 실사를 **분포로** 견준다 — 임계 하나가 아니라.

계기(2026-09-11): 소실점 공허 판정이 3시드로도 분해되지 않았다(6.59 ± 1.24, 임계까지
여유 0.49). 시드를 더 늘려 풀려면 σ 를 0.25 까지 줄여야 하고 그건 25시드 ≈ 10시간이다.
비용이 목적에 비해 터무니없다.

그런데 추정량 자체가 잘못돼 있었다. 실사 기준선은 150장을 **풀링**해 분위수를 냈는데,
렌더 쪽은 «장면 12개의 중앙값» 을 실행마다 구해 그 평균을 썼다. 표본이 12개뿐인 중앙값은
흔들리고, 무엇보다 **같은 방식으로 계산한 값이 아니라 비교가 성립하지 않는다.**

그래서 이 도구는 (1) 여러 실행의 장면을 전부 풀링하고 (2) 실사와 같은 분위수를 내고
(3) 임계 통과/실패 대신 **두 분포가 어디서 갈리는지**를 보여준다. 목표가 "평범한 실사와
구별 불가" 이므로 비교 대상도 분포여야 한다.

실행: python ue/dist_compare.py C:/ue/noise5_90000 C:/ue/noise5_91000 ...
"""
import glob
import importlib.util
import io
import json
import os
import sys

import numpy as np
from PIL import Image

# 참조 집합은 **도메인이 결과를 지배**한다. 둘을 다 볼 수 있게 인자로 받는다.
#   real_labeled (Udacity CrowdAI) — 캘리포니아 간선도로/고속도로. 하늘이 넓게 열린다.
#   ref_all — sKVD 작업용 혼합 도시 참조 170장. 도심 거리가 많아 우리 장면(협곡)에
#             더 가깝지만 스튜디오 차량 사진 같은 비거리 이미지도 섞여 있다.
# 어느 쪽도 «정답» 이 아니므로 두 값을 괄호로 읽는다.
REAL_DIR = os.environ.get("REF_DIR", "C:/ue/real_labeled")
REAL_N = int(os.environ.get("REF_N", "150"))
W, H = 1280, 720


def load_audit():
    here = os.path.dirname(os.path.abspath(__file__))
    spec = importlib.util.spec_from_file_location(
        "render_audit", os.path.join(here, "render_audit.py"))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def metrics(rgb, ra):
    """render_audit 과 **같은 정의**로 소실점 공허·과노출을 낸다."""
    lum = rgb.mean(axis=2)
    h0, h1 = int(H * 0.42), int(H * 0.62)
    mid = rgb[h0:h1].mean(axis=2)
    void = float(((ra._local_sd(mid) < ra.SKY_SMOOTH) & (mid > 0.55)).mean())
    blown = float((lum > 0.92).mean())
    return void, blown


def collect_render(roots, ra):
    void, blown = [], []
    for r in roots:
        for f in sorted(glob.glob(os.path.join(r, "scene_*.png"))):
            if "contact" in os.path.basename(f) or "plain" in os.path.basename(f):
                continue
            rgb = np.asarray(Image.open(f).convert("RGB"), dtype=np.float32) / 255.0
            v, b = metrics(rgb, ra)
            void.append(v)
            blown.append(b)
    return np.array(void), np.array(blown)


def collect_real(ra, n=REAL_N):
    import random
    fs = [f for ext in ("jpg", "jpeg", "png")
          for f in glob.glob(os.path.join(REAL_DIR, "**", "*." + ext), recursive=True)]
    random.seed(0)
    fs = random.sample(fs, min(n, len(fs)))
    void, blown = [], []
    for f in fs:
        rgb = np.asarray(Image.open(f).convert("RGB").resize((W, H), Image.LANCZOS),
                         dtype=np.float32) / 255.0
        v, b = metrics(rgb, ra)
        void.append(v)
        blown.append(b)
    return np.array(void), np.array(blown)


def ks(a, b):
    """두 표본의 KS 통계량과 근사 p — scipy 없이."""
    a, b = np.sort(a), np.sort(b)
    allv = np.concatenate([a, b])
    ca = np.searchsorted(a, allv, "right") / len(a)
    cb = np.searchsorted(b, allv, "right") / len(b)
    d = float(np.max(np.abs(ca - cb)))
    ne = len(a) * len(b) / (len(a) + len(b))
    lam = (np.sqrt(ne) + 0.12 + 0.11 / np.sqrt(ne)) * d
    p = 2 * sum((-1) ** (k - 1) * np.exp(-2 * k * k * lam * lam) for k in range(1, 101))
    return d, float(min(1.0, max(0.0, p)))


def show(name, ren, real):
    q = (10, 25, 50, 75, 90)
    print("  %s" % name)
    print("    %-8s %s" % ("", " ".join("%7s" % ("%d분위" % p) for p in q)))
    print("    %-8s %s" % ("렌더", " ".join("%6.1f%%" % (100 * np.percentile(ren, p)) for p in q)))
    print("    %-8s %s" % ("실사", " ".join("%6.1f%%" % (100 * np.percentile(real, p)) for p in q)))
    d, p = ks(ren, real)
    print("    KS D=%.3f p=%.4f  (렌더 n=%d · 실사 n=%d)" % (d, p, len(ren), len(real)))
    med_r, med_s = np.median(ren), np.median(real)
    print("    중앙값 차이 %+.1f%%p — 렌더가 실사보다 %s"
          % (100 * (med_r - med_s), "높다(더 비어 보인다)" if med_r > med_s else "낮다"))
    return d, p


def main():
    roots = sys.argv[1:]
    if not roots:
        print("렌더 디렉터리를 하나 이상 주어야 한다.")
        return 2
    ra = load_audit()
    rv, rb = collect_render(roots, ra)
    if not len(rv):
        print("렌더 없음")
        return 2
    sv, sb = collect_real(ra)
    print("풀링 비교 — 렌더 %d장 (%d개 실행) vs 실사 %d장\n" % (len(rv), len(roots), len(sv)))
    show("소실점 공허", rv, sv)
    print()
    show("과노출", rb, sb)
    print()
    print("  임계 하나로 통과/실패를 가르는 대신 분포를 본다. 목표가 «구별 불가» 이므로")
    print("  KS p 가 크면(두 분포가 구별되지 않으면) 그 축에서는 목표에 닿은 것이다.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
