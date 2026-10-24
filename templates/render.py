"""Рендер постов 1080x1350 в стиле Агентства Добрых Дел - 11 разных макетов.

Запуск:  python3 -I templates/render.py config.json out.jpg
Каталог макетов с примерами конфигов: templates/LAYOUTS.md

Общие поля конфига:
  layout   - stat | dark | marquee | checklist | myth | compare | quote | chat | pixel | steps | news
  label    - текст метки справа сверху (напр. "РАЗБОР МИФА")
  title    - заголовок; [[слово]] = акцент; \\n = принудительный перенос
  accent   - доп. цвет: violet | orange | cyan | mint | pink
  icon     - пиксельная иконка: star check cross chart search chat phone target bolt eye coin
             clock mail play megaphone trophy cursor heart arrow bag bulb
  source   - подпись источника внизу
  ribbon   - слова для бегущей строки ["SEO", "РЕКЛАМА"]
Поля конкретных макетов - в LAYOUTS.md.
"""
import hashlib
import json
import math
import os
import random
import re
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, ".."))
FD = os.path.join(ROOT, "assets", "fonts")
S = 2
W, H = 1080, 1350
M = 72

INK = (12, 16, 28)
MUTED = (98, 108, 128)
V1 = (94, 22, 234)
V2 = (123, 56, 242)
LILAC = (196, 170, 255)
LAV = (243, 238, 253)
BG = (244, 247, 252)
NAVY = (11, 18, 32)
WHITE = (255, 255, 255)
RED = (234, 61, 73)
GREEN = (16, 185, 129)
YELLOW = (250, 204, 21)
ACCENTS = {"violet": (123, 56, 242), "orange": (247, 147, 30), "cyan": (34, 166, 224),
           "mint": (16, 185, 129), "pink": (236, 72, 153)}

FONT_FILES = {"serif": "PlayfairDisplay[wght].ttf", "serif_i": "PlayfairDisplay-Italic[wght].ttf",
              "sans": "Manrope[wght].ttf", "jost": "Jost[wght].ttf", "pixel": "PressStart2P-Regular.ttf"}
_fc = {}


def px(v):
    return int(round(v * S))


def font(kind, size, w=None):
    key = (kind, int(size * S), w)
    if key not in _fc:
        f = ImageFont.truetype(os.path.join(FD, FONT_FILES[kind]), int(size * S))
        if w is not None and kind != "pixel":
            f.set_variation_by_axes([w])
        _fc[key] = f
    return _fc[key]


