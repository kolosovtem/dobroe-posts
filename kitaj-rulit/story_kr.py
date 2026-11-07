#!/usr/bin/env python3
"""Сторис «Китай RUлит» 1080×1920 в фирменном стиле (тёмно-бордовый фон, фото сверху,
плашка-тег, заголовок, текст, источник, красная плашка «Привезём любой автомобиль из Китая»).

Запуск:  python3 -I story_kr.py plan.json out_dir/
plan.json — массив записей: {date:"2026-11-19", time:"10:00", tag, title, body, source,
           photo (путь к jpg или ""), photo_credit, kind: "news"|"poll"|"company"}
Файлы сохраняются как out_dir/YYYY-MM-DD/HH-00.jpg
"""
import json
import os
import sys
from PIL import Image, ImageDraw, ImageFilter, ImageFont

W, H = 1080, 1920
HERE = os.path.dirname(os.path.abspath(__file__))
LOGO = os.path.join(HERE, "assets", "logo_color.png")
FONT = "/usr/share/fonts/opentype/inter/Inter-%s.otf"

RED = (146, 43, 44)
BURG = (44, 14, 18)
DARK = (14, 12, 13)
WHITE = (255, 255, 255)
BODY = (222, 214, 215)
MUTED = (150, 146, 148)
M = 80  # левое поле


def f(w, s):
    return ImageFont.truetype(FONT % w, s)


def wrap(d, text, font, maxw):
    # короткие слова (предлоги, союзы, числа до 2 знаков) не отрываем от следующего слова
    raw, words, i = text.split(), [], 0
    while i < len(raw):
        w = raw[i]
        while i + 1 < len(raw) and (len(w.split("\u00a0")[-1]) <= 2
                                    or (w[-1].isdigit() and (raw[i + 1][0].isdigit() or len(raw[i + 1]) <= 5))):
            i += 1
            w = w + "\u00a0" + raw[i]
        words.append(w)
        i += 1
    lines, cur = [], ""
    for w in words:
        t = (cur + " " + w).strip()
        if not cur or d.textlength(t.replace("\u00a0", " "), font=font) <= maxw:
            cur = t
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return [l.replace("\u00a0", " ") for l in lines]


