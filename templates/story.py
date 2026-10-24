"""Истории Instagram 1080x1920 в стиле Агентства Добрых Дел.

Запуск:  python3 -I templates/story.py posts/stories/<папка>/story.json posts/stories/<папка>/story.jpg
Типы (поле "type"):
  promo    - анонс поста из ленты: post (путь к post.jpg/post-1.jpg), title, subtitle
  tip      - совет: kicker, title ([[акцент]]), subtitle, icon, accent
  fact     - цифра: big, title, source, accent
  question - вопрос аудитории: title, cta ("Ответьте в директ")
  offer    - услуга агентства: kicker, title, items (до 4), cta
Безопасные зоны: верхние ~250 px и нижние ~250 px перекрывает интерфейс Instagram - текста там нет.
Примеры - templates/examples/story_*.json.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from PIL import Image, ImageDraw  # noqa: E402

import render as R  # noqa: E402

R.H = 1920
W, H, M, S = R.W, R.H, R.M, R.S
TOP, BOT = 270, 1650  # безопасная зона для контента


def head(c, cfg, dark):
    R.logo(c, y=TOP - 70, dark=dark)
    lab = cfg.get("label")
    if lab:
        R.pill(c, W - M, TOP - 66, lab, R.LILAC if dark else R.V1,
               outline=R.LILAC if dark else R.V1, right=True)


def site(c, color):
    c.text(W / 2, BOT + 40, "dobroe.agency", R.font("sans", 24, 700), color, anchor="mm", sp=0.5)


def button(c, y, text):
    cf = R.font("jost", 30, 700)
    cw = c.tw(text, cf) + 110
    x = (W - cw) / 2
    g = R.lin_grad(R.px(cw), R.px(84), R.V1, R.V2, 0)
    mk = Image.new("L", g.size, 0)
    ImageDraw.Draw(mk).rounded_rectangle([0, 0, g.width - 1, g.height - 1], radius=R.px(24), fill=255)
    g.putalpha(mk)
    R.shadow(c, [x, y, x + cw, y + 84], r=24, color=R.V1, alpha=70, blur=14, dy=8)
    c.paste(g, R.px(x), R.px(y))
    c.text(x + 40, y + 42, text, cf, R.WHITE, anchor="lm")
    R.arrow_ne(c, x + cw - 40, y + 42, 10, R.WHITE)


def S_promo(c, cfg):
    c.im = Image.new("RGBA", c.im.size, (246, 242, 254, 255))
    c.refresh()
    R.glow(c, 980, 300, 700, R.LILAC, 0.55)
    R.glow(c, 80, 1700, 600, (190, 236, 250), 0.5)
    head(c, cfg, False)
    y = TOP + 40
    R.kicker(c, M, y, cfg.get("kicker", "НОВЫЙ ПОСТ"), R.V1)
    s, f, lines = R.fit(c, cfg["title"], "serif", 800, W - 2 * M, 230, 72, lh=1.1)
    y = R.draw_rich(c, lines, f, s, M, y + 46, R.INK, R.V1, "underline", lh=1.1, deco=R.acc(cfg, "orange"))
    post = Image.open(cfg["post"]).convert("RGBA")
    top = y + 50
    maxh = BOT - 150 - top
    pw = min(W - 2 * M - 40, maxh * post.width / post.height)
    ph = pw * post.height / post.width
    x = (W - pw) / 2
    im = post.resize((R.px(pw), R.px(ph)), Image.LANCZOS)
    mk = Image.new("L", im.size, 0)
    ImageDraw.Draw(mk).rounded_rectangle([0, 0, im.width - 1, im.height - 1], radius=R.px(28), fill=255)
    im.putalpha(mk)
    R.shadow(c, [x, top, x + pw, top + ph], r=28, color=R.V1, alpha=60, blur=26, dy=16)
    c.paste(im, R.px(x), R.px(top))
    button(c, BOT - 100, cfg.get("cta", "Смотрите в профиле"))
    site(c, R.MUTED)


def S_tip(c, cfg):
    a = R.acc(cfg, "cyan")
    c.im = Image.new("RGBA", c.im.size, R.NAVY + (255,))
    c.refresh()
    R.glow(c, 900, 420, 800, R.V2, 0.55)
    R.glow(c, 120, 1650, 700, a, 0.3)
    R.dots(c, (40, 52, 84))
    head(c, cfg, True)
    R.put_icon(c, cfg.get("icon", "bulb"), M, TOP + 60, 14, color=a, glow_c=R.V2)
    y = TOP + 420
    R.kicker(c, M, y, cfg.get("kicker", "СОВЕТ"), R.LILAC)
    s, f, lines = R.fit(c, cfg["title"], "serif", 800, W - 2 * M, 560, 96, lh=1.1)
    y = R.draw_rich(c, lines, f, s, M, y + 50, R.WHITE, R.WHITE, "marker", lh=1.1, deco=R.V2)
    if cfg.get("subtitle"):
        y = R.para(c, cfg["subtitle"], R.font("sans", 34, 500), 34, M, y + 40, (190, 198, 224), W - 2 * M, lh=1.4, max_lines=5)
    if y > BOT - 140:
        raise R.Fail("Совет не влезает в безопасную зону: сократи текст")
    button(c, BOT - 100, cfg.get("cta", "Ещё советы - в профиле"))
    site(c, (150, 160, 190))


def S_fact(c, cfg):
    a = R.acc(cfg, "mint")
    c.im = Image.new("RGBA", c.im.size, (246, 249, 254, 255))
    c.refresh()
    R.glow(c, 900, 500, 760, R.LILAC, 0.6)
    R.glow(c, 100, 1600, 600, (200, 236, 250), 0.5)
    head(c, cfg, False)
    y = TOP + 120
    R.kicker(c, M, y, cfg.get("kicker", "ЦИФРА ДНЯ"), R.V1)
    bf = R.font("serif", 300, 800)
    big = cfg["big"]
    while c.tw(big, bf) > W - 2 * M and bf.size > 120 * S:
        bf = R.font("serif", bf.size / S - 20, 800)
    c.text(M - 6, y + 60, big, bf, R.V1)
    y += 60 + bf.size / S * 1.15
    s, f, lines = R.fit(c, cfg["title"], "sans", 800, W - 2 * M, 420, 60, lh=1.2)
    y = R.draw_rich(c, lines, f, s, M, y + 20, R.INK, R.V1, "underline", lh=1.2, deco=a)
    if cfg.get("source"):
        R.para(c, "Источник: " + cfg["source"], R.font("sans", 26, 600), 26, M, y + 40, R.MUTED, W - 2 * M, max_lines=2)
    button(c, BOT - 100, cfg.get("cta", "Разбор - в профиле"))
    site(c, R.MUTED)


def S_question(c, cfg):
    R.bg_grad(c, R.V1, R.V2, 60)
    R.glow(c, 900, 1500, 700, R.acc(cfg, "pink"), 0.35)
    head(c, {**cfg, "label": None}, True)
    if cfg.get("label"):
        R.pill(c, W - M, TOP - 66, cfg["label"], R.V1, bg=R.WHITE, right=True)
    y = TOP + 160
    R.put_icon(c, cfg.get("icon", "chat"), W / 2 - 13 * 10, y, 13, color=R.WHITE)
    y += 330
    s, f, lines = R.fit(c, cfg["title"], "serif", 800, W - 2 * M, 640, 96, lh=1.12)
    y = R.draw_rich(c, lines, f, s, M, y, R.WHITE, R.WHITE, "marker", lh=1.12, align="m", maxw=W - 2 * M,
                    deco=R.mix(R.V1, R.WHITE, 0.25))
    R.card(c, [M, BOT - 230, W - M, BOT - 100], r=34)
    c.text(W / 2, BOT - 165, cfg.get("cta", "Ответьте в директ"), R.font("sans", 34, 800), R.V1, anchor="mm")
    site(c, (225, 215, 255))


def S_offer(c, cfg):
    a = R.acc(cfg, "orange")
    R.bg_grad(c, R.NAVY, R.V1, 70)
    R.glow(c, 950, 420, 700, a, 0.3)
    R.dots(c, (60, 50, 120))
    head(c, cfg, True)
    y = TOP + 40
    R.kicker(c, M, y, cfg.get("kicker", "ЧЕМ ПОМОЖЕМ"), R.LILAC)
    s, f, lines = R.fit(c, cfg["title"], "serif", 800, W - 2 * M, 420, 86, lh=1.1)
    y = R.draw_rich(c, lines, f, s, M, y + 50, R.WHITE, R.WHITE, "marker", lh=1.1, deco=a)
    tf = R.font("sans", 32, 700)
    rows = [R.plain_wrap(c, it, tf, W - 2 * M - 150) for it in cfg.get("items", [])[:4]]
    if rows:
        hh = sum(36 + len(r) * 32 * 1.3 for r in rows) + 50
        top = y + 50
        R.card(c, [M, top, W - M, top + hh], r=36)
        yy = top + 42
        for r in rows:
            R.put_icon(c, "check", M + 40, yy + 4, 2, color=a)
            for k, l in enumerate(r):
                c.text(M + 110, yy + k * 32 * 1.3, l, tf, R.INK)
            yy += 36 + len(r) * 32 * 1.3
        y = top + hh
    contacts = [("phone", "+996 222 522 235"), ("chat", "t.me/Dobroe_agency"), ("mail", "ceo@dobroe.agency")]
    cy0 = BOT - 60 - len(contacts) * 72
    if y > cy0 - 90:
        raise R.Fail("Оффер не влезает в безопасную зону: сократи текст")
    c.text(M, cy0 - 30, cfg.get("cta", "Напишите в директ или:"), R.font("jost", 32, 700), R.WHITE, anchor="ls")
    for i, (ic, t) in enumerate(contacts):
        cy = cy0 + i * 72
        R.put_icon(c, ic, M, cy, 2, color=R.WHITE)
        c.text(M + 64, cy + 20, t, R.font("sans", 36, 800), R.WHITE, anchor="lm")
    site(c, (190, 180, 230))


TYPES = {"promo": S_promo, "tip": S_tip, "fact": S_fact, "question": S_question, "offer": S_offer}


def main(cfg_path, out):
    cfg = json.load(open(cfg_path, encoding="utf-8"))
    R.check_dashes(cfg)
    t = cfg.get("type")
    if t not in TYPES:
        raise R.Fail(f"Неизвестный type «{t}». Доступны: {', '.join(TYPES)}")
    c = R.C(R.BG)
    TYPES[t](c, cfg)
    c.save(out)
    print("saved", out, "story", t)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
