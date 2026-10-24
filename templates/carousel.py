"""Карусель для Instagram + адаптированный альбом для Telegram из одного конфига.

Запуск:  python3 -I templates/carousel.py posts/<папка>/carousel.json posts/<папка>
Конфиг:  {"slides": [ {<конфиг слайда как для render.py>, "tg": {<правки для Telegram>}}, ... ],
          "tg_label": "UTM · 4 КАРТОЧКИ"}   - от 3 до 6 слайдов
  - слайд 1 - обложка (сильный заголовок, интрига, label вроде "ЛИСТАЙТЕ ->")
  - середина - польза (steps / checklist / compare / stat / myth / chat ...)
  - последний - "offer": услуга агентства по теме + контакты
Результат:
  Instagram: post-1.jpg ... post-N.jpg (+ post.jpg = обложка), сверху индикатор листания.
  Facebook:  fb.jpg - адаптированная обложка без номера (коннектор публикует одно фото), текст поста сам пересказывает пользу.
  Telegram:  tg-1.jpg ... tg-N.jpg - без индикатора листания и без призывов «листайте»,
             «на следующих слайдах», «сохраните»; вместо них номер карточки «1 / N».
             Правки на слайд: поле "tg" в слайде (перекрывает любые поля только для Telegram).
"""
import copy
import json
import os
import re
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from PIL import Image, ImageDraw  # noqa: E402

import render as R  # noqa: E402

IG_ONLY = re.compile(r"листа|слайд|свайп|сохрани|в профил|в директ|ссылк[аеу] в шапк", re.I)


def progress(path, i, n):
    im = Image.open(path).convert("RGB")
    d = ImageDraw.Draw(im)
    W = im.width
    m, gap, y, h = 72, 10, 22, 6
    seg = (W - 2 * m - gap * (n - 1)) / n
    for k in range(n):
        x0 = m + k * (seg + gap)
        col = (247, 147, 30) if k <= i else (214, 214, 228)
        d.rounded_rectangle([int(x0), y, int(x0 + seg), y + h], radius=3, fill=col)
    im.save(path, quality=93)


def card_no(path, i, n, dark):
    """маленький номер карточки «1 / 4» сверху по центру - порядок в альбоме Telegram"""
    im = Image.open(path).convert("RGB")
    d = ImageDraw.Draw(im)
    f = R.font("sans", 9, 800)  # R.font умножает на S=2 -> 18px
    t = f"{i + 1} / {n}"
    w = d.textlength(t, font=f)
    x0, y0 = (im.width - w) / 2 - 16, 18
    d.rounded_rectangle([x0, y0, x0 + w + 32, y0 + 32], radius=16,
                        fill=(255, 255, 255) if not dark else (40, 30, 80))
    d.text((im.width / 2, y0 + 16), t, font=f, fill=R.V1 if not dark else (230, 222, 255), anchor="mm")
    im.save(path, quality=93)


def plural_cards(n):
    return "КАРТОЧКИ" if n in (2, 3, 4) else "КАРТОЧЕК"


def tg_slide(s, i, n, cfg):
    t = copy.deepcopy(s)
    t.pop("tg", None)
    # авто-правки
    if t.get("label") and IG_ONLY.search(t["label"]):
        t["label"] = cfg.get("tg_label", f"{n} {plural_cards(n)}")
    for k in ("subtitle", "kicker", "chip", "cta"):
        if isinstance(t.get(k), str):
            t[k] = re.sub(r"[Кк]ак [^.]*?- на следующих слайдах\.?", "Коротко - на карточках ниже.", t[k])
            t[k] = re.sub(r"на следующих слайдах", "на карточках ниже", t[k])
            t[k] = re.sub(r"[Лл]истайте", "Смотрите карточки", t[k])
    if t.get("layout") == "checklist":
        t["save"] = t.get("save_tg", "Перешлите тому, кому пригодится")
    t.pop("save_tg", None)
    # ручные правки
    t.update(s.get("tg", {}))
    # проверка: не осталось инстаграм-призывов
    flat = json.dumps({k: v for k, v in t.items() if k not in ("ribbon", "art", "icon")}, ensure_ascii=False)
    m = IG_ONLY.search(flat)
    if m:
        raise R.Fail(f"Слайд {i + 1}: для Telegram остался призыв «{m.group(0)}...». "
                     f"Добавь в слайд поле \"tg\" с другим текстом.")
    return t


def main(cfg_path, out_dir):
    cfg = json.load(open(cfg_path, encoding="utf-8"))
    slides = cfg["slides"]
    if not 3 <= len(slides) <= 6:
        raise R.Fail("В карусели должно быть от 3 до 6 слайдов")
    if slides[-1].get("layout") != "offer":
        raise R.Fail("Последний слайд карусели - layout «offer»")
    n = len(slides)
    dark = {"dark", "myth", "pixel", "marquee", "offer"}
    for i, s in enumerate(slides):
        ig = {k: v for k, v in s.items() if k != "tg"}
        out = os.path.join(out_dir, f"post-{i + 1}.jpg")
        R.render(ig, out)
        progress(out, i, n)
        tg = tg_slide(s, i, n, cfg)
        out_tg = os.path.join(out_dir, f"tg-{i + 1}.jpg")
        R.render(tg, out_tg)
        if i == 0:
            # обложка для Facebook: та же адаптированная обложка, но без номера карточки
            R.render(tg, os.path.join(out_dir, "fb.jpg"))
        card_no(out_tg, i, n, tg.get("layout") in dark)
    shutil.copyfile(os.path.join(out_dir, "post-1.jpg"), os.path.join(out_dir, "post.jpg"))
    print("carousel", n, "slides ->", out_dir, "(Instagram: post-*.jpg, Telegram: tg-*.jpg, Facebook: fb.jpg)")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
