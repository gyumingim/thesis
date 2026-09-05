"""검증 렌더 컨택트 시트 — 사용자 육안 판정에 넘길 한 장을 만든다.

**대량 생성 게이트가 이 산출물에 달려 있다**(STATUS «자율 운행 재개 지침»). 판정 기준은
"예쁜 사진"이 아니라 **"평범한 실사와 구별 불가"** 이므로, 시트는 장면을 미화하지 않고
있는 그대로 붙이고 라벨 상자만 겹친다.

상자 색은 가시비로 가른다 — 초록 = 잘 보임(>0.3), 노랑 = 부분 가림(0.3 이하), 회색 =
완전 가림(ignore). 회색이 많은 것은 결함이 아니라 6차로에 차량이 겹쳐 선 결과다.

실행: python ue/contact_sheet.py [입력 디렉터리] [출력 png] [열 수]
"""
import glob
import io
import json
import math
import os
import sys

from PIL import Image, ImageDraw, ImageFont

TILE_W = 900
FONTS = ("C:/Windows/Fonts/malgun.ttf", "C:/Windows/Fonts/arial.ttf")


def load_font(size):
    for f in FONTS:
        try:
            return ImageFont.truetype(f, size)
        except Exception:
            continue
    return ImageFont.load_default()


def main():
    root = sys.argv[1] if len(sys.argv) > 1 else "C:/ue/verify10"
    out = sys.argv[2] if len(sys.argv) > 2 else os.path.join(root, "contact_sheet.png")
    cols = int(sys.argv[3]) if len(sys.argv) > 3 else 2

    files = sorted(glob.glob(os.path.join(root, "scene_*.png")),
                   key=lambda f: int(os.path.basename(f)[6:-4]))
    files = [f for f in files if "contact" not in os.path.basename(f)]
    if not files:
        print("렌더 없음:", root)
        return 2
    font, small = load_font(20), load_font(15)

    tiles = []
    for f in files:
        im = Image.open(f).convert("RGB")
        j = f[:-4] + ".json"
        meta = json.load(io.open(j, encoding="utf-8")) if os.path.exists(j) else {}
        d = ImageDraw.Draw(im)
        clear = 0
        for lb in meta.get("vehicles", []):
            b = lb.get("bbox2d")
            if not b:
                continue
            vis = lb.get("visibility", 1.0)
            if vis <= 0.001:
                col, w = (95, 95, 95), 1
            elif vis <= 0.3:
                col, w = (255, 190, 40), 2
            else:
                col, w = (60, 235, 110), 2
                clear += 1
            d.rectangle(b, outline=col, width=w)
        wx = meta.get("weather", {})
        hdr = "#%s  %s  태양 %.1f  안개 %.4f  가로등 %s  |  라벨 %d (선명 %d)" % (
            os.path.basename(f)[6:-4], wx.get("preset", "?"),
            wx.get("sun_intensity", 0.0), wx.get("fog_density", 0.0),
            "켬" if wx.get("lamps") else "끔",
            len(meta.get("vehicles", [])), clear)
        d.rectangle([0, 0, im.width, 30], fill=(0, 0, 0))
        d.text((8, 5), hdr, fill=(255, 255, 255), font=font)
        im = im.resize((TILE_W, int(im.height * TILE_W / im.width)), Image.LANCZOS)
        tiles.append(im)

    tw, th = tiles[0].size
    rows = math.ceil(len(tiles) / cols)
    sheet = Image.new("RGB", (cols * tw, rows * th + 34), (18, 18, 20))
    for i, t in enumerate(tiles):
        sheet.paste(t, ((i % cols) * tw, (i // cols) * th))
    d = ImageDraw.Draw(sheet)
    d.text((10, rows * th + 9),
           "초록 = 가시비>0.3 · 노랑 = 부분 가림 · 회색 = 완전 가림(ignore, GT 는 보존)",
           fill=(190, 190, 195), font=small)
    sheet.save(out)
    print("저장 %s  %dx%d  (%d장)" % (out, sheet.size[0], sheet.size[1], len(tiles)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
