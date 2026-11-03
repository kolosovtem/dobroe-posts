#!/usr/bin/env python3
"""Рендер сторис БСК 1080x1920 (JPEG) из story.json.

Запуск: python3 -I bsk/render.py bsk/stories/<дата>/story.json bsk/stories/<дата>/story.jpg

Макеты (поле "layout"): photo, project, compare, bignum, tip. Описание полей - bsk/README.md.
В заголовках: "|" - перенос строки, *текст* - синий акцент.
"""
import html, json, os, re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
A = (ROOT / "assets").as_uri()
MAX_WORDS = {"compare": 70}  # остальные макеты - 40

CSS = """
@font-face{font-family:"BSK Text";src:url("@@A@@/fonts/bsk-text-regular.otf");font-weight:400}
@font-face{font-family:"BSK Text";src:url("@@A@@/fonts/bsk-text-bold.otf");font-weight:700}
@font-face{font-family:"BSK Display";src:url("@@A@@/fonts/bsk-display.otf")}
:root{--ink:#152033;--blue:#1358d8;--navy:#0b2a63;--ice:#edf3fa;--line:#d9e1eb;--muted:#667085}
*{box-sizing:border-box;margin:0;padding:0}
.s{width:1080px;height:1920px;position:relative;overflow:hidden;font-family:"BSK Text",sans-serif;color:var(--ink)}
.disp{font-family:"BSK Display",sans-serif;text-transform:uppercase;letter-spacing:-1px;line-height:.98;font-weight:400}
.disp em{font-style:normal;color:var(--blue)}
.grid{position:absolute;inset:0;background-image:linear-gradient(to right,rgba(21,32,51,.05) 1px,transparent 1px),linear-gradient(to bottom,rgba(21,32,51,.05) 1px,transparent 1px);background-size:90px 90px}
.gridw{background-image:linear-gradient(to right,rgba(255,255,255,.07) 1px,transparent 1px),linear-gradient(to bottom,rgba(255,255,255,.07) 1px,transparent 1px)}
.logo{position:absolute;top:160px;left:80px;height:84px}
.kicker{font-size:26px;letter-spacing:5px;text-transform:uppercase;font-weight:700;display:flex;align-items:center;gap:18px;color:var(--blue)}
.kicker:before{content:"";width:56px;height:4px;background:currentColor}
.foot{position:absolute;left:80px;right:80px;bottom:190px;display:flex;justify-content:space-between;align-items:center;font-size:30px;font-weight:700;color:var(--navy)}
.btn{background:var(--blue);color:#fff;padding:30px 44px;font-size:30px;font-weight:700;letter-spacing:1px}
.lead{font-size:34px;line-height:1.5;color:#3d4a60}
.dark{background:var(--navy);color:#fff}
.dark .kicker{color:#a9c6ff}.dark .disp em{color:#6fa0ff}.dark .lead{color:#d3ddef}.dark .foot{color:#b9c7e2}
.bg{position:absolute;inset:0;background-size:cover}
.shade{position:absolute;inset:0;background:linear-gradient(180deg,rgba(11,42,99,.85) 0%,rgba(11,42,99,.15) 30%,rgba(11,42,99,.45) 40%,rgba(8,26,64,.96) 58%,#081a40 100%)}
.stats{display:grid;grid-template-columns:repeat(3,1fr);border-top:2px solid rgba(255,255,255,.25);margin-top:50px}
.stats div{padding:34px 18px 0 0;font-size:24px;color:#b9c7e2;line-height:1.35}
.stats b{display:block;font-family:"BSK Display";font-size:62px;color:#fff;font-weight:400;margin-bottom:8px;white-space:nowrap}
.card{position:absolute;left:80px;right:80px;background:#fff;padding:64px 64px 70px;box-shadow:0 30px 80px rgba(21,32,51,.18)}
.card:before{content:"";position:absolute;left:0;top:0;width:14px;height:100%;background:var(--blue)}
.num{position:absolute;right:56px;top:46px;font-family:"BSK Display";font-size:30px;color:var(--muted);letter-spacing:2px;text-transform:uppercase}
.tags{display:flex;gap:16px;margin-top:40px;flex-wrap:wrap}
.tags span{border:2px solid var(--line);padding:14px 22px;font-size:22px;font-weight:700;letter-spacing:1.5px;text-transform:uppercase;color:var(--navy)}
.cols{display:grid;grid-template-columns:1fr 1fr;gap:28px}
.col{border:2px solid var(--line);background:#fff;padding:0 0 34px}
.col.a{border-color:var(--blue);box-shadow:0 24px 60px rgba(19,88,216,.14)}
.imgw{height:270px;background:var(--ice);display:flex;align-items:center;justify-content:center;overflow:hidden}
.imgw img{width:118%}
.imgw.ph{background-size:cover;background-position:center}
.lbl{padding:28px 34px 6px;font-size:22px;letter-spacing:3px;text-transform:uppercase;font-weight:700;color:var(--blue)}
.col h3{padding:0 34px;font-family:"BSK Display";font-weight:400;font-size:46px;text-transform:uppercase;color:var(--navy);line-height:1.05;min-height:100px}
dl{padding:10px 34px 0}
dl div{display:flex;justify-content:space-between;gap:12px;border-top:1px solid var(--line);padding:18px 0;font-size:25px}
dt{color:var(--muted)} dd{font-weight:700;text-align:right}
.for{padding:16px 34px 0;font-size:24px;line-height:1.45;color:#3d4a60}
.big{font-family:"BSK Display";color:var(--blue);line-height:.9;letter-spacing:-6px;white-space:nowrap}
.unit{font-family:"BSK Display";text-transform:uppercase;font-size:64px;color:var(--navy);margin-top:14px}
.frame{position:absolute;left:80px;right:80px;height:520px;background-size:cover;background-position:center}
.frame:after{content:"";position:absolute;left:-18px;top:-18px;width:120px;height:120px;border-left:8px solid var(--blue);border-top:8px solid var(--blue)}
.pts{margin-top:56px;display:flex;flex-direction:column;gap:26px}
.pts div{display:flex;gap:28px;align-items:flex-start;background:#fff;border:2px solid var(--line);padding:40px 40px;font-size:38px;line-height:1.35;font-weight:700;color:var(--navy)}
.pts i{font-style:normal;font-family:"BSK Display";color:var(--blue);font-size:40px;line-height:1;min-width:52px}
"""


