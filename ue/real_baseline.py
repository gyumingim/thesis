"""판정 임계를 **실사 분포에서** 뽑는다 — 내가 고른 숫자가 아니라.

계기(2026-09-06): render_audit 의 임계(과노출 5%, 소실점 공허 8%)는 전부 내가 눈대중으로
정한 값이었다. 실사 150장(Udacity CrowdAI)에 같은 지표를 돌려 보니 둘 다 **실사가 지키지
못하는 기준**이었다:

  * 과노출: 실사 중앙 7.0% · 90분위 14.0%. 임계 5% 는 실사가 절반 이상 위반한다.
    우리 렌더의 평균 최대 과노출은 4.56% 이므로 **오히려 실사보다 덜 탄다**.
  * 소실점 공허: 실사 중앙 3.4% · 90분위 10.0% · 최대 18.9%. 최대값에 8% 를 걸면
    실사도 자주 실패한다. 최대가 아니라 **중앙값**으로 비교해야 한다.

"평범한 실사와 구별 불가" 가 목표라면 임계는 실사 분포에서 와야 한다. 이 도구가 그 분포를
출력하고 권장 임계를 제안한다.

**한계**: 참조 집합(Udacity CrowdAI)은 캘리포니아 간선도로/고속도로라 하늘이 넓게 열려
있고, 우리 장면은 도심 협곡이라 하늘이 좁다. 소실점·하늘 지표는 이 구성 차이에 민감하므로
여기서 나온 값은 **방향과 크기의 참고**이지 그대로 옮길 수치가 아니다(§6.4 의 도메인 갭과
같은 주의). 그래도 «내가 고른 숫자» 보다는 낫다.

실행: python ue/real_baseline.py [참조 디렉터리] [표본 수]
"""
import glob
import importlib.util
import os
import random
import sys

import numpy as np
from PIL import Image

W, H = 1280, 720


def load_audit():
    here = os.path.dirname(os.path.abspath(__file__))
    spec = importlib.util.spec_from_file_location(
        "render_audit", os.path.join(here, "render_audit.py"))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def main():
    root = sys.argv[1] if len(sys.argv) > 1 else "C:/ue/real_labeled"
    n = int(sys.argv[2]) if len(sys.argv) > 2 else 150
    ra = load_audit()
    fs = [f for ext in ("jpg", "jpeg", "png")
          for f in glob.glob(os.path.join(root, "**", "*." + ext), recursive=True)]
    if not fs:
        print("참조 이미지 없음:", root)
        return 2
    random.seed(0)
    fs = random.sample(fs, min(n, len(fs)))

    void, blown, skybr = [], [], []
    for f in fs:
        rgb = np.asarray(Image.open(f).convert("RGB").resize((W, H), Image.LANCZOS),
                         dtype=np.float32) / 255.0
        lum = rgb.mean(axis=2)
        blown.append(float((lum > 0.92).mean()))
        h0, h1 = int(H * 0.42), int(H * 0.62)
        mid = rgb[h0:h1].mean(axis=2)
        void.append(float(((ra._local_sd(mid) < ra.SKY_SMOOTH) & (mid > 0.55)).mean()))
        band = rgb[:int(H * ra.SKY_BAND)]
        bl = band.mean(axis=2)
        st = ra._local_sd(bl) > ra.SKY_SMOOTH
        first = np.where(st.any(axis=0), st.argmax(axis=0), band.shape[0])
        m = (np.arange(band.shape[0])[:, None] < first[None, :]) & ~st
        if m.sum() > 300:
            sk = band[m]
            skybr.append(float(np.median(sk[:, 2] - sk[:, 0])))

    def pc(a, p):
        return float(np.percentile(a, p))

    print("참조 실사 %d장 (%s)" % (len(fs), root))
    print("  %-12s %8s %8s %8s %8s" % ("지표", "중앙", "75분위", "90분위", "최대"))
    for name, arr, scale in (("소실점 공허", void, 100), ("과노출", blown, 100)):
        print("  %-12s %7.1f%% %7.1f%% %7.1f%% %7.1f%%"
              % (name, scale * pc(arr, 50), scale * pc(arr, 75),
                 scale * pc(arr, 90), scale * max(arr)))
    print("  %-12s %+7.3f %+7.3f %+7.3f %+7.3f  (하늘 있는 %d장)"
          % ("하늘 B−R", pc(skybr, 50), pc(skybr, 75), pc(skybr, 90), max(skybr), len(skybr)))
    print()
    print("권장 임계 (실사 90분위 = «실사 10장 중 1장은 이보다 나쁘다» 지점)")
    print("  소실점 공허 — **최대가 아니라 중앙값**으로 비교하고 임계 %.1f%%" % (100 * pc(void, 75)))
    print("     (최대값 판정은 실사도 자주 실패한다: 실사 최대 %.1f%%)" % (100 * max(void)))
    print("  과노출     — 임계 %.1f%%  (현행 5%% 는 실사 중앙 %.1f%% 보다 엄격하다)"
          % (100 * pc(void and blown, 90), 100 * pc(blown, 50)))
    print()
    print("  주의: 참조는 간선도로라 하늘이 넓고 우리 장면은 도심 협곡이라 좁다.")
    print("  방향과 크기의 참고로만 쓰고, 그대로 옮기지 마라(§6.4 도메인 갭과 같은 주의).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
