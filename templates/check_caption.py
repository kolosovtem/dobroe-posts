"""Проверка подписей перед публикацией: длина, тире, контактный блок, запрещённые слова.

Запуск:  python3 -I templates/check_caption.py posts/<папка>
Проверяет caption.txt, caption-tg.txt, caption-fb.txt (какие есть). Падает с понятной ошибкой.
"""
import html
import os
import re
import sys

MAX_BODY = 650  # символов до хэштегов и контактов - коротко, как пишет живой человек
CONTACT_MARK = "📞 +996 222 522 235"
TG_ONLY_BAD = re.compile(r"листа|слайд|свайп|сохрани|в профил|в директ|ссылк[аеу] в шапк", re.I)


def body(text):
    """текст до блока хэштегов / контактов"""
    lines = text.strip().splitlines()
    out = []
    for l in lines:
        s = l.strip()
        if s.startswith("🌐") or (s and all(w.startswith("#") for w in s.split())):
            break
        out.append(l)
    return "\n".join(out).strip()


def check(path, kind):
    t = open(path, encoding="utf-8").read()
    errs = []
    if "—" in t or "–" in t:
        errs.append("есть длинное тире - замени на «-»")
    if CONTACT_MARK not in t:
        errs.append("нет контактного блока в конце")
    b = body(t)
    if kind == "tg":
        b = html.unescape(re.sub(r"<[^>]+>", "", b))
        if TG_ONLY_BAD.search(t):
            errs.append(f"инстаграм-слово для Telegram: «{TG_ONLY_BAD.search(t).group(0)}»")
    if kind == "fb" and re.search(r"листа|слайд|свайп|в профил|в директ|ссылк[аеу] в шапк", t, re.I):
        errs.append("инстаграм-слово в тексте для Facebook")
    n_list = sum(1 for l in b.splitlines() if re.match(r"\s*(-|\d+[.)])\s", l))
    if len(b) > MAX_BODY:
        errs.append(f"текст {len(b)} символов, максимум {MAX_BODY}: сократи, оставь одну мысль")
    if n_list > 4:
        errs.append(f"{n_list} пунктов в списке, максимум 4")
    tags = re.findall(r"#\w+", t)
    if kind == "ig" and len(tags) > 5:
        errs.append("больше 5 хэштегов")
    return len(b), errs


def main(folder):
    bad = False
    for name, kind in (("caption.txt", "ig"), ("caption-tg.txt", "tg"), ("caption-fb.txt", "fb")):
        p = os.path.join(folder, name)
        if not os.path.exists(p):
            continue
        n, errs = check(p, kind)
        print(f"{name}: {n} симв. {'OK' if not errs else '; '.join(errs)}")
        bad |= bool(errs)
    if bad:
        sys.exit(1)


if __name__ == "__main__":
    main(sys.argv[1])