def e(t):
    return html.escape(str(t or ""))


def title(t):
    t = e(t).replace("|", "<br>")
    return re.sub(r"\*(.+?)\*", r"<em>\1</em>", t)


def img(p):
    """Путь картинки относительно bsk/assets (например projects/meerim.webp)."""
    f = ROOT / "assets" / p
    if not f.exists():
        sys.exit(f"Нет картинки: {f}")
    return f.as_uri()


def foot(d):
    right = d.get("foot", "paneli.kg")
    return f'<div class="foot"><span class="btn">{e(d.get("button","Получить расчёт"))} →</span><span>{e(right)}</span></div>'


def kicker(d):
    return f'<div class="kicker">{e(d.get("kicker",""))}</div>' if d.get("kicker") else ""


def L_photo(d):
    pos = d.get("focus", "center")
    stats = "".join(f'<div><b>{e(s[0])}</b>{e(s[1])}</div>' for s in d.get("stats", []))
    stats = f'<div class="stats">{stats}</div>' if stats else ""
    top = d.get("text_top", 850 if stats else 1000)
    return f'''<div class="s dark"><div class="bg" style="background-image:url({img(d["photo"])});background-position:{pos}"></div>
<div class="shade"></div><div class="grid gridw"></div><img class="logo" src="{A}/img/logo-white.png">
<div style="position:absolute;left:80px;right:80px;top:{top}px">{kicker(d)}
<h1 class="disp" style="font-size:{d.get("size",128)}px;margin:30px 0 36px">{title(d["title"])}</h1>
<div class="lead" style="max-width:880px">{e(d.get("text",""))}</div>{stats}</div>{foot(d)}</div>'''


