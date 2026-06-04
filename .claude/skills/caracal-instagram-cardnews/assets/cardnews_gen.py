#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CARACAL Instagram 카드뉴스 PNG 생성기 (v11 — runninglife_korea/cltoo 풀블리드 스타일)
참고: instagram.com/p/DTcmiUSj5j8, instagram.com/p/DYxz-PeEyTV

핵심:
- 풀블리드 사진이 카드를 꽉 채움(잘린 느낌 X). 사진별 focus로 인물 프레이밍.
- 사진은 밝게 두고 '하단만' 그라데이션으로 어둡게 → 사진 잘 보이고 글씨도 또렷.
- 하단 왼쪽정렬: 라벨태그(pill) + 제목(키워드 *별표*=주황) + 설명. 좌상단 아이콘 + 출처표기.
- 핵심 데이터는 반투명 정보박스(infobox).
- closing = 공식 CARACAL 워드마크 + 아이콘 로고 페이지.
사용: python3 cardnews_gen.py --spec spec.json --out dir
"""
import json, os, argparse, sys
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance

WHITE = (255, 255, 255)
SUB   = (226, 226, 228)
DARK  = (18, 18, 22)
DEFAULT_ACCENT = (240, 90, 28)   # #F05A1C

W, H = 1080, 1350
MARGIN = 84
# macOS는 AppleSDGothicNeo.ttc(가중치=index)를 그대로 사용한다.
# 리눅스(예: Claude Code on the web, 모바일 세션)에는 이 폰트가 없으므로
# 나눔고딕 등 한글 폰트로 자동 폴백한다. CARACAL_FONT_TTC 환경변수로 직접 지정도 가능.
FONT_TTC = os.environ.get("CARACAL_FONT_TTC", "/System/Library/Fonts/AppleSDGothicNeo.ttc")
WEIGHT = {"regular": 0, "medium": 2, "semibold": 4, "bold": 6}
ASSET_DIR = os.path.dirname(os.path.abspath(__file__))
BRAND_DIR = os.path.join(ASSET_DIR, "brand")

def _first_existing(paths):
    for p in paths:
        if p and os.path.exists(p): return p
    return None

# 리눅스 한글 폰트 폴백(가중치별 파일).
# 우선순위: 저장소 번들 폰트(네트워크 불필요) → 시스템 나눔고딕 → 노토산스 CJK.
_BUNDLE = os.path.join(ASSET_DIR, "fonts")
_LINUX_FONT = {
    "regular":  _first_existing([os.path.join(_BUNDLE, "NanumGothic.ttf"),
                                 "/usr/share/fonts/truetype/nanum/NanumGothic.ttf",
                                 "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"]),
    "medium":   _first_existing([os.path.join(_BUNDLE, "NanumGothic.ttf"),
                                 "/usr/share/fonts/truetype/nanum/NanumGothic.ttf",
                                 "/usr/share/fonts/opentype/noto/NotoSansCJK-Medium.ttc"]),
    "semibold": _first_existing([os.path.join(_BUNDLE, "NanumGothicBold.ttf"),
                                 "/usr/share/fonts/truetype/nanum/NanumGothicBold.ttf",
                                 "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc"]),
    "bold":     _first_existing([os.path.join(_BUNDLE, "NanumGothicBold.ttf"),
                                 "/usr/share/fonts/truetype/nanum/NanumGothicBold.ttf",
                                 "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc"]),
}
_USE_TTC = os.path.exists(FONT_TTC)

def hex_to_rgb(s):
    s = s.lstrip("#"); return tuple(int(s[i:i+2], 16) for i in (0, 2, 4))

_fc = {}
def font(w, s):
    k = (w, s)
    if k not in _fc:
        if _USE_TTC:
            _fc[k] = ImageFont.truetype(FONT_TTC, s, index=WEIGHT.get(w, 0))
        else:
            path = _LINUX_FONT.get(w) or _LINUX_FONT["regular"]
            _fc[k] = ImageFont.truetype(path, s) if path else ImageFont.load_default()
    return _fc[k]

_lc = {}
def load_logo(n):
    if n not in _lc:
        p = os.path.join(BRAND_DIR, n); _lc[n] = Image.open(p).convert("RGBA") if os.path.exists(p) else None
    return _lc[n]

def tw_(d, s, f): return d.textbbox((0, 0), s, font=f)[2]
def th_(d, s, f):
    b = d.textbbox((0, 0), s, font=f); return b[3] - b[1]
def lh(d, f, lg): return int(th_(d, "가Ag", f) * lg)

def wrap(d, text, f, mw):
    out = []
    for raw in text.split("\n"):
        if raw == "": out.append(""); continue
        line = ""
        for wd in raw.split(" "):
            t = wd if line == "" else line + " " + wd
            if tw_(d, t.replace("*", ""), f) <= mw or line == "": line = t
            else: out.append(line); line = wd
        out.append(line)
    return out

def seg_parse(line):
    segs = []
    for i, p in enumerate(line.split("*")):
        if p: segs.append((p, i % 2 == 1))
    return segs or [("", False)]

def _ax(d, line_w, align):
    if align == "right": return W - MARGIN - line_w
    if align == "center": return (W - line_w) / 2
    return MARGIN

def draw_rich(d, lines, f, base_fill, accent, align, y, lg, shadow=True, underline=True):
    """키워드(*별표*)는 주황색 + 굵은 밑줄로 확실하게 강조."""
    step = lh(d, f, lg)
    asc = th_(d, "가Ag", f)
    for ln in lines:
        segs = seg_parse(ln)
        total = sum(tw_(d, t, f) for t, _ in segs)
        cx = _ax(d, total, align)
        for t, acc in segs:
            wseg = tw_(d, t, f)
            if shadow:
                d.text((cx + 2, y + 2), t, font=f, fill=(0, 0, 0))
            d.text((cx, y), t, font=f, fill=(accent if acc else base_fill))
            if acc and underline:
                uy = y + asc + 3
                d.rounded_rectangle([cx + 2, uy, cx + wseg - 2, uy + 6], radius=3, fill=accent)
            cx += wseg
        y += step
    return y

def draw_txt(d, lines, f, fill, align, y, lg, shadow=True):
    step = lh(d, f, lg)
    for ln in lines:
        x = _ax(d, tw_(d, ln, f), align)
        if shadow: d.text((x + 1, y + 1), ln, font=f, fill=(0, 0, 0))
        d.text((x, y), ln, font=f, fill=fill); y += step
    return y

# ---------- 사진 ----------
def resolve_photo(p):
    for c in (p, os.path.join(os.getcwd(), p), os.path.join(ASSET_DIR, p), os.path.join(ASSET_DIR, "photos", p)):
        if c and os.path.exists(c): return c
    return None

def cover_fit(img, w, h, focus=0.4, zoom=1.0, focus_x=0.5):
    r = max(w / img.width, h / img.height) * zoom
    img = img.resize((int(img.width * r + .5), int(img.height * r + .5)))
    maxx = img.width - w; maxy = img.height - h
    x = max(0, min(maxx, int(maxx * focus_x)))
    y = max(0, min(maxy, int(maxy * focus)))
    return img.crop((x, y, x + w, y + h))

def bottom_gradient(base, start_y, strength=248):
    """start_y 위는 밝게(사진이 먼저 시선), 아래로 갈수록 부드럽게 어두워져 글씨로 시선이 흐르게.
    완만한 곡선(t^1.5)으로 상단은 오래 밝고 하단만 진하게 → 자연스러운 흐름."""
    m = Image.new("L", (1, H), 0); mp = m.load()
    span = H - start_y
    for y in range(H):
        if y <= start_y: mp[0, y] = 0
        else:
            t = (y - start_y) / max(1, span)
            mp[0, y] = int(strength * (t ** 1.5))
    ov = Image.new("RGBA", (W, H), (8, 8, 12, 255)); ov.putalpha(m.resize((W, H)))
    base.alpha_composite(ov)

def transl_box(base, box, fill, radius, outline=None, width=0):
    ov = Image.new("RGBA", base.size, (0, 0, 0, 0))
    ImageDraw.Draw(ov).rounded_rectangle(box, radius=radius, fill=fill, outline=outline, width=width)
    base.alpha_composite(ov)

def infobox_h(d, rows):
    fl = font("bold", 27); fv = font("bold", 34); h = 28
    for _ in rows: h += lh(d, fl, 1.0) + 4 + lh(d, fv, 1.12) + 18
    return h + 4

def draw_infobox(base, rows, accent, x, y, w):
    d = ImageDraw.Draw(base); fl = font("bold", 27); fv = font("bold", 34)
    bh = infobox_h(d, rows)
    transl_box(base, [x, y, x + w, y + bh], (14, 14, 18, 200), 22, outline=accent + (235,), width=2)
    yy = y + 24
    for r in rows:
        d.text((x + 28, yy), r["label"], font=fl, fill=accent); yy += lh(d, fl, 1.0) + 4
        d.text((x + 28, yy), r["value"], font=fv, fill=WHITE); yy += lh(d, fv, 1.12) + 18
    return bh

def label_pill(base, text, accent, align, y):
    d = ImageDraw.Draw(base); f = font("bold", 25)
    tw = tw_(d, text, f); bw = tw + 44; bh = 48
    x = _ax(d, bw, align)
    transl_box(base, [x, y, x + bw, y + bh], accent + (255,), bh / 2)
    d.text((x + 22, y + bh / 2 - th_(d, text, f) / 2 - 3), text, font=f, fill=WHITE)
    return bh

def watermark_tl(base):
    ic = load_logo("icon_white.png")
    if ic is None: return
    hh = 50; r = hh / ic.height; icr = ic.resize((int(ic.width * r), hh))
    a = icr.getchannel("A").point(lambda v: int(v * 0.96)); icr.putalpha(a)
    base.paste(icr, (MARGIN, MARGIN - 22), icr)

# ---------- 레이아웃 ----------
def render_fullbleed(base, s, accent, is_cover):
    mw = W - 2 * MARGIN
    d = ImageDraw.Draw(base)
    pill = s.get("kicker", "")
    fh = font("bold", 78 if is_cover else 60)
    head = wrap(d, s.get("headline", ""), fh, mw)
    while head and max(tw_(d, ln.replace("*", ""), fh) for ln in head) > mw and fh.size > 42:
        fh = font("bold", fh.size - 4); head = wrap(d, s.get("headline", ""), fh, mw)
    fb = font("medium", 35) if is_cover else font("regular", 34)
    body = wrap(d, s.get("subtitle" if is_cover else "body", ""), fb, mw) if s.get("subtitle" if is_cover else "body") else []
    rows = s.get("infobox") or []
    box_w = mw

    GAP_PILL, GAP_BODY, GAP_BOX = 30, 24, 28
    bh_pill = (48 + GAP_PILL) if pill else 0
    bh_head = lh(d, fh, 1.2) * len(head)
    bh_body = (GAP_BODY + lh(d, fb, 1.46) * len(body)) if body else 0
    bh_box = (GAP_BOX + infobox_h(d, rows)) if rows else 0
    total = bh_pill + bh_head + bh_body + bh_box
    bottom = H - 84
    y0 = bottom - total
    bottom_gradient(base, max(330, int(y0 - 210)))   # 더 위에서부터 완만히 → 사진→글씨 자연스런 흐름
    d = ImageDraw.Draw(base)
    align = s.get("align", "left")
    y = y0
    if pill:
        label_pill(base, pill, accent, align, y); y += 48 + GAP_PILL; d = ImageDraw.Draw(base)
    y = draw_rich(d, head, fh, WHITE, accent, align, y, 1.2)
    if body:
        y = draw_txt(d, body, fb, SUB, align, y + GAP_BODY, 1.46)
    if rows:
        bx = _ax(d, box_w, align) if align != "left" else MARGIN
        draw_infobox(base, rows, accent, bx, y + GAP_BOX, box_w)
    watermark_tl(base)
    if s.get("source"):
        d.text((MARGIN, MARGIN + 40), s["source"], font=font("regular", 19), fill=(225, 225, 228))

def render_closing(base, s, accent):
    d = ImageDraw.Draw(base); CXc = W // 2; icon = load_logo("icon_white.png"); top = 250
    if icon is not None:
        ih = 300; r = ih / icon.height; ic = icon.resize((int(icon.width * r), ih))
        base.paste(ic, (CXc - ic.width // 2, top), ic); y = top + ih + 34
    else: y = 470
    wm = load_logo("wordmark_official_white.png")
    if wm is not None:
        ww = 500; r = ww / wm.width; wmi = wm.resize((ww, int(wm.height * r)))
        base.paste(wmi, (CXc - ww // 2, y), wmi); y += int(wm.height * r) + 28
    fs = font("bold", 27)
    d.text((CXc - tw_(d, "WE SUPPORT ALL THE PLAYERS", fs) / 2, y), "WE SUPPORT ALL THE PLAYERS", font=fs, fill=accent); y += 60
    d.rectangle([CXc - 36, y, CXc + 36, y + 6], fill=accent); y += 46
    if s.get("subtitle"):
        fsu = font("medium", 37)
        for ln in wrap(d, s["subtitle"], fsu, W - 2 * MARGIN):
            d.text((CXc - tw_(d, ln, fsu) / 2, y), ln, font=fsu, fill=SUB); y += lh(d, fsu, 1.36)
    handle = s.get("handle", "@caracal_supply"); cta = s.get("cta", "프로필 링크 → 네이버 스마트스토어")
    fh = font("bold", 41); d.text((CXc - tw_(d, handle, fh) / 2, H - MARGIN - 150), handle, font=fh, fill=WHITE)
    fc = font("medium", 33); d.text((CXc - tw_(d, cta, fc) / 2, H - MARGIN - 92), cta, font=fc, fill=accent)

def page_badge(base, idx, total):
    d = ImageDraw.Draw(base); f = font("bold", 26); s = f"{idx:02d} / {total:02d}"
    d.text((W - MARGIN - tw_(d, s, f) + 1, MARGIN - 21), s, font=f, fill=(0, 0, 0))
    d.text((W - MARGIN - tw_(d, s, f), MARGIN - 22), s, font=f, fill=WHITE)

def build(spec, out_dir):
    accent = hex_to_rgb(spec["accent"]) if isinstance(spec.get("accent"), str) else DEFAULT_ACCENT
    slides = spec["slides"]; total = len(slides); os.makedirs(out_dir, exist_ok=True); paths = []
    for i, s in enumerate(slides, 1):
        layout = s.get("layout", "photo")
        pp = resolve_photo(s.get("photo")) if s.get("photo") else None
        if s.get("photo") and not pp: print(f"  [경고] 사진 못 찾음: {s.get('photo')}", file=sys.stderr)
        if layout == "closing":
            base = Image.new("RGBA", (W, H), DARK + (255,)); render_closing(base, s, accent)
        elif pp:
            base = cover_fit(Image.open(pp).convert("RGB"), W, H, float(s.get("focus", 0.4)), float(s.get("zoom", 1.0)), float(s.get("focus_x", 0.5))).convert("RGBA")
            render_fullbleed(base, s, accent, layout == "cover"); page_badge(base, i, total)
        else:
            base = Image.new("RGBA", (W, H), DARK + (255,)); render_fullbleed(base, s, accent, layout == "cover"); page_badge(base, i, total)
        p = os.path.join(out_dir, f"slide_{i:02d}.png"); base.convert("RGB").save(p, "PNG"); paths.append(p)
    return paths

def main():
    global H
    ap = argparse.ArgumentParser(); ap.add_argument("--spec"); ap.add_argument("--out", required=True)
    ap.add_argument("--height", type=int, default=1350, help="1350=피드(4:5), 1920=릴스(9:16)")
    a = ap.parse_args()
    H = a.height
    spec = json.load(open(a.spec, encoding="utf-8")) if a.spec else json.load(sys.stdin)
    for p in build(spec, a.out): print(" -", p)

if __name__ == "__main__":
    main()
