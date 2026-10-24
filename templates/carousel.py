"""Карусель для Instagram/Telegram: несколько слайдов 1080x1350 из одного конфига.

Запуск:  python3 -I templates/carousel.py posts/<папка>/carousel.json posts/<папка>
Конфиг:  {"slides": [ {<конфиг слайда как для render.py>}, ... ]}   - от 3 до 6 слайдов
  - слайд 1 - обложка (сильный заголовок, интрига, label вроде "ЛИСТАЙТЕ ->")
  - середина - польза (steps / checklist / compare / stat / myth / chat ...)
  - последний - "offer": услуга агентства по теме + контакты
Результат: post-1.jpg ... post-N.jpg и копия обложки post.jpg.
Сверху каждого слайда рисуется индикатор листания (N сегментов).
"""
import json
import os
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from PIL import Image, ImageDraw  # noqa: E402

import render as R  # noqa: E402


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


def main(cfg_path, out_dir):
    cfg = json.load(open(cfg_path, encoding="utf-8"))
    slides = cfg["slides"]
    if not 3 <= len(slides) <= 6:
        raise R.Fail("В карусели должно быть от 3 до 6 слайдов")
    if slides[-1].get("layout") != "offer":
        raise R.Fail("Последний слайд карусели - layout «offer»")
    n = len(slides)
    for i, s in enumerate(slides):
        out = os.path.join(out_dir, f"post-{i + 1}.jpg")
        R.render(s, out)
        progress(out, i, n)
    shutil.copyfile(os.path.join(out_dir, "post-1.jpg"), os.path.join(out_dir, "post.jpg"))
    print("carousel", n, "slides ->", out_dir)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
