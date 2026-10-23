"""Рендер поста 1080x1350 в стиле Агентства Добрых Дел.

Запуск:  python3 -I templates/post.py config.json out.jpg
Config (JSON):
{
  "pill": "ИССЛЕДОВАНИЕ · 10.2026",            # метка справа сверху
  "big": "46%",                                # крупная цифра/слово (необязательно)
  "headline": ["покупателей относятся",        # 2-4 строки, [[...]] = фиолетовый акцент с подчёркиванием
               "негативно к [[ИИ-карточкам]]",
               "и постам о товарах"],
  "chip": "а позитивно — всего 1%",           # тёмная плашка (необязательно)
  "card": {                                    # белая карточка
    "type": "bars",                            # "bars" или "points"
    "title": "Чему верят, когда выбирают товар",
    "subtitle": "доля ответов, %",
    "unit": "%",
    "rows": [["Отзывы в постах и комментариях", 33, true], ["Советы знакомых", 12, false]]
    # для "points": "items": ["первый пункт", "второй пункт", "третий пункт"]  (3-4 пункта, короткие)
  },
  "source": "Опрос ВКонтакте и Наука Mail, октябрь 2026",
  "ribbon": ["ЖИВОЙ КОНТЕНТ", "ОТЗЫВЫ", "РЕАЛЬНЫЕ ФОТО"]
}
"""
import json
import os
import re
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
S = 2
W, H = 1080 * S, 1350 * S
INTER = "/usr/share/fonts/opentype/inter/Inter-{}.otf"
LORA = "/usr/share/fonts/truetype/google-fonts/Lora-Variable.ttf"

INK = (11, 18, 32)
MUTED = (96, 108, 128)
VIOLET = (98, 38, 214)
VIOLET2 = (147, 51, 234)
BG = (243, 247, 252)
LEFT, RIGHT = 70, 1010
CARD_BOTTOM = 1196


def px(v):
    return int(round(v * S))


def inter(w, size):
    return ImageFont.truetype(INTER.format(w), int(size * S))


def lora(size, weight="Bold"):
    f = ImageFont.truetype(LORA, int(size * S))
    f.set_variation_by_name(weight)
    return f