def L_project(d):
    pos = d.get("focus", "center")
    tags = "".join(f"<span>{e(t)}</span>" for t in d.get("tags", []))
    return f'''<div class="s" style="background:var(--ice)"><div class="grid"></div>
<div style="position:absolute;left:0;right:0;top:0;height:1000px;background:url({img(d["photo"])}) {pos}/cover"></div>
<div style="position:absolute;left:0;right:0;top:0;height:1000px;background:linear-gradient(180deg,rgba(11,42,99,.65),rgba(11,42,99,0) 28%)"></div>
<img class="logo" src="{A}/img/logo-white.png">
<div class="card" style="top:780px"><div class="num">{e(d.get("num",""))}</div>{kicker(d)}
<h1 class="disp" style="font-size:{d.get("size",104)}px;margin:28px 0 30px;color:var(--navy)">{title(d["title"])}</h1>
<p class="lead" style="font-size:33px">{e(d.get("text",""))}</p><div class="tags">{tags}</div></div>{foot(d)}</div>'''


def L_compare(d):
    cols = ""
    for i, c in enumerate(d["cols"][:2]):
        rows = "".join(f"<div><dt>{e(k)}</dt><dd>{e(v)}</dd></div>" for k, v in c.get("rows", []))
        if c.get("cutout"):
            pic = f'<div class="imgw"><img src="{img(c["cutout"])}"></div>'
        else:
            pic = f'<div class="imgw ph" style="background-image:url({img(c["photo"])})"></div>'
        cols += f'''<div class="col{' a' if i == 0 else ''}">{pic}<div class="lbl">{e(c.get("label",""))}</div>
<h3>{title(c["name"])}</h3><dl>{rows}</dl><div class="for">{e(c.get("for",""))}</div></div>'''
    return f'''<div class="s" style="background:#fff"><div class="grid"></div><img class="logo" src="{A}/img/logo-navy.png">
<div style="position:absolute;left:80px;right:80px;top:320px">{kicker(d)}
<h1 class="disp" style="font-size:{d.get("size",86)}px;margin-top:30px;color:var(--navy)">{title(d["title"])}</h1></div>
<div class="cols" style="position:absolute;left:80px;right:80px;top:740px">{cols}</div>
<div style="position:absolute;left:80px;right:80px;top:1525px;font-size:30px;line-height:1.4">{e(d.get("text",""))}</div>{foot(d)}</div>'''


def L_bignum(d):
    dark = d.get("dark", False)
    return f'''<div class="s{' dark' if dark else ''}" style="{'' if dark else 'background:#fff'}"><div class="grid{' gridw' if dark else ''}"></div>
<img class="logo" src="{A}/img/{'logo-white' if dark else 'logo-navy'}.png">
<div style="position:absolute;left:80px;right:80px;top:340px">{kicker(d)}
<div class="big" style="font-size:{d.get("size",300)}px;margin-top:40px;{'color:#6fa0ff' if dark else ''}">{e(d["number"])}</div>
<div class="unit" style="{'color:#fff' if dark else ''}">{title(d.get("unit",""))}</div>
<div class="lead" style="margin-top:30px;max-width:900px">{e(d.get("text",""))}</div></div>
<div class="frame" style="top:1120px;background-image:url({img(d["photo"])});background-position:{d.get("focus","center")}"></div>{foot(d)}</div>'''