def mix(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


class Fail(SystemExit):
    pass


# ---------------------------------------------------------------- canvas
class C:
    def __init__(self, bg):
        self.im = Image.new("RGBA", (W * S, H * S), tuple(bg) + (255,))
        self.d = ImageDraw.Draw(self.im)

    def refresh(self):
        self.d = ImageDraw.Draw(self.im)

    def layer(self):
        return Image.new("RGBA", self.im.size, (0, 0, 0, 0))

    def over(self, L):
        self.im = Image.alpha_composite(self.im, L)
        self.refresh()

    def paste(self, img, x, y):
        """alpha-composite img at supersampled coords (may be negative / off-canvas)"""
        x, y = int(x), int(y)
        sx0, sy0 = max(0, -x), max(0, -y)
        dx0, dy0 = max(0, x), max(0, y)
        w = min(img.width - sx0, self.im.width - dx0)
        h = min(img.height - sy0, self.im.height - dy0)
        if w <= 0 or h <= 0:
            return
        self.im.alpha_composite(img.crop((sx0, sy0, sx0 + w, sy0 + h)), (dx0, dy0))
        self.refresh()

    def tw(self, s, f):
        return self.d.textlength(s, font=f) / S

    def text(self, x, y, s, f, fill, anchor="la", sp=0.0):
        if not sp:
            self.d.text((px(x), px(y)), s, font=f, fill=fill, anchor=anchor)
            return self.tw(s, f)
        total = sum(self.tw(ch, f) + sp for ch in s) - sp
        if anchor[0] == "r":
            x -= total
        elif anchor[0] == "m":
            x -= total / 2
        a2 = "l" + anchor[1]
        cx = x
        for ch in s:
            self.d.text((px(cx), px(y)), ch, font=f, fill=fill, anchor=a2)
            cx += self.tw(ch, f) + sp
        return total

    def save(self, path):
        self.im.convert("RGB").resize((W, H), Image.LANCZOS).save(path, quality=93)


# ---------------------------------------------------------------- backgrounds
def lin_grad(w, h, c1, c2, angle=0.0):
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    a = math.radians(angle)
    t = (xx * math.cos(a) + yy * math.sin(a))
    t = (t - t.min()) / max(1e-6, (t.max() - t.min()))
    arr = np.array(c1, np.float32) * (1 - t[..., None]) + np.array(c2, np.float32) * t[..., None]
    return Image.fromarray(arr.clip(0, 255).astype(np.uint8)).convert("RGBA")


def bg_grad(c, c1, c2, angle=35):
    g = lin_grad(W // 4, H // 4, c1, c2, angle).resize(c.im.size, Image.BILINEAR)
    c.im = g
    c.refresh()


def glow(c, cx, cy, r, color, a):
    sw, sh = W // 4, H // 4
    yy, xx = np.mgrid[0:sh, 0:sw].astype(np.float32)
    dd = np.sqrt((xx - cx / 4) ** 2 + (yy - cy / 4) ** 2) / (r / 4)
    al = (np.clip(1 - dd, 0, 1) ** 2 * a * 255).astype(np.uint8)
    A = Image.fromarray(al, "L").resize(c.im.size, Image.BILINEAR)
    L = Image.new("RGBA", c.im.size, tuple(color) + (0,))
    L.putalpha(A)
    c.over(L)


def dots(c, color, step=40, r=1.6, alpha=255):
    L = c.layer()
    d = ImageDraw.Draw(L)
    for gx in range(step, W, step):
        for gy in range(step, H, step):
            d.ellipse([px(gx - r), px(gy - r), px(gx + r), px(gy + r)], fill=tuple(color) + (alpha,))
    c.over(L)


def shadow(c, box, r=36, color=(70, 40, 160), alpha=46, blur=22, dy=14):
    x0, y0, x1, y1 = box
    pad = blur * 3
    w, h = px(x1 - x0 + 2 * pad), px(y1 - y0 + 2 * pad + dy)
    L = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    ImageDraw.Draw(L).rounded_rectangle([px(pad), px(pad + dy), px(pad + x1 - x0), px(pad + y1 - y0 + dy)],
                                        radius=px(r), fill=tuple(color) + (alpha,))
    L = L.filter(ImageFilter.GaussianBlur(px(blur)))
    c.paste(L, px(x0 - pad), px(y0 - pad))


def card(c, box, r=36, fill=WHITE, sh=True, outline=None, ow=2, grad=None):
    if sh:
        shadow(c, box, r)
    x0, y0, x1, y1 = box
    if grad:
        g = lin_grad(px(x1 - x0), px(y1 - y0), grad[0], grad[1], grad[2] if len(grad) > 2 else 30)
        m = Image.new("L", g.size, 0)
        ImageDraw.Draw(m).rounded_rectangle([0, 0, g.width - 1, g.height - 1], radius=px(r), fill=255)
        g.putalpha(m)
        c.paste(g, px(x0), px(y0))
    else:
        c.d.rounded_rectangle([px(x0), px(y0), px(x1), px(y1)], radius=px(r), fill=fill,
                              outline=outline, width=px(ow) if outline else 0)


def grad_text(c, x, y_top, s, f, c1, c2):
    tmp = ImageDraw.Draw(Image.new("L", (1, 1)))
    bb = tmp.textbbox((0, 0), s, font=f)
    w, h = bb[2] - bb[0], bb[3] - bb[1]
    m = Image.new("L", (w + 4, h + 4), 0)
    ImageDraw.Draw(m).text((2 - bb[0], 2 - bb[1]), s, font=f, fill=255)
    g = lin_grad(w + 4, h + 4, c1, c2, 20)
    g.putalpha(m)
    c.paste(g, px(x), px(y_top))
    return w / S, h / S


def outline_text(c, x, y, s, f, color, alpha, sw=3, anchor="la"):
    L = c.layer()
    d = ImageDraw.Draw(L)
    d.text((px(x), px(y)), s, font=f, fill=tuple(color) + (alpha,), stroke_width=px(sw),
           stroke_fill=tuple(color) + (alpha,), anchor=anchor)
    m = Image.new("L", c.im.size, 0)
    ImageDraw.Draw(m).text((px(x), px(y)), s, font=f, fill=255, anchor=anchor)
    a = np.array(L.split()[3], np.int16) - np.array(m, np.int16)
    L.putalpha(Image.fromarray(a.clip(0, 255).astype(np.uint8)))
    c.over(L)


# ---------------------------------------------------------------- rich text
def tokens(s):
    """list of (word, hot, glue). glue=True: attach to previous word without space"""
    out = []
    prev = ""
    for part in re.split(r"(\[\[.*?\]\])", s):
        if not part:
            continue
        hot = part.startswith("[[")
        p = part[2:-2] if hot else part
        lead_glue = bool(out) and not p[:1].isspace() and not prev[-1:].isspace()
        prev = p
        for i, line in enumerate(p.split("\n")):
            if i > 0:
                out.append(("\n", False, False))
                lead_glue = False
            for k, w in enumerate(line.split()):
                g = lead_glue and i == 0 and k == 0 and not line[:1].isspace()
                out.append((w, hot, g))
    return out


def wrap_tokens(c, toks, f, maxw):
    lines, cur = [[]], 0.0
    sp = c.tw(" ", f)
    for w, h, g in toks:
        if w == "\n":
            lines.append([])
            cur = 0
            continue
        ww = c.tw(w, f)
        gap = 0 if (g or not lines[-1]) else sp
        if lines[-1] and not g and cur + gap + ww > maxw:
            lines.append([])
            cur = 0
            gap = 0
        cur += gap + ww
        lines[-1].append((w, h, g))
    return [l for l in lines if l]


def line_w(c, line, f):
    sp = c.tw(" ", f)
    return sum(c.tw(w, f) for w, _, _ in line) + sp * sum(1 for j, (_, _, g) in enumerate(line) if j and not g)


def fit(c, s, kind, wght, maxw, maxh, smax, smin=24, lh=1.12, max_lines=None):
    toks = tokens(s)
    for size in range(int(smax), int(smin) - 1, -2):
        f = font(kind, size, wght)
        lines = wrap_tokens(c, toks, f, maxw)
        if (max(line_w(c, l, f) for l in lines) <= maxw and len(lines) * size * lh <= maxh
                and (max_lines is None or len(lines) <= max_lines)):
            return size, f, lines
    raise Fail(f"Текст не влезает: «{s[:60]}». Сократи его.")


def plain_wrap(c, s, f, maxw):
    return ["".join((w if (j == 0 or g) else " " + w) for j, (w, _, g) in enumerate(l))
            for l in wrap_tokens(c, tokens(s), f, maxw)]


def draw_rich(c, lines, f, size, x, y, color, hot, style="color", lh=1.12, align="l", maxw=936, deco=None):
    """returns bottom y. style: color | underline | marker | box"""
    sp = c.tw(" ", f)
    deco = deco or hot
    words, spans = [], []
    for i, line in enumerate(lines):
        lw = line_w(c, line, f)
        cx = x if align == "l" else (x + (maxw - lw) / 2 if align == "m" else x + maxw - lw)
        base = y + i * size * lh + size * 0.92
        span = None
        for j, (w, h, g) in enumerate(line):
            if g and j:
                cx -= sp
            ww = c.tw(w, f)
            words.append((cx, base, w, h))
            if h:
                if span is None:
                    span = [cx, cx + ww, base]
                else:
                    span[1] = cx + ww
            else:
                if span:
                    spans.append(span)
                span = None
            cx += ww + sp
        if span:
            spans.append(span)
    if style == "marker":
        L = c.layer()
        d = ImageDraw.Draw(L)
        for x0, x1, b in spans:
            d.rounded_rectangle([px(x0 - 8), px(b - size * 0.42), px(x1 + 8), px(b + size * 0.14)],
                                radius=px(size * 0.12), fill=tuple(deco) + (110,))
        c.over(L)
    if style == "box":
        for x0, x1, b in spans:
            c.d.rounded_rectangle([px(x0 - 14), px(b - size * 0.86), px(x1 + 14), px(b + size * 0.28)],
                                  radius=px(size * 0.3), outline=deco, width=px(4))
    for cx, base, w, h in words:
        c.d.text((px(cx), px(base)), w, font=f, fill=hot if h else color, anchor="ls")
    if style == "underline":
        for x0, x1, b in spans:
            pts = [(px(x0 + (x1 - x0) * i / 40), px(b + size * 0.16 + 3 * math.sin(i / 40 * 6.3))) for i in range(41)]
            c.d.line(pts, fill=deco, width=px(max(4, size * 0.07)), joint="curve")
    return y + len(lines) * size * lh


def para(c, s, f, size, x, y, color, maxw, lh=1.35, max_lines=None, align="l"):
    ls = plain_wrap(c, s, f, maxw)
    if max_lines and len(ls) > max_lines:
        raise Fail(f"Слишком длинный текст: «{s[:50]}»")
    for i, l in enumerate(ls):
        if align == "m":
            c.text(x + maxw / 2, y + i * size * lh, l, f, color, anchor="ma")
        else:
            c.text(x, y + i * size * lh, l, f, color)
    return y + len(ls) * size * lh


# ---------------------------------------------------------------- brand elements
_LOGO = {}


def logo_img(dark=False):
    if dark not in _LOGO:
        im = Image.open(os.path.join(ROOT, "assets", "logo_grid.png")).convert("RGBA")
        if dark:
            a = np.array(im)
            blk = (a[..., 0] < 30) & (a[..., 1] < 30) & (a[..., 2] < 30) & (a[..., 3] > 0)
            a[blk, :3] = 255
            im = Image.fromarray(a)
        _LOGO[dark] = im
    return _LOGO[dark]


def logo(c, x=M, y=62, scale=2, dark=False):
    im = logo_img(dark)
    c.paste(im.resize((im.width * scale * S, im.height * scale * S), Image.NEAREST), px(x), px(y))


def pill(c, x, y, s, fg, bg=None, outline=None, size=17, right=False, h=44, dot=None, kind="sans", w8=700):
    f = font(kind, size, w8 if kind != "pixel" else None)
    sp = size * 0.08
    tw = sum(c.tw(ch, f) + sp for ch in s) - sp
    dw = 22 if dot else 0
    width = tw + 44 + dw
    x0 = x - width if right else x
    box = [px(x0), px(y), px(x0 + width), px(y + h)]
    if bg:
        c.d.rounded_rectangle(box, radius=px(h / 2), fill=bg)
    if outline:
        c.d.rounded_rectangle(box, radius=px(h / 2), outline=outline, width=px(2))
    if dot:
        c.d.ellipse([px(x0 + 20), px(y + h / 2 - 5), px(x0 + 30), px(y + h / 2 + 5)], fill=dot)
    c.text(x0 + 22 + dw, y + h / 2, s, f, fg, anchor="lm", sp=sp)
    return width


def kicker(c, x, y, s, color, size=18):
    c.d.ellipse([px(x), px(y + 5), px(x + 10), px(y + 15)], fill=color)
    return c.text(x + 22, y + 10, s, font("sans", size, 800), color, anchor="lm", sp=size * 0.12) + 22


def band(c, y0, y1, bg, fg, words, star=None):
    if isinstance(bg, tuple) and len(bg) == 2 and isinstance(bg[0], tuple):
        g = lin_grad(px(W), px(y1 - y0), bg[0], bg[1], 0)
        c.paste(g, 0, px(y0))
    else:
        c.d.rectangle([0, px(y0), px(W), px(y1)], fill=bg)
    f = font("sans", 26, 800)
    mid = (y0 + y1) / 2
    x, i = -60, 0
    while x < W + 20:
        x += c.text(x, mid, words[i % len(words)], f, fg, anchor="lm", sp=1.5) + 30
        star4(c, x + 10, mid, 11, star or fg)
        x += 50
        i += 1


def star4(c, cx, cy, r, color):
    k = r * 0.28
    pts = [(cx, cy - r), (cx + k, cy - k), (cx + r, cy), (cx + k, cy + k),
           (cx, cy + r), (cx - k, cy + k), (cx - r, cy), (cx - k, cy - k)]
    c.d.polygon([(px(a), px(b)) for a, b in pts], fill=color)


def footer_site(c, y, color, line=None, left=None):
    if line:
        c.d.line([px(M), px(y - 26), px(W - M), px(y - 26)], fill=line, width=px(1.5))
    f = font("sans", 20, 700)
    if left:
        c.text(M, y, left, f, color, anchor="lm", sp=1.2)
    w = c.text(W - M - 52, y, "dobroe.agency", f, color, anchor="rm", sp=0.5)
    c.d.ellipse([px(W - M - 40), px(y - 20), px(W - M), px(y + 20)], outline=color, width=px(2))
    arrow_ne(c, W - M - 20, y, 8, color)


def arrow_ne(c, cx, cy, r, color, w=2.5):
    c.d.line([px(cx - r), px(cy + r), px(cx + r), px(cy - r)], fill=color, width=px(w))
    c.d.line([px(cx - r * 0.2), px(cy - r), px(cx + r), px(cy - r), px(cx + r), px(cy + r * 0.2)], fill=color,
             width=px(w), joint="curve")


def source(c, s, y=1218, color=MUTED, x=M):
    if s:
        c.text(x, y, s, font("sans", 19, 500), color)


# ---------------------------------------------------------------- pixel icons
OUT = (34, 20, 56)


def _neigh(m):
    p = np.pad(m, 1)
    return p[1:-1, 2:], p[1:-1, :-2], p[2:, 1:-1], p[:-2, 1:-1]  # right, left, down, up


def _compose(mask, color, details=(), n=20):
    m = mask > 0
    r, l, d, u = _neigh(m)
    dark = m & (~r | ~d)
    light = m & (~l | ~u) & ~dark
    outl = (r | l | d | u | m) & ~m
    out = np.zeros((n, n, 4), np.uint8)
    out[outl] = OUT + (255,)
    out[m] = tuple(color) + (255,)
    out[dark] = mix(color, (0, 0, 0), 0.28) + (255,)
    out[light] = mix(color, (255, 255, 255), 0.45) + (255,)
    for dm, dc in details:
        dmm = np.array(dm) > 0
        out[dmm] = tuple(dc) + (255,)
    return Image.fromarray(out, "RGBA")


def icon(name, color=V2):
    n = 20
    m = Image.new("L", (n, n), 0)
    d = ImageDraw.Draw(m)
    det = []

    def layer():
        L = Image.new("L", (n, n), 0)
        return L, ImageDraw.Draw(L)

    W_ = (255, 255, 255)
    if name == "heart":
        im = logo_img(False).crop((0, 0, 30, 26)).resize((15, 13), Image.NEAREST)
        return im
    if name == "star":
        pts = []
        for i in range(10):
            ang = -math.pi / 2 + i * math.pi / 5
            rr = 9 if i % 2 == 0 else 3.8
            pts.append((9.5 + rr * math.cos(ang), 10.5 + rr * math.sin(ang)))
        d.polygon(pts, fill=255)
    elif name == "check":
        d.line([(3, 10), (8, 15), (17, 4)], fill=255, width=4)
    elif name == "cross":
        d.line([(4, 4), (15, 15)], fill=255, width=4)
        d.line([(15, 4), (4, 15)], fill=255, width=4)
    elif name == "chart":
        for r_ in [(2, 12, 5, 17), (7, 8, 10, 17), (12, 3, 15, 17)]:
            d.rectangle(r_, fill=255)
        L, dl = layer()
        dl.line([(2, 9), (7, 5), (12, 1)], fill=255)
        det.append((L, YELLOW))
    elif name == "search":
        d.ellipse((1, 1, 13, 13), fill=255)
        d.line([(11, 11), (17, 17)], fill=255, width=3)
        L, dl = layer()
        dl.ellipse((4, 4, 10, 10), fill=255)
        det.append((L, (190, 232, 255)))
        L2, dl2 = layer()
        dl2.point([(5, 6), (6, 5)], fill=255)
        det.append((L2, W_))
    elif name == "chat":
        d.rounded_rectangle((1, 2, 18, 13), radius=3, fill=255)
        d.polygon([(4, 13), (9, 13), (3, 17)], fill=255)
        L, dl = layer()
        for x in (5, 9, 13):
            dl.rectangle((x, 7, x + 1, 8), fill=255)
        det.append((L, W_))
    elif name == "phone":
        d.rounded_rectangle((5, 1, 14, 18), radius=2, fill=255)
        L, dl = layer()
        dl.rectangle((7, 3, 12, 14), fill=255)
        det.append((L, (220, 235, 255)))
        L2, dl2 = layer()
        dl2.rectangle((9, 16, 10, 16), fill=255)
        det.append((L2, W_))
    elif name == "target":
        d.ellipse((1, 1, 18, 18), fill=255)
        L, dl = layer()
        dl.ellipse((4, 4, 15, 15), fill=255)
        det.append((L, W_))
        L2, dl2 = layer()
        dl2.ellipse((7, 7, 12, 12), fill=255)
        det.append((L2, color))
        L3, dl3 = layer()
        dl3.rectangle((9, 9, 10, 10), fill=255)
        det.append((L3, W_))
    elif name == "bolt":
        d.polygon([(12, 1), (4, 11), (9, 11), (7, 18), (15, 7), (10, 7), (13, 1)], fill=255)
    elif name == "eye":
        d.ellipse((1, 5, 18, 14), fill=255)
        L, dl = layer()
        dl.ellipse((6, 5, 13, 14), fill=255)
        det.append((L, OUT))
        L2, dl2 = layer()
        dl2.rectangle((8, 7, 9, 8), fill=255)
        det.append((L2, W_))
    elif name == "coin":
        d.ellipse((2, 2, 17, 17), fill=255)
        L, dl = layer()
        dl.ellipse((5, 5, 14, 14), outline=255)
        dl.rectangle((9, 7, 10, 12), fill=255)
        det.append((L, mix(color, W_, 0.55)))
    elif name == "clock":
        d.ellipse((1, 1, 18, 18), fill=255)
        L, dl = layer()
        dl.ellipse((3, 3, 16, 16), fill=255)
        det.append((L, W_))
        L2, dl2 = layer()
        dl2.line([(9, 5), (9, 10), (13, 12)], fill=255)
        det.append((L2, OUT))
    elif name == "mail":
        d.rectangle((1, 4, 18, 15), fill=255)
        L, dl = layer()
        dl.line([(1, 4), (9, 11), (10, 11), (18, 4)], fill=255)
        det.append((L, OUT))
    elif name == "play":
        d.rounded_rectangle((1, 4, 18, 15), radius=4, fill=255)
        L, dl = layer()
        dl.polygon([(8, 7), (8, 12), (12, 9)], fill=255)
        det.append((L, W_))
    elif name == "megaphone":
        d.polygon([(2, 8), (8, 7), (15, 2), (15, 17), (8, 12), (2, 11)], fill=255)
        d.rectangle((5, 12, 7, 16), fill=255)
        L, dl = layer()
        dl.line([(17, 7), (17, 12)], fill=255)
        det.append((L, YELLOW))
    elif name == "trophy":
        d.polygon([(5, 2), (14, 2), (13, 9), (10, 11), (9, 11), (6, 9)], fill=255)
        d.rectangle((9, 11, 10, 14), fill=255)
        d.rectangle((6, 15, 13, 17), fill=255)
        d.rectangle((2, 3, 4, 7), fill=255)
        d.rectangle((15, 3, 17, 7), fill=255)
    elif name == "cursor":
        d.polygon([(5, 1), (5, 16), (8, 13), (11, 18), (13, 17), (10, 12), (15, 12)], fill=255)
    elif name == "arrow":
        d.line([(3, 16), (14, 5)], fill=255, width=4)
        d.polygon([(7, 2), (17, 2), (17, 12)], fill=255)
    elif name == "bag":
        d.rectangle((3, 7, 16, 18), fill=255)
        L, dl = layer()
        dl.ellipse((6, 2, 13, 10), outline=255)
        det.append((L, OUT))
    elif name == "bulb":
        d.ellipse((4, 1, 15, 12), fill=255)
        d.rectangle((7, 12, 12, 17), fill=255)
        L, dl = layer()
        dl.rectangle((7, 13, 12, 13), fill=255)
        dl.rectangle((7, 15, 12, 15), fill=255)
        det.append((L, (120, 120, 140)))
        L2, dl2 = layer()
        dl2.point([(7, 4), (6, 5), (6, 6)], fill=255)
        det.append((L2, W_))
    else:
        raise Fail(f"Нет иконки «{name}»")
    return _compose(np.array(m), color, det, n)


def put_icon(c, name, x, y, p, color=V2, glow_c=None):
    im = icon(name, color)
    if glow_c:
        glow(c, x + im.width * p / 2, y + im.height * p / 2, im.width * p * 0.9, glow_c, 0.45)
    c.paste(im.resize((im.width * p * S, im.height * p * S), Image.NEAREST), px(x), px(y))
    return im.width * p, im.height * p



# ---------------------------------------------------------------- site art
ART = ["cow", "bucket", "plane", "team", "ill_handshake", "ill_layers", "ill_calendar", "ill_brain", "ill_flow",
       "ill_sliders", "ill_people", "ill_battery"]


def art_img(name):
    if name not in ART:
        raise Fail(f"Нет иллюстрации «{name}». Доступны: {', '.join(ART)}")
    return Image.open(os.path.join(ROOT, "assets", "img", name + ".png")).convert("RGBA")


def put_art(c, name, x, y, w=None, h=None, anchor="lt", shade=True):
    im = art_img(name)
    if w and not h:
        h = im.height * w / im.width
    elif h and not w:
        w = im.width * h / im.height
    im = im.resize((px(w), px(h)), Image.LANCZOS)
    if anchor[0] == "r":
        x -= w
    elif anchor[0] == "m":
        x -= w / 2
    if anchor[1] == "b":
        y -= h
    elif anchor[1] == "m":
        y -= h / 2
    if shade:
        sh = Image.new("RGBA", (px(w * 0.8), px(h * 0.08)), (0, 0, 0, 0))
        ImageDraw.Draw(sh).ellipse([0, 0, sh.width - 1, sh.height - 1], fill=(40, 20, 90, 50))
        sh = sh.filter(ImageFilter.GaussianBlur(px(12)))
        c.paste(sh, px(x + w * 0.1), px(y + h * 0.94))
    c.paste(im, px(x), px(y))
    return w, h

# ---------------------------------------------------------------- helpers
def acc(cfg, default="violet"):
    return ACCENTS.get(cfg.get("accent", default), ACCENTS[default])


def rnd(cfg):
    return random.Random(int(hashlib.md5(json.dumps(cfg, ensure_ascii=False).encode()).hexdigest()[:8], 16))


def header(c, cfg, dark=False, label_style=None):
    logo(c, dark=dark)
    lab = cfg.get("label")
    if lab:
        st = label_style or {}
        pill(c, W - M, 66, lab, st.get("fg", LILAC if dark else V1), bg=st.get("bg"),
             outline=st.get("outline", None if st.get("bg") else (LILAC if dark else V1)), right=True,
             dot=st.get("dot"))


def ribbon(cfg, default):
    return cfg.get("ribbon") or default


# ================================================================ layouts
def L_stat(c, cfg):
    a = acc(cfg)
    c.im = Image.new("RGBA", c.im.size, BG + (255,))
    c.refresh()
    r = rnd(cfg)
    glow(c, r.choice([900, 1000]), r.choice([100, 200]), 640, LILAC, 0.55)
    glow(c, 60, 1250, 560, (168, 230, 248), 0.45)
    dots(c, (208, 216, 230))
    header(c, cfg)
    y = 150
    big = cfg.get("big", "")
    size = 330
    while c.tw(big, font("serif", size, 900)) > W - 2 * M and size > 120:
        size -= 10
    _, bh = grad_text(c, M - 8, y, big, font("serif", size, 900), V1, a)
    y += bh + 36
    s, f, lines = fit(c, cfg["title"], "serif", 700, W - 2 * M, 250, 62, lh=1.18)
    y = draw_rich(c, lines, f, s, M, y, INK, V1, "underline", lh=1.18, deco=a)
    if cfg.get("chip"):
        y += 22
        cf = font("sans", 24, 700)
        cw = c.tw(cfg["chip"], cf)
        c.d.rounded_rectangle([px(M), px(y), px(M + cw + 48), px(y + 52)], radius=px(26), fill=INK)
        c.d.ellipse([px(M + 18), px(y + 20), px(M + 30), px(y + 32)], fill=(255, 92, 92))
        c.text(M + 42, y + 26, cfg["chip"], cf, WHITE, anchor="lm")
        y += 52
    y += 40
    if cfg.get("stats"):
        st = cfg["stats"][:4]
        cols = 2 if len(st) == 4 else len(st)
        rows_n = math.ceil(len(st) / cols)
        ch = 180
        top = 1196 - rows_n * ch - (rows_n - 1) * 20
        if top < y:
            raise Fail("Не влезают карточки цифр: сократи заголовок")
        cw = (W - 2 * M - (cols - 1) * 20) / cols
        for i, (val, lab) in enumerate(st):
            cx = M + (i % cols) * (cw + 20)
            cy = top + (i // cols) * (ch + 20)
            card(c, [cx, cy, cx + cw, cy + ch], r=28)
            vf = font("sans", 64 if cols <= 2 else 52, 800)
            c.text(cx + 32, cy + 34, val, vf, V1)
            para(c, lab, font("sans", 21, 600), 21, cx + 32, cy + 118, MUTED, cw - 64, lh=1.3, max_lines=2)
    elif cfg.get("rows"):
        rows = cfg["rows"][:5]
        unit = cfg.get("unit", "%")
        ch = 34 + 40 + (44 if cfg.get("subtitle") else 10) + 52 * len(rows) + 28
        cy0 = 1196 - ch
        if cy0 < y - 10:
            raise Fail("Не влезает график: сократи заголовок или строки")
        card(c, [M, cy0, W - M, 1196], r=34)
        ix, iy = M + 40, cy0 + 34
        c.text(ix, iy, cfg.get("card_title", ""), font("sans", 28, 800), INK)
        iy += 40
        if cfg.get("subtitle"):
            c.text(ix, iy, cfg["subtitle"], font("sans", 19, 500), MUTED)
            iy += 44
        else:
            iy += 10
        mx = max(r_[1] for r_ in rows)
        bw = W - 2 * M - 160
        for name, v, hot in rows:
            c.text(ix, iy, name, font("sans", 21, 600), INK if hot else MUTED)
            ty = iy + 32
            c.d.rounded_rectangle([px(ix), px(ty), px(ix + bw), px(ty + 12)], radius=px(6), fill=(236, 240, 247))
            c.d.rounded_rectangle([px(ix), px(ty), px(ix + max(14, bw * v / mx)), px(ty + 12)], radius=px(6),
                                  fill=V2 if hot else (176, 186, 204))
            c.text(W - M - 40, ty + 6, f"{v:g}{unit}", font("sans", 22, 800), V1 if hot else MUTED, anchor="rm")
            iy += 52
    source(c, cfg.get("source"))
    band(c, 1262, 1350, (V1, V2), WHITE, ribbon(cfg, ["ЦИФРЫ", "ИССЛЕДОВАНИЕ", "МАРКЕТИНГ"]))


def L_dark(c, cfg):
    a = acc(cfg, "violet")
    c.im = Image.new("RGBA", c.im.size, NAVY + (255,))
    c.refresh()
    r = rnd(cfg)
    glow(c, r.choice([880, 960]), 260, 700, V2, 0.55)
    glow(c, 120, 1200, 600, a, 0.30)
    dots(c, (40, 52, 84))
    wm = cfg.get("watermark")
    if wm:
        f = font("serif", 400, 900)
        while c.tw(wm, f) > 1500 and f.size > 160 * S:
            f = font("serif", f.size / S - 20, 900)
        outline_text(c, W + 60, 1150, wm, f, LILAC, 42, sw=2.5, anchor="rs")
    header(c, cfg, dark=True)
    ic = cfg.get("icon", "bolt")
    p = 13
    put_icon(c, ic, W - M - 20 * p, 150, p, color=a if a != ACCENTS["violet"] else LILAC, glow_c=V2)
    s, f, lines = fit(c, cfg["title"], "serif", 800, W - 2 * M, 460, 96, lh=1.1)
    ty = 1180 - (len(lines) * s * 1.1) - (150 if cfg.get("subtitle") else 40)
    ty = max(ty, 430)
    y = draw_rich(c, lines, f, s, M, ty, WHITE, WHITE, "marker", lh=1.1, deco=V2)
    if cfg.get("subtitle"):
        para(c, cfg["subtitle"], font("sans", 28, 500), 28, M, y + 24, (172, 180, 208), W - 2 * M - 80, max_lines=3)
    # CTA
    cta = cfg.get("cta", "Подробнее - в описании")
    cf = font("jost", 24, 700)
    cw = c.tw(cta, cf) + 92
    g = lin_grad(px(cw), px(64), V1, V2, 0)
    mk = Image.new("L", g.size, 0)
    ImageDraw.Draw(mk).rounded_rectangle([0, 0, g.width - 1, g.height - 1], radius=px(18), fill=255)
    g.putalpha(mk)
    c.paste(g, px(M), px(1230))
    c.text(M + 28, 1262, cta, cf, WHITE, anchor="lm")
    arrow_ne(c, M + cw - 34, 1262, 8, WHITE)
    c.text(W - M, 1262, "dobroe.agency", font("sans", 20, 700), (150, 160, 190), anchor="rm", sp=0.5)


def L_marquee(c, cfg):
    bg_grad(c, V1, V2, 40)
    words = ribbon(cfg, ["МАРКЕТИНГ", "SEO", "SMM", "РЕКЛАМА", "ТАРГЕТ", "КОНТЕНТ"])
    L = Image.new("RGBA", (px(W * 1.8), px(H * 1.6)), (0, 0, 0, 0))
    dl = ImageDraw.Draw(L)
    f = font("sans", 150, 800)
    for row in range(9):
        x = -row * 260 % 900 - 900
        y = row * 190
        i = row
        while x < W * 1.8:
            t = words[i % len(words)] + ". "
            dl.text((px(x), px(y)), t, font=f, fill=(255, 255, 255, 34 if row % 2 else 22))
            x += dl.textlength(t, font=f) / S
            i += 1
    L = L.rotate(9, resample=Image.BICUBIC)
    c.paste(L, (c.im.width - L.width) // 2, (c.im.height - L.height) // 2)
    header(c, cfg, dark=True, label_style={"bg": WHITE, "fg": V1})
    # card
    inner = W - 2 * M - 80
    s, f, lines = fit(c, cfg["title"], "serif", 800, inner, 420, 82, lh=1.12)
    sub = cfg.get("subtitle")
    sf = font("sans", 27, 500)
    sub_l = plain_wrap(c, sub, sf, inner) if sub else []
    if len(sub_l) > 4:
        raise Fail("Подзаголовок слишком длинный")
    hcard = 40 + 30 + 34 + len(lines) * s * 1.12 + (24 + len(sub_l) * 27 * 1.4 if sub_l else 0) + 48
    hcard = max(hcard, 480)
    top = 170 + (1220 - 170 - hcard) / 2
    card(c, [M, top, W - M, top + hcard], r=44)
    kicker(c, M + 40, top + 40, cfg.get("kicker", cfg.get("label", "")), V1)
    y = draw_rich(c, lines, f, s, M + 40, top + 40 + 30 + 34, INK, V1, "marker", lh=1.12, deco=LILAC)
    if sub_l:
        para(c, sub, sf, 27, M + 40, y + 24, MUTED, inner, lh=1.4)
    if cfg.get("art"):
        put_art(c, cfg["art"], W - M - 20, top + 30, h=200, anchor="rb", shade=False)
    else:
        put_icon(c, cfg.get("icon", "star"), W - M - 40 - 80, top - 50, 4, color=YELLOW)
    band(c, 1262, 1350, WHITE, V1, words, star=V2)


def L_checklist(c, cfg):
    a = acc(cfg, "mint")
    c.im = Image.new("RGBA", c.im.size, (246, 242, 254, 255))
    c.refresh()
    glow(c, 980, 180, 600, LILAC, 0.5)
    glow(c, 80, 1300, 520, (190, 236, 250), 0.45)
    header(c, cfg)
    y = 158
    kicker(c, M, y, cfg.get("kicker", "ЧЕК-ЛИСТ"), V1)
    y += 46
    s, f, lines = fit(c, cfg["title"], "serif", 800, W - 2 * M, 250, 76, lh=1.1)
    y = draw_rich(c, lines, f, s, M, y, INK, V1, "underline", lh=1.1, deco=a)
    items = cfg["items"][:6]
    top, bot = y + 40, 1190
    n = len(items)
    gap = 16
    chh = min(132, (bot - top - gap * (n - 1)) / n)
    if chh < 84:
        raise Fail("Пункты не влезают: сократи заголовок или число пунктов")
    tf = font("sans", 27, 700)
    for i, it in enumerate(items):
        cy = top + i * (chh + gap)
        card(c, [M, cy, W - M, cy + chh], r=26)
        sq = 64
        sx, sy = M + 28, cy + (chh - sq) / 2
        g = lin_grad(px(sq), px(sq), V1, V2, 45)
        mk = Image.new("L", g.size, 0)
        ImageDraw.Draw(mk).rounded_rectangle([0, 0, g.width - 1, g.height - 1], radius=px(18), fill=255)
        g.putalpha(mk)
        c.paste(g, px(sx), px(sy))
        c.text(sx + sq / 2, sy + sq / 2 + 1, f"{i + 1:02d}", font("jost", 26, 800), WHITE, anchor="mm")
        ls = plain_wrap(c, it, tf, W - 2 * M - 140 - 70)
        if len(ls) > 2:
            raise Fail(f"Пункт длинный: «{it}»")
        ty = cy + chh / 2 - (len(ls) * 27 * 1.3) / 2
        for k, l in enumerate(ls):
            c.text(M + 120, ty + k * 27 * 1.3, l, tf, INK)
        put_icon(c, "check", W - M - 28 - 40, cy + chh / 2 - 20, 2, color=a)
    put_icon(c, "star", M, 1236, 2, color=YELLOW)
    c.text(M + 54, 1256, cfg.get("save", "Сохраните, чтобы не потерять"), font("sans", 22, 700), INK, anchor="lm")
    c.text(W - M, 1256, "dobroe.agency", font("sans", 20, 700), MUTED, anchor="rm", sp=0.5)


def L_myth(c, cfg):
    c.im = Image.new("RGBA", c.im.size, BG + (255,))
    c.refresh()
    split = 700
    top = Image.new("RGBA", (px(W), px(split + 30)), NAVY + (255,))
    c.paste(top, 0, 0)
    glow(c, 900, 200, 520, (180, 40, 70), 0.35)
    glow(c, 120, 520, 500, V2, 0.35)
    # torn edge
    pts = [(0, px(split))]
    for i in range(0, 37):
        x = W * i / 36
        pts.append((px(x), px(split + (14 if i % 2 else -14))))
    pts += [(px(W), px(H)), (0, px(H))]
    c.d.polygon(pts, fill=BG)
    glow(c, 980, 1250, 520, LILAC, 0.5)
    logo(c, dark=True)
    pill(c, M, 172, "МИФ", WHITE, bg=RED, size=18)
    put_icon(c, "cross", W - M - 160, 150, 8, color=RED)
    s, f, lines = fit(c, cfg["myth"], "serif_i", 700, W - 2 * M - 120, 360, 76, lh=1.15)
    y0 = 250 + (650 - 250 - len(lines) * s * 1.15) / 2
    draw_rich(c, lines, f, s, M, y0, WHITE, WHITE, "color", lh=1.15)
    for i, line in enumerate(lines):
        b = y0 + i * s * 1.15 + s * 0.92
        lw = line_w(c, line, f)
        mid = b - s * 0.3
        pts = [(px(M - 6 + (lw + 12) * k / 30), px(mid + 2.5 * math.sin(k / 30 * 9))) for k in range(31)]
        c.d.line(pts, fill=RED, width=px(max(5, s * 0.08)), joint="curve")
    # truth
    g = lin_grad(px(260), px(44), V1, V2, 0)
    mk = Image.new("L", g.size, 0)
    ImageDraw.Draw(mk).rounded_rectangle([0, 0, g.width - 1, g.height - 1], radius=px(22), fill=255)
    tw_ = pill(c, -999, 0, "НА САМОМ ДЕЛЕ", WHITE, size=18)  # measure
    c.im = c.im  # noop
    g = lin_grad(px(tw_), px(44), V1, V2, 0)
    mk = Image.new("L", g.size, 0)
    ImageDraw.Draw(mk).rounded_rectangle([0, 0, g.width - 1, g.height - 1], radius=px(22), fill=255)
    g.putalpha(mk)
    c.paste(g, px(M), px(772))
    pill(c, M, 772, "НА САМОМ ДЕЛЕ", WHITE, size=18)
    put_icon(c, "check", W - M - 120, 750, 6, color=GREEN)
    s2, f2, l2 = fit(c, cfg["truth"], "serif", 800, W - 2 * M, 250, 62, lh=1.14)
    y = draw_rich(c, l2, f2, s2, M, 850, INK, V1, "underline", lh=1.14, deco=acc(cfg))
    for it in cfg.get("items", [])[:3]:
        y += 18
        c.d.ellipse([px(M), px(y + 9), px(M + 14), px(y + 23)], fill=GREEN)
        y = para(c, it, font("sans", 25, 600), 25, M + 30, y, (40, 46, 64), W - 2 * M - 30, lh=1.3, max_lines=2)
    if y > 1230:
        raise Fail("Правда не влезает: сократи текст или пункты")
    source(c, cfg.get("source"), y=1290)
    c.text(W - M, 1300, "dobroe.agency", font("sans", 20, 700), MUTED, anchor="rm", sp=0.5)


def L_compare(c, cfg):
    c.im = Image.new("RGBA", c.im.size, BG + (255,))
    c.refresh()
    glow(c, 960, 160, 600, LILAC, 0.55)
    glow(c, 80, 1100, 520, (190, 236, 250), 0.45)
    dots(c, (210, 218, 232))
    header(c, cfg)
    s, f, lines = fit(c, cfg["title"], "serif", 800, W - 2 * M, 250, 76, lh=1.1)
    y = draw_rich(c, lines, f, s, M, 160, INK, V1, "underline", lh=1.1, deco=acc(cfg))
    gw = 28
    cw = (W - 2 * M - gw) / 2
    cols = [cfg["left"], cfg["right"]]
    tf, itf, isz = font("sans", 34, 800), font("sans", 28, 600), 28
    lay = []
    for col in cols:
        tl = plain_wrap(c, col["title"], tf, cw - 72)
        its = [plain_wrap(c, it, itf, cw - 72 - 40) for it in col["items"][:5]]
        hgt = 40 + 72 + 26 + len(tl) * 34 * 1.2 + 22 + sum(len(l) * isz * 1.3 + 22 for l in its) + 30
        lay.append((tl, its, hgt))
    ch = max(h for _, _, h in lay)
    verdict = cfg.get("verdict")
    vh = 96 if verdict else 0
    region_top, region_bot = y + 44, 1196
    if ch + vh > region_bot - region_top:
        raise Fail("Колонки не влезают: сократи пункты или заголовок")
    top = region_top + (region_bot - region_top - ch - vh) * 0.35
    card(c, [M, top, M + cw, top + ch], r=32)
    card(c, [M + cw + gw, top, W - M, top + ch], r=32, grad=(V1, V2, 60))
    for k, (tl, its, _) in enumerate(lay):
        x0 = M + k * (cw + gw) + 36
        put_icon(c, "cross" if k == 0 else "check", x0, top + 40, 3.6 if False else 3, color=RED if k == 0 else GREEN)
        ty = top + 40 + 72 + 26
        for l in tl:
            c.text(x0, ty, l, tf, INK if k == 0 else WHITE)
            ty += 34 * 1.2
        ty += 22
        for ls in its:
            if k == 0:
                c.d.line([px(x0 + 2), px(ty + 9), px(x0 + 18), px(ty + 25)], fill=RED, width=px(4))
                c.d.line([px(x0 + 18), px(ty + 9), px(x0 + 2), px(ty + 25)], fill=RED, width=px(4))
            else:
                c.d.line([px(x0), px(ty + 17), px(x0 + 8), px(ty + 25), px(x0 + 22), px(ty + 8)], fill=(150, 255, 210),
                         width=px(4), joint="curve")
            for j, l in enumerate(ls):
                c.text(x0 + 40, ty + j * isz * 1.3, l, itf, (70, 78, 98) if k == 0 else (240, 236, 255))
            ty += len(ls) * isz * 1.3 + 22
    # VS badge
    vx, vy = M + cw + gw / 2, top + ch / 2
    c.d.ellipse([px(vx - 38), px(vy - 38), px(vx + 38), px(vy + 38)], fill=NAVY, outline=WHITE, width=px(5))
    c.text(vx, vy + 2, "VS", font("jost", 26, 800), WHITE, anchor="mm")
    if verdict:
        vy0 = top + ch + 28
        vf = font("sans", 26, 700)
        vl = plain_wrap(c, verdict, vf, W - 2 * M - 140)
        if len(vl) > 2:
            raise Fail("Вывод слишком длинный")
        c.d.rounded_rectangle([px(M), px(vy0), px(W - M), px(vy0 + 68 if len(vl) == 1 else vy0 + 96)],
                              radius=px(22), fill=NAVY)
        put_icon(c, "bulb", M + 24, vy0 + 14, 2, color=YELLOW)
        for j, l in enumerate(vl):
            c.text(M + 84, vy0 + 34 + j * 32 - (14 if len(vl) == 2 else 0), l, vf, WHITE, anchor="lm")
    source(c, cfg.get("source"))
    band(c, 1262, 1350, NAVY, WHITE, ribbon(cfg, ["БЫЛО", "СТАЛО", "РЕЗУЛЬТАТ"]), star=V2)


def L_quote(c, cfg):
    c.im = Image.new("RGBA", c.im.size, (251, 250, 255, 255))
    c.refresh()
    glow(c, 1000, 1150, 640, LILAC, 0.5)
    glow(c, 60, 200, 500, (200, 236, 250), 0.4)
    c.text(W + 30, 1560, "”", font("serif", 1000, 900), (236, 230, 252), anchor="rs")
    header(c, cfg)
    s, f, lines = fit(c, cfg["quote"], "serif_i", 600, W - 2 * M, 560, 66, lh=1.22)
    block = len(lines) * s * 1.22 + 40 + 30 + 44 + (60 if cfg.get("role") else 0)
    qy = 420 + max(0, (1150 - 420 - block) / 2)
    grad_text(c, M - 6, qy - 250, "“", font("serif", 280, 900), V1, acc(cfg))
    y = draw_rich(c, lines, f, s, M, qy, INK, INK, "marker", lh=1.22, deco=LILAC)
    y += 40
    c.d.rounded_rectangle([px(M), px(y), px(M + 64), px(y + 6)], radius=px(3), fill=V2)
    y += 30
    c.text(M, y, cfg.get("author", ""), font("sans", 30, 800), INK)
    if cfg.get("role"):
        para(c, cfg["role"], font("sans", 22, 500), 22, M, y + 44, MUTED, W - 2 * M - 220, max_lines=2)
    if y > 1100:
        raise Fail("Цитата слишком длинная")
    if cfg.get("art"):
        put_art(c, cfg["art"], W - M, 1190, h=230, anchor="rb")
    else:
        put_icon(c, cfg.get("icon", "chat"), W - M - 160, 1010, 8, color=acc(cfg))
    source(c, cfg.get("source"))
    band(c, 1262, 1350, (V1, V2), WHITE, ribbon(cfg, ["МНЕНИЕ", "ЭКСПЕРТ", "ЦИТАТА"]))


def L_chat(c, cfg):
    bg_grad(c, (236, 242, 255), (245, 238, 254), 90)
    glow(c, 980, 300, 520, (180, 228, 250), 0.5)
    glow(c, 80, 900, 520, LILAC, 0.45)
    header(c, cfg)
    s, f, lines = fit(c, cfg["title"], "serif", 800, W - 2 * M, 230, 70, lh=1.1)
    y = draw_rich(c, lines, f, s, M, 160, INK, V1, "color", lh=1.1)
    if cfg.get("source"):
        c.text(M, y + 12, cfg["source"], font("sans", 19, 500), MUTED)
        y += 30
    fx0, fx1, fy0 = 140, W - 140, y + 46
    shadow(c, [fx0, fy0, fx1, H + 80], r=64, alpha=60, blur=30)
    c.d.rounded_rectangle([px(fx0), px(fy0), px(fx1), px(H + 80)], radius=px(64), fill=NAVY)
    sx0, sx1, sy0 = fx0 + 16, fx1 - 16, fy0 + 16
    c.d.rounded_rectangle([px(sx0), px(sy0), px(sx1), px(H + 80)], radius=px(50), fill=(244, 246, 251))
    # top bar
    c.d.rounded_rectangle([px(sx0), px(sy0), px(sx1), px(sy0 + 100)], radius=px(50), fill=WHITE)
    c.d.rectangle([px(sx0), px(sy0 + 60), px(sx1), px(sy0 + 100)], fill=WHITE)
    c.d.line([px(sx0), px(sy0 + 100), px(sx1), px(sy0 + 100)], fill=(228, 232, 242), width=px(2))
    ax, ay = sx0 + 40, sy0 + 50
    g = lin_grad(px(56), px(56), V1, V2, 45)
    mk = Image.new("L", g.size, 0)
    ImageDraw.Draw(mk).ellipse([0, 0, g.width - 1, g.height - 1], fill=255)
    g.putalpha(mk)
    c.paste(g, px(ax), px(ay - 28))
    put_icon(c, "heart", ax + 13, ay - 13, 2)
    c.text(ax + 74, ay - 4, cfg.get("chat_title", "Клиент"), font("sans", 24, 800), INK, anchor="ls")
    c.text(ax + 74, ay + 22, cfg.get("chat_status", "в сети"), font("sans", 18, 600), GREEN, anchor="ls")
    by = sy0 + 130
    mf = font("sans", 25, 600)
    maxbw = (sx1 - sx0) * 0.68
    for side, txt, *rest in cfg["messages"][:6]:
        ls = plain_wrap(c, txt, mf, maxbw - 48)
        bw = max(c.tw(l, mf) for l in ls) + 48
        bh = len(ls) * 25 * 1.32 + 52
        if by + bh > H - 30:
            raise Fail("Сообщения не влезают: сократи диалог")
        tm = rest[0] if rest else ""
        if side == "in":
            bx = sx0 + 28
            shadow(c, [bx, by, bx + bw, by + bh], r=24, alpha=30, blur=10, dy=4)
            c.d.rounded_rectangle([px(bx), px(by), px(bx + bw), px(by + bh)], radius=px(24), fill=WHITE)
            col = INK
            tc = MUTED
        else:
            bx = sx1 - 28 - bw
            gg = lin_grad(px(bw), px(bh), V1, V2, 30)
            mk = Image.new("L", gg.size, 0)
            ImageDraw.Draw(mk).rounded_rectangle([0, 0, gg.width - 1, gg.height - 1], radius=px(24), fill=255)
            gg.putalpha(mk)
            c.paste(gg, px(bx), px(by))
            col = WHITE
            tc = (220, 210, 255)
        for j, l in enumerate(ls):
            c.text(bx + 24, by + 22 + j * 25 * 1.32, l, mf, col)
        if tm:
            c.text(bx + bw - 20, by + bh - 14, tm, font("sans", 15, 600), tc, anchor="rs")
        by += bh + 18


def L_pixel(c, cfg):
    base = (22, 10, 51)
    c.im = Image.new("RGBA", c.im.size, base + (255,))
    c.refresh()
    glow(c, 540, 380, 560, V2, 0.45)
    r = rnd(cfg)
    step = 30
    for gx in range(0, W, step):
        c.d.line([px(gx), 0, px(gx), px(H)], fill=(34, 20, 74), width=px(1))
    for gy in range(0, H, step):
        c.d.line([0, px(gy), px(W), px(gy)], fill=(34, 20, 74), width=px(1))
    for _ in range(40):
        gx, gy = r.randrange(0, W // step) * step, r.randrange(0, H // step) * step
        col = r.choice([WHITE, LILAC, YELLOW, (120, 220, 255)])
        sz = r.choice([6, 6, 12])
        c.d.rectangle([px(gx + 12), px(gy + 12), px(gx + 12 + sz), px(gy + 12 + sz)], fill=col)
    logo(c, dark=True)
    if cfg.get("label"):
        lf = font("pixel", 15)
        lw = c.tw(cfg["label"], lf) + 36
        x0 = W - M - lw
        c.d.rectangle([px(x0), px(66), px(W - M), px(110)], fill=YELLOW)
        c.d.rectangle([px(x0 + 4), px(110), px(W - M + 4), px(114)], fill=(140, 100, 10))
        c.text(x0 + 18, 89, cfg["label"], lf, base, anchor="lm")
    ic = cfg.get("icon", "trophy")
    p = 13
    iw = 20 * p
    s_, f_, lines_ = fit(c, cfg["title"], "pixel", None, W - 2 * M, 300, 44, smin=20, lh=1.55)
    items = cfg.get("items", [])[:4]
    itf = font("sans", 27, 700)
    lines_i = [plain_wrap(c, "> " + it, itf, W - 2 * M - 80) for it in items]
    hbox = (sum(len(l) for l in lines_i) * 27 * 1.4 + 20 * (len(items) - 1) + 68) if items else 0
    total = iw + 50 + len(lines_) * s_ * 1.55 + (36 + hbox if items else 0)
    if total > 1180 - 140:
        raise Fail("Пиксель-макет: слишком много текста")
    y0 = 140 + (1180 - 140 - total) / 2
    ix = (W - iw) / 2
    sh_ = icon(ic, acc(cfg, "orange")).resize((iw * S, iw * S), Image.NEAREST)
    a_ = np.array(sh_)
    a_[..., :3] = 10
    a_[..., 3] = (a_[..., 3] > 0) * 120
    c.paste(Image.fromarray(a_), px(ix + p), px(y0 + p))
    put_icon(c, ic, ix, y0, p, color=acc(cfg, "orange"))
    y = y0 + iw + 50
    y = draw_rich(c, lines_, f_, s_, M, y, WHITE, YELLOW, "color", lh=1.55, align="m", maxw=W - 2 * M)
    if items:
        bx0, by0 = M, y + 36
        c.d.rectangle([px(bx0), px(by0), px(W - M), px(by0 + hbox)], fill=WHITE)
        c.d.rectangle([px(bx0 + 6), px(by0 + 6), px(W - M - 6), px(by0 + hbox - 6)], fill=base)
        c.d.rectangle([px(bx0 + 12), px(by0 + 12), px(W - M - 12), px(by0 + hbox - 12)], outline=V2, width=px(3))
        ty = by0 + 34
        for ls in lines_i:
            for l in ls:
                c.text(bx0 + 40, ty, l, itf, (230, 226, 255))
                ty += 27 * 1.4
            ty += 20
    # progress bar
    by = 1258
    c.text(M, by - 40, cfg.get("bar_label", "ПРОКАЧКА МАРКЕТИНГА"), font("pixel", 13), LILAC)
    segs = 20
    filled = int(segs * cfg.get("progress", 0.75))
    sw_ = (W - 2 * M - 300) / segs
    for i in range(segs):
        x0 = M + i * sw_
        c.d.rectangle([px(x0), px(by - 8), px(x0 + sw_ - 6), px(by + 22)], fill=GREEN if i < filled else (52, 34, 96))
    c.text(W - M, by + 8, "dobroe.agency", font("pixel", 13), WHITE, anchor="rm")


def L_steps(c, cfg):
    c.im = Image.new("RGBA", c.im.size, BG + (255,))
    c.refresh()
    glow(c, 1000, 220, 620, LILAC, 0.55)
    glow(c, 60, 1250, 560, (190, 236, 250), 0.45)
    dots(c, (210, 218, 232))
    header(c, cfg)
    kicker(c, M, 158, cfg.get("kicker", "ПОШАГОВО"), V1)
    s, f, lines = fit(c, cfg["title"], "serif", 800, W - 2 * M, 230, 72, lh=1.1)
    y = draw_rich(c, lines, f, s, M, 204, INK, V1, "underline", lh=1.1, deco=acc(cfg))
    items = cfg["items"][:5]
    top, bot = y + 50, 1170
    n = len(items)
    step = (bot - top) / n
    if step < 150:
        raise Fail("Шаги не влезают")
    cxl = M + 44
    # path
    for i in range(n - 1):
        y0, y1 = top + i * step + 44, top + (i + 1) * step + 44
        k = 0
        yy = y0 + 54
        while yy < y1 - 54:
            c.d.rectangle([px(cxl - 2), px(yy), px(cxl + 2), px(yy + 12)], fill=LILAC)
            yy += 22
    for i, it in enumerate(items):
        ttl, desc = (it if isinstance(it, list) else [it, ""])[:2]
        cy = top + i * step
        g = lin_grad(px(88), px(88), V1, acc(cfg), 45)
        mk = Image.new("L", g.size, 0)
        ImageDraw.Draw(mk).ellipse([0, 0, g.width - 1, g.height - 1], fill=255)
        g.putalpha(mk)
        shadow(c, [cxl - 44, cy, cxl + 44, cy + 88], r=44, alpha=50, blur=12, dy=6)
        c.paste(g, px(cxl - 44), px(cy))
        c.text(cxl, cy + 45, str(i + 1), font("jost", 38, 800), WHITE, anchor="mm")
        tx = cxl + 80
        ty = para(c, ttl, font("sans", 30, 800), 30, tx, cy + 8, INK, W - M - tx, lh=1.2, max_lines=2)
        if desc:
            para(c, desc, font("sans", 23, 500), 23, tx, ty + 6, MUTED, W - M - tx, lh=1.35, max_lines=2)
    source(c, cfg.get("source"), y=1196)
    band(c, 1262, 1350, (V1, V2), WHITE, ribbon(cfg, ["ШАГ ЗА ШАГОМ", "ПРОЦЕСС", "СИСТЕМА"]))


def L_news(c, cfg):
    c.im = Image.new("RGBA", c.im.size, BG + (255,))
    c.refresh()
    a = acc(cfg, "cyan")
    glow(c, 980, 300, 640, LILAC, 0.6)
    glow(c, 100, 1200, 520, mix(a, WHITE, 0.6), 0.5)
    wm = cfg.get("watermark", "NEWS")
    f = font("serif", 330, 900)
    while c.tw(wm, f) > W - M - 20 and f.size > 90 * S:
        f = font("serif", f.size / S - 10, 900)
    c.text(M - 14, 470, wm, f, (232, 224, 252), anchor="ls")
    header(c, cfg, label_style={"bg": NAVY, "fg": WHITE, "dot": (255, 92, 92)})
    if cfg.get("art"):
        put_art(c, cfg["art"], W - M, 400, h=250, anchor="rb")
    else:
        put_icon(c, cfg.get("icon", "megaphone"), W - M - 176, 150, 9, color=a)
    s, f2, lines = fit(c, cfg["title"], "serif", 800, W - 2 * M, 330, 78, lh=1.1)
    y = draw_rich(c, lines, f2, s, M, 540, INK, V1, "marker", lh=1.1, deco=LILAC)
    if cfg.get("subtitle"):
        y = para(c, cfg["subtitle"], font("sans", 27, 500), 27, M, y + 22, MUTED, W - 2 * M - 40, lh=1.4, max_lines=3)
    facts = cfg.get("facts", [])[:3]
    if facts:
        fh = 170
        ft = 1196 - fh
        if ft < y + 30:
            raise Fail("Факты не влезают: сократи заголовок/подзаголовок")
        n = len(facts)
        fw = (W - 2 * M - 20 * (n - 1)) / n
        for i, (val, lab) in enumerate(facts):
            fx = M + i * (fw + 20)
            card(c, [fx, ft, fx + fw, ft + fh], r=28)
            vf = font("sans", 48 if n == 3 else 56, 800)
            while c.tw(val, vf) > fw - 48:
                vf = font("sans", vf.size / S - 4, 800)
            c.text(fx + 26, ft + 28, val, vf, V1)
            para(c, lab, font("sans", 20, 600), 20, fx + 26, ft + 100, MUTED, fw - 52, lh=1.3, max_lines=2)
    source(c, cfg.get("source"))
    footer_site(c, 1290, INK, line=(222, 226, 236), left=cfg.get("footer", "01 / НОВОСТЬ"))


def L_hero(c, cfg):
    """как первый экран сайта: заголовок + большая иллюстрация (cow / bucket / plane)"""
    c.im = Image.new("RGBA", c.im.size, (246, 249, 254, 255))
    c.refresh()
    glow(c, 860, 900, 640, LILAC, 0.55)
    glow(c, 120, 260, 520, (200, 236, 250), 0.45)
    header(c, cfg)
    art = cfg.get("art", "cow")
    s, f, lines = fit(c, cfg["title"], "serif", 800, W - 2 * M, 300, 82, lh=1.1)
    y = 170
    if cfg.get("kicker"):
        kicker(c, M, y, cfg["kicker"], V1)
        y += 46
    y = draw_rich(c, lines, f, s, M, y, INK, V1, "color", lh=1.1)
    c.d.rounded_rectangle([px(M), px(y + 14), px(M + 90), px(y + 18)], radius=px(2), fill=LILAC)
    if cfg.get("subtitle"):
        y = para(c, cfg["subtitle"], font("sans", 28, 500), 28, M, y + 40, MUTED, W - 2 * M - 40, lh=1.4, max_lines=3)
    top = y + 30
    area_h = 1180 - top
    if area_h < 360:
        raise Fail("Мало места для иллюстрации: сократи заголовок/подзаголовок")
    im = art_img(art)
    ratio = im.width / im.height
    aw = min(W - 2 * M + 80, area_h * ratio)
    ah = aw / ratio
    put_art(c, art, W / 2 + (60 if art == "cow" else 0), 1180, w=aw, anchor="mb")
    # CTA pill like site button
    cta = cfg.get("cta", "Подробнее - в описании")
    cf = font("jost", 24, 700)
    cw = c.tw(cta, cf) + 92
    g = lin_grad(px(cw), px(64), V1, V2, 0)
    mk = Image.new("L", g.size, 0)
    ImageDraw.Draw(mk).rounded_rectangle([0, 0, g.width - 1, g.height - 1], radius=px(18), fill=255)
    g.putalpha(mk)
    shadow(c, [M, 1230, M + cw, 1294], r=18, color=V1, alpha=70, blur=14, dy=8)
    c.paste(g, px(M), px(1230))
    c.text(M + 28, 1262, cta, cf, WHITE, anchor="lm")
    arrow_ne(c, M + cw - 34, 1262, 8, WHITE)
    c.text(W - M, 1262, "dobroe.agency", font("sans", 20, 700), MUTED, anchor="rm", sp=0.5)


def L_team(c, cfg):
    """как баннер сайта: команда со спины + огромные фиолетовые слова"""
    c.im = Image.new("RGBA", c.im.size, WHITE + (255,))
    c.refresh()
    glow(c, 980, 140, 520, LILAC, 0.45)
    header(c, cfg)
    y = 165
    if cfg.get("kicker"):
        kicker(c, M, y, cfg["kicker"], V1)
        y += 46
    s, f, lines = fit(c, cfg["title"], "serif", 800, W - 2 * M, 330, 80, lh=1.1)
    y = draw_rich(c, lines, f, s, M, y, INK, V1, "underline", lh=1.1, deco=acc(cfg))
    if cfg.get("subtitle"):
        y = para(c, cfg["subtitle"], font("sans", 27, 500), 27, M, y + 26, MUTED, W - 2 * M - 40, lh=1.4, max_lines=3)
    team = art_img("team")
    tw_ = W + 60
    th = team.height * tw_ / team.width
    ty = H - th + 10
    if ty < y + 150:
        raise Fail("Мало места для фото команды: сократи текст")
    put_art(c, "team", -30, ty, w=tw_, shade=False)
    # giant words in front of the team - like the site banner
    words = ribbon(cfg, ["Маркетинг.", "SEO.", "Реклама.", "Контент."])
    bf = font("sans", 150, 800)
    by = ty + th * 0.58
    x = -60
    i = 0
    while x < W:
        x += c.text(x, by, words[i % len(words)] + " ", bf, V2, anchor="lm")
        i += 1


def L_offer(c, cfg):
    """последний слайд карусели / продающий пост: услуга агентства по теме + контакты"""
    a = acc(cfg, "orange")
    bg_grad(c, V1, V2, 40)
    glow(c, 960, 220, 520, a, 0.35)
    dots(c, mix(V1, WHITE, 0.25))
    header(c, cfg, dark=True, label_style={"bg": WHITE, "fg": V1})
    y = 170
    kicker(c, M, y, cfg.get("kicker", "ЧЕМ ПОМОЖЕМ"), WHITE)
    y += 46
    s, f, lines = fit(c, cfg["title"], "serif", 800, W - 2 * M, 300, 78, lh=1.1)
    y = draw_rich(c, lines, f, s, M, y, WHITE, WHITE, "marker", lh=1.1, deco=a)
    items = cfg.get("items", [])[:4]
    top = y + 34
    contacts = [("phone", "+996 222 522 235"), ("chat", "t.me/Dobroe_agency"), ("cursor", "dobroe.agency")]
    ctop = 1300 - 70 - len(contacts) * 62
    tf = font("sans", 27, 700)
    hh = 0
    rows = []
    if items:
        rows = [plain_wrap(c, it, tf, W - 2 * M - 140) for it in items]
        if any(len(r) > 2 for r in rows):
            raise Fail("Пункт оффера длинный: максимум 2 строки")
        hh = sum(30 + len(r) * 27 * 1.3 for r in rows) + 40
        if top + hh > ctop - 40:
            raise Fail("Оффер не влезает: сократи заголовок или пункты")
    free = ctop - 40 - (top + hh)
    art = cfg.get("art")
    if art and free < 200:
        raise Fail("Мало места для иллюстрации в offer: сократи текст или убери art")
    if not art:
        top += free * 0.3
    if items:
        card(c, [M, top, W - M, top + hh], r=32)
        yy = top + 34
        for r in rows:
            put_icon(c, "check", M + 34, yy + 2, 2, color=a if a != ACCENTS["violet"] else GREEN)
            for k, l in enumerate(r):
                c.text(M + 96, yy + k * 27 * 1.3, l, tf, INK)
            yy += 30 + len(r) * 27 * 1.3
    if art:
        ah = min(free - 30, 420)
        y0 = top + hh + 20
        im = art_img(art)
        aw = min(W - 2 * M, (ah) * im.width / im.height)
        ah = aw * im.height / im.width
        put_art(c, art, W - M - aw / 2 + (0 if aw > 500 else -20), y0 + (free - 10 - ah) / 2, w=aw, anchor="mt")
    if cfg.get("cta"):
        cf = font("jost", 26, 700)
        c.text(M, ctop - 6, cfg["cta"], cf, WHITE, anchor="ls")
    cf = font("sans", 30, 800)
    for i, (ic, t) in enumerate(contacts):
        cy = ctop + 14 + i * 62
        put_icon(c, ic, M, cy, 2, color=WHITE)
        c.text(M + 60, cy + 20, t, cf, WHITE, anchor="lm")


LAYOUTS = {"stat": L_stat, "dark": L_dark, "marquee": L_marquee, "checklist": L_checklist, "myth": L_myth,
           "compare": L_compare, "quote": L_quote, "chat": L_chat, "pixel": L_pixel, "steps": L_steps,
           "news": L_news, "hero": L_hero, "team": L_team, "offer": L_offer}


def check_dashes(cfg):
    s = json.dumps(cfg, ensure_ascii=False)
    if "—" in s or "–" in s:
        raise Fail("В конфиге есть длинное тире «—»/«–» - замени на дефис «-»")


def render(cfg, out):
    check_dashes(cfg)
    lay = cfg.get("layout", "stat")
    if lay not in LAYOUTS:
        raise Fail(f"Неизвестный layout «{lay}». Доступны: {', '.join(LAYOUTS)}")
    c = C(BG)
    LAYOUTS[lay](c, cfg)
    c.save(out)
    print("saved", out, "layout", lay)


if __name__ == "__main__":
    render(json.load(open(sys.argv[1], encoding="utf-8")), sys.argv[2])