def background(photo):
    """Фон: фото сверху (0..~780) с затемнением, переходящее в бордовый градиент."""
    bg = Image.new("RGB", (W, H), DARK)
    grad = Image.new("RGB", (1, H))
    for y in range(H):
        # бордовый в середине, к низу почти чёрный; без фото верх тоже тёмный
        if not photo and y < 700:
            t = max(0.0, 1 - y / 700)
        else:
            t = 0 if y < 700 else min(1, (y - 700) / 1100)
        c = tuple(round(BURG[i] * (1 - t) + DARK[i] * t) for i in range(3))
        grad.putpixel((0, y), c)
    bg.paste(grad.resize((W, H)))
    if photo:
        ph = Image.open(photo).convert("RGB")
        ph_h = 900
        sc = max(W / ph.width, ph_h / ph.height)
        ph = ph.resize((round(ph.width * sc), round(ph.height * sc)), Image.LANCZOS)
        x0 = (ph.width - W) // 2
        y0 = max(0, (ph.height - ph_h) // 2)
        ph = ph.crop((x0, y0, x0 + W, y0 + ph_h))
        # затемнение и плавный переход в фон
        mask = Image.new("L", (W, ph_h))
        md = ImageDraw.Draw(mask)
        for y in range(ph_h):
            a = 255 if y < 420 else max(0, round(255 * (1 - (y - 420) / (ph_h - 420)) ** 1.4))
            md.line([(0, y), (W, y)], fill=a)
        dark = Image.new("RGB", (W, ph_h), (20, 10, 12))
        ph = Image.blend(ph, dark, 0.18)
        bg.paste(ph, (0, 0), mask)
    else:
        # большой полупрозрачный значок-колесо справа сверху
        logo = Image.open(LOGO).convert("RGBA")
        wheel = logo.crop((0, 0, round(logo.height * 1.4), logo.height))
        wheel = wheel.resize((round(wheel.width * 4.6), round(wheel.height * 4.6)), Image.LANCZOS)
        r, g, b, a = wheel.split()
        a = a.point(lambda v: v * 0.20)
        wheel = Image.new("RGBA", wheel.size, (120, 30, 34, 255))
        wheel.putalpha(a)
        bg.paste(wheel, (W - wheel.width + 330, 40), wheel)
    return bg


def header(im, d, date):
    # плашка с логотипом
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    od = ImageDraw.Draw(ov)
    od.rounded_rectangle([52, 118, 509, 260], radius=26, fill=(28, 26, 28, 215))
    od.rounded_rectangle([808, 150, 1028, 222], radius=18, fill=(28, 26, 28, 215))
    im.paste(Image.alpha_composite(im.convert("RGBA"), ov).convert("RGB"))
    logo = Image.open(LOGO).convert("RGBA")
    lw = 400
    logo = logo.resize((lw, round(logo.height * lw / logo.width)), Image.LANCZOS)
    im.paste(logo, (80, 189 - logo.height // 2), logo)
    d = ImageDraw.Draw(im)
    dd = "%s.%s.%s" % (date[8:10], date[5:7], date[0:4])
    d.text((918, 187), dd, font=f("Regular", 32), fill=(235, 233, 234), anchor="mm")
    return d


def pill(d, x, y, text):
    ft = f("Bold", 29)
    tw = d.textlength(text, font=ft)
    d.rounded_rectangle([x, y, x + tw + 52, y + 62], radius=31, fill=RED)
    d.text((x + 26, y + 31), text, font=ft, fill=WHITE, anchor="lm")


def cta(d):
    d.rounded_rectangle([60, 1555, 1020, 1690], radius=30, fill=RED)
    d.text((W / 2, 1597), "Привезём любой автомобиль из Китая", font=f("Bold", 33), fill=WHITE, anchor="mm")
    d.text((W / 2, 1650), "kitaj-rulit.ru", font=f("Bold", 48), fill=WHITE, anchor="mm")


def render(e, out):
    kind = e.get("kind", "news")
    photo = e.get("photo") or ""
    if photo and not os.path.exists(photo):
        photo = ""
    im = background(photo)
    d = ImageDraw.Draw(im)
    d = header(im, d, e["date"])

    y = 760 if photo else 560
    pill(d, M, y, e["tag"].upper())
    y += 62 + 50

    # заголовок: подбираем кегль, чтобы влез в 3 строки
    for size in (66, 62, 58, 54, 50):
        tf = f("Bold", size)
        tl = wrap(d, e["title"], tf, (760 if kind == "company" and len(e["title"]) < 30 else W - 2 * M))
        if len(tl) <= 3:
            break
    lh = round(size * 1.22)
    for ln in tl:
        d.text((M, y), ln, font=tf, fill=WHITE)
        y += lh
    y += 30

    body = e.get("body", "")
    if body:
        for size in (38, 36, 34, 32):
            bf = f("Regular", size)
            bl = wrap(d, body, bf, W - 2 * M - 20)
            if y + len(bl) * round(size * 1.47) < 1420:
                break
        blh = round(size * 1.47)
        for ln in bl:
            d.text((M, y), ln, font=bf, fill=BODY)
            y += blh

    if kind == "company":
        # кнопки «Сайт» и «Instagram», как в сторис 16:00
        by = max(y + 50, 1150)
        bh, gap = (146, 18) if by + 310 <= 1530 else (118, 12)
        by = min(by, 1530 - 2 * bh - gap)
        d.rounded_rectangle([60, by, 1020, by + bh], radius=24, outline=RED, width=3, fill=(18, 12, 14))
        d.text((W / 2, by + bh * 0.31), "Сайт", font=f("Regular", 27), fill=BODY, anchor="mm")
        d.text((W / 2, by + bh * 0.67), "kitaj-rulit.ru", font=f("Bold", 48 if bh > 130 else 42), fill=WHITE, anchor="mm")
        by += bh + gap
        d.rounded_rectangle([60, by, 1020, by + bh], radius=24, outline=(80, 72, 74), width=2, fill=(26, 24, 26))
        d.text((W / 2, by + bh * 0.31), "Instagram", font=f("Regular", 27), fill=BODY, anchor="mm")
        d.text((W / 2, by + bh * 0.67), "@kitaj_rulit", font=f("Bold", 48 if bh > 130 else 42), fill=WHITE, anchor="mm")
        e = dict(e, source="")

    # источник и фото — над красной плашкой
    notes = []
    if e.get("source"):
        notes.append("Источник: " + e["source"])
    if photo and e.get("photo_credit"):
        notes.append("Фото: " + e["photo_credit"])
    nf = f("Regular", 25)
    ny = 1528 - 35 * len(notes)
    for n in notes:
        while d.textlength(n, font=nf) > W - 2 * M and len(n) > 10:
            n = n[:-2].rstrip() + "…"
        d.text((M, ny), n, font=nf, fill=MUTED)
        ny += 35

    cta(d)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    im.save(out, "JPEG", quality=92, optimize=True)


if __name__ == "__main__":
    plan = json.load(open(sys.argv[1], encoding="utf-8"))
    outdir = sys.argv[2]
    only = sys.argv[3] if len(sys.argv) > 3 else None
    for e in plan:
        name = os.path.join(outdir, e["date"], e["time"].replace(":", "-") + ".jpg")
        if only and only not in name:
            continue
        render(e, name)
        print(name)