def wrap(d, s, font, width):
    words, lines, cur = s.split(), [], ""
    for w in words:
        t = (cur + " " + w).strip()
        if d.textlength(t, font=font) / S <= width:
            cur = t
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def render(cfg, out_path):
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    img = np.zeros((H, W, 3), np.float32)
    img[:] = BG

    def glow(cx, cy, r, color, strength):
        dd = np.sqrt((xx - cx * S) ** 2 + (yy - cy * S) ** 2) / (r * S)
        a = np.clip(1 - dd, 0, 1) ** 2 * strength
        for i in range(3):
            img[..., i] = img[..., i] * (1 - a) + color[i] * a

    glow(1000, 120, 620, (196, 170, 255), 0.55)
    glow(40, 1250, 560, (168, 230, 248), 0.45)
    canvas = Image.fromarray(img.clip(0, 255).astype(np.uint8)).convert("RGBA")
    d = ImageDraw.Draw(canvas)

    for gx in range(40, 1080, 40):
        for gy in range(40, 1350, 40):
            d.ellipse([px(gx - 1.6), px(gy - 1.6), px(gx + 1.6), px(gy + 1.6)], fill=(208, 216, 230, 255))

    def text(xy, s, font, fill, spacing=0.0, anchor="la"):
        x, y = xy
        if not spacing:
            d.text((px(x), px(y)), s, font=font, fill=fill, anchor=anchor)
            return d.textlength(s, font=font) / S
        cx = px(x)
        for ch in s:
            d.text((cx, px(y)), ch, font=font, fill=fill, anchor=anchor)
            cx += d.textlength(ch, font=font) + px(spacing)
        return (cx - px(x)) / S

    # logo (real pixel logo of the agency)
    logo = Image.open(os.path.join(HERE, "..", "assets", "logo_grid.png"))
    canvas.alpha_composite(logo.resize((logo.width * 2 * S, logo.height * 2 * S), Image.NEAREST), (px(LEFT), px(61)))
    d = ImageDraw.Draw(canvas)

    # pill
    label = cfg.get("pill", "")
    if label:
        pf = inter("SemiBold", 17)
        tw = d.textlength(label, font=pf) / S + 17 * 0.08 * len(label)
        x0 = RIGHT - tw - 44
        d.rounded_rectangle([px(x0), px(66), px(RIGHT), px(108)], radius=px(21), outline=VIOLET, width=px(2))
        text((x0 + 22, 87), label, pf, VIOLET, spacing=17 * 0.08, anchor="lm")

    # ---------- measure card ----------
    card = cfg.get("card")
    big = cfg.get("big")
    pf_items = inter("Medium", 23 if big else 26)
    card_h = 0
    if card:
        head = 34 + 40 + (44 if card.get("subtitle") else 10)
        if card.get("type", "bars") == "bars":
            if len(card["rows"]) > 5:
                raise SystemExit("Слишком много строк в графике: максимум 5")
            body = 52 * len(card["rows"]) - 6
        else:
            body = 0
            for it in card["items"]:
                n = len(wrap(d, it, pf_items, RIGHT - LEFT - 80 - 64))
                body += max(40, 6 + n * (36 if not big else 32)) + 22
            body -= 22
        card_h = head + body + 34
    card_top = CARD_BOTTOM - card_h if card else CARD_BOTTOM

    # ---------- top block on its own layer ----------
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ld = ImageDraw.Draw(layer)
    y = 0
    if big:
        size = 300
        nf = lora(size)
        while ld.textlength(big, font=nf) / S > 940 and size > 120:
            size -= 10
            nf = lora(size)
        bb = ld.textbbox((0, 0), big, font=nf)
        mask = Image.new("L", (W, H), 0)
        ImageDraw.Draw(mask).text((px(LEFT - 12), -bb[1]), big, font=nf, fill=255)
        grad = np.zeros((H, W, 3), np.float32)
        t = np.clip((xx - px(LEFT)) / px(720), 0, 1)[..., None]
        grad[:] = np.array(VIOLET) * (1 - t) + np.array(VIOLET2) * t
        layer.paste(Image.fromarray(grad.astype(np.uint8)).convert("RGBA"), (0, 0), mask)
        ld = ImageDraw.Draw(layer)
        y = (bb[3] - bb[1]) / S + 40

    lines = cfg["headline"]
    hs = 62 if big else 84

    def plain(s):
        return s.replace("[[", "").replace("]]", "")

    hf = lora(hs)
    while max(ld.textlength(plain(l), font=hf) / S for l in lines) > RIGHT - LEFT and hs > 40:
        hs -= 2
        hf = lora(hs)
    lh = hs * 1.23
    for line in lines:
        x = LEFT
        for part in re.split(r"(\[\[.*?\]\])", line):
            if not part:
                continue
            hot = part.startswith("[[")
            seg = plain(part)
            ld.text((px(x), px(y)), seg, font=hf, fill=VIOLET if hot else INK)
            wseg = ld.textlength(seg, font=hf) / S
            if hot:
                uy = y + hs * 1.2
                pts = [(px(x + wseg * i / 40), px(uy + 3 * np.sin(i / 40 * 6.0))) for i in range(41)]
                ld.line(pts, fill=VIOLET2, width=px(5), joint="curve")
            x += wseg
        y += lh
    y += 14 - (hs * 0.23)

    chip = cfg.get("chip")
    if chip:
        y += 22
        cf = inter("SemiBold", 24)
        cw = ld.textlength(chip, font=cf) / S
        ld.rounded_rectangle([px(LEFT), px(y), px(LEFT + cw + 48), px(y + 52)], radius=px(26), fill=INK)
        ld.ellipse([px(LEFT + 18), px(y + 20), px(LEFT + 30), px(y + 32)], fill=(255, 92, 92))
        ld.text((px(LEFT + 42), px(y + 26)), chip, font=cf, fill=(255, 255, 255), anchor="lm")
        y += 52
    block_h = y

    region_top, region_bot = 150, card_top - 40
    if block_h > region_bot - region_top:
        raise SystemExit(f"Верхний блок не влезает ({block_h:.0f} > {region_bot - region_top:.0f}px): сократи заголовок/карточку")
    off = region_top + ((region_bot - region_top) - block_h) * (0.35 if big else 0.5)
    canvas.alpha_composite(layer, (0, px(off)))
    d = ImageDraw.Draw(canvas)

    # ---------- card ----------
    if card:
        cy0, cy1 = card_top, CARD_BOTTOM
        shadow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        ImageDraw.Draw(shadow).rounded_rectangle([px(LEFT), px(cy0 + 14), px(RIGHT), px(cy1 + 14)],
                                                 radius=px(34), fill=(70, 40, 160, 46))
        canvas = Image.alpha_composite(canvas, shadow.filter(ImageFilter.GaussianBlur(px(22))))
        d = ImageDraw.Draw(canvas)
        d.rounded_rectangle([px(LEFT), px(cy0), px(RIGHT), px(cy1)], radius=px(34), fill=(255, 255, 255))
        ix = LEFT + 40
        iy = cy0 + 34
        text((ix, iy), card.get("title", ""), inter("Bold", 28), INK)
        iy += 40
        if card.get("subtitle"):
            text((ix, iy), card["subtitle"], inter("Regular", 19), MUTED)
            iy += 44
        else:
            iy += 10
        if card.get("type", "bars") == "bars":
            rows = card["rows"]
            unit = card.get("unit", "%")
            maxv = max(r[1] for r in rows)
            bw = RIGHT - LEFT - 80 - 80
            for name, v, hot in rows:
                text((ix, iy), name, inter("Medium", 21), INK if hot else MUTED)
                ty = iy + 32
                d.rounded_rectangle([px(ix), px(ty), px(ix + bw), px(ty + 12)], radius=px(6), fill=(236, 240, 247))
                d.rounded_rectangle([px(ix), px(ty), px(ix + max(14, bw * v / maxv)), px(ty + 12)], radius=px(6),
                                    fill=VIOLET if hot else (176, 186, 204))
                vs = (f"{v:g}" if isinstance(v, (int, float)) else str(v)) + unit
                text((RIGHT - 40, ty + 6), vs, inter("Bold", 22), VIOLET if hot else MUTED, anchor="rm")
                iy += 52
        else:
            step_l = 32 if big else 36
            for n, it in enumerate(card["items"], 1):
                ls = wrap(d, it, pf_items, RIGHT - LEFT - 80 - 64)
                d.ellipse([px(ix), px(iy - 2), px(ix + 40), px(iy + 38)], fill=VIOLET)
                text((ix + 20, iy + 18), str(n), inter("Bold", 20), (255, 255, 255), anchor="mm")
                ty = iy + 6
                for l in ls:
                    text((ix + 64, ty), l, pf_items, INK)
                    ty += step_l
                iy = max(ty, iy + 40) + 22

    if cfg.get("source"):
        text((LEFT, 1218), cfg["source"], inter("Regular", 19), MUTED)

    # running line
    b0, b1 = 1262, 1350
    band = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(band).rectangle([0, px(b0), W, px(b1)], fill=VIOLET)
    canvas = Image.alpha_composite(canvas, band)
    d = ImageDraw.Draw(canvas)
    words = cfg.get("ribbon") or ["МАРКЕТИНГ", "SEO", "SMM", "РЕКЛАМА"]
    mid = (b0 + b1) / 2
    rf = inter("Bold", 26)

    def star(cx, cy, r):
        k = r * 0.28
        pts = [(cx, cy - r), (cx + k, cy - k), (cx + r, cy), (cx + k, cy + k),
               (cx, cy + r), (cx - k, cy + k), (cx - r, cy), (cx - k, cy - k)]
        d.polygon([(px(a), px(b)) for a, b in pts], fill=(255, 255, 255))

    x, i = -70, 0
    while x < 1100:
        x += text((x, mid), words[i % len(words)], rf, (255, 255, 255), spacing=1.5, anchor="lm") + 30
        star(x + 9, mid, 11)
        x += 48
        i += 1

    canvas.convert("RGB").resize((1080, 1350), Image.LANCZOS).save(out_path, quality=93)
    print("saved", out_path)


if __name__ == "__main__":
    render(json.load(open(sys.argv[1], encoding="utf-8")), sys.argv[2])