def L_tip(d):
    pts = "".join(f"<div><i>{i+1:02d}</i><span>{e(p)}</span></div>" for i, p in enumerate(d.get("points", [])[:3]))
    return f'''<div class="s" style="background:var(--ice)"><div class="grid"></div>
<div style="position:absolute;left:0;right:0;top:0;height:640px;background:url({img(d["photo"])}) {d.get("focus","center")}/cover"></div>
<div style="position:absolute;left:0;right:0;top:0;height:640px;background:linear-gradient(180deg,rgba(11,42,99,.7),rgba(11,42,99,.1) 45%,rgba(237,243,250,0) 70%,var(--ice))"></div>
<img class="logo" src="{A}/img/logo-white.png">
<div style="position:absolute;left:80px;right:80px;top:600px">{kicker(d)}
<h1 class="disp" style="font-size:{d.get("size",84)}px;margin-top:26px;color:var(--navy)">{title(d["title"])}</h1>
<div class="pts">{pts}</div></div>{foot(d)}</div>'''


LAYOUTS = {"photo": L_photo, "project": L_project, "compare": L_compare, "bignum": L_bignum, "tip": L_tip}


def words(d):
    out = []
    def walk(x, k=""):
        if k in ("layout", "photo", "cutout", "focus", "size", "text_top", "dark", "foot", "caption", "caption_tg", "topic"):
            return
        if isinstance(x, str):
            out.extend(re.findall(r"[\wА-Яа-яЁё]+", x))
        elif isinstance(x, list):
            for i in x: walk(i)
        elif isinstance(x, dict):
            for kk, v in x.items(): walk(v, kk)
    walk(d)
    return len(out)


def main():
    src, dst = sys.argv[1], sys.argv[2]
    d = json.load(open(src, encoding="utf-8"))
    raw = json.dumps(d, ensure_ascii=False)
    if "—" in raw or "–" in raw:
        sys.exit("В story.json есть длинное/среднее тире. Используйте дефис '-'.")
    n = words(d)
    lim = MAX_WORDS.get(d.get("layout"), 40)
    if n > lim:
        sys.exit(f"На картинке {n} слов, максимум {lim}. Сократите текст.")
    if d.get("layout") not in LAYOUTS:
        sys.exit(f"Неизвестный layout. Доступны: {', '.join(LAYOUTS)}")
    body = LAYOUTS[d["layout"]](d)
    page = f'<!doctype html><html><head><meta charset="utf-8"><style>{CSS.replace("@@A@@", A)}</style></head><body>{body}</body></html>'
    tmp = Path(dst).resolve().with_suffix(".html")
    tmp.write_text(page, encoding="utf-8")
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={"width": 1080, "height": 1920})
        pg.goto(tmp.as_uri())
        pg.evaluate("document.fonts.ready")
        pg.wait_for_timeout(400)
        # проверка переполнения: текст не должен вылезать за край кадра и заходить на кнопку
        bad = pg.evaluate("""() => {
          const s=document.querySelector('.s').getBoundingClientRect();
          const f=document.querySelector('.foot').getBoundingClientRect();
          const out=[];
          document.querySelectorAll('h1,.lead,.stats,.tags,.cols,.pts,.unit,.big,.card').forEach(el=>{
            const r=el.getBoundingClientRect();
            if(r.right>s.right-40) out.push(el.className+'|'+el.tagName+': вылезает справа');
            if(r.bottom>f.top-20 && !el.closest('.foot')) out.push(el.className+'|'+el.tagName+': заходит на кнопку');
          });
          return out;}""")
        png = Path(dst).with_suffix(".png")
        pg.screenshot(path=str(png), clip={"x": 0, "y": 0, "width": 1080, "height": 1920})
        b.close()
    tmp.unlink()
    from PIL import Image
    Image.open(png).convert("RGB").save(dst, "JPEG", quality=92, optimize=True)
    png.unlink()
    if bad:
        print("ВНИМАНИЕ, проверьте макет:\n  " + "\n  ".join(bad))
        sys.exit(2)
    print(f"OK {dst} ({n} слов)")


if __name__ == "__main__":
    main()
