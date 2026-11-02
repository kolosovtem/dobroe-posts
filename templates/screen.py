"""Макет `screen` - реалистичный экран (поиск Google, реклама, профиль Instagram, сайт,
таблица заявок, карточка на картах, уведомления на телефоне) + крупный заголовок.

Вызывается сам из render.py (layout "screen") и из story.py (type "layout"), отдельно:
  python3 -I templates/screen.py config.json out.jpg
Рисуется через Chromium (playwright). Если playwright недоступен - рендер падает с понятной ошибкой,
тогда выбери другой макет.

Поля:
  layout  "screen"
  screen  serp | ads | insta | site | sheet | maps | notify
  theme   violet orange lemon mint sky pink cream night white (как у афиш)
  title   3-7 слов, [[акцент]]                 (считается в лимит 26 слов)
  subtitle, label, tag                         (по желанию)
  ui      {...} - текст внутри экрана (см. ниже), до 30 слов, только примеры «как это выглядит»:
          не выдавать за реальных клиентов, без выдуманных цифр результатов.
    serp:   query, site, headline, text
    ads:    query, site, headline, text, links [до 4]
    insta:  name, bio, photos [6 имён из assets/photos]
    site:   (без полей - скриншот dobroe.agency)
    sheet:  rows [[источник, канал, статус]] до 6; статус: Новая | В работе | Продажа | Отказ
    maps:   name, kind, address, hours
    notify: items [[приложение, заголовок, текст]] до 3; приложение: whatsapp | telegram | instagram | mail | site
"""
import html
import json
import os
import re
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import render as R  # noqa: E402

FD = R.FD
ROOT = R.ROOT
UI_MAX = 30


def rgb(c):
    return "rgb(%d,%d,%d)" % tuple(c)


def rich(s, hot):
    s = html.escape(s).replace("\\n", "<br>").replace("\n", "<br>")
    return re.sub(r"\[\[(.+?)\]\]", lambda m: f'<span style="color:{hot}">{m.group(1)}</span>', s)


def esc(s):
    return html.escape(str(s))


def fileurl(p):
    return "file://" + os.path.abspath(p)


DEFAULTS = {
    "serp": {"query": "ремонт квартир бишкек", "site": "vash-sait.kg", "headline": "Ремонт квартир в Бишкеке под ключ",
             "text": "Смета за 1 день, фото объектов и цены за м²."},
    "ads": {"query": "доставка цветов бишкек", "site": "vash-sait.kg", "headline": "Доставка цветов по Бишкеку",
            "text": "Фото букета перед отправкой.", "links": ["Розы", "Букеты", "Доставка сегодня"]},
    "insta": {"name": "vash.biznes", "bio": "Кофейня в центре Бишкека", "photos": ["barista_latte", "cafe_signboard", "barista_serving",
                                                                                     "cafe_owners", "barista_urban", "store_counter"]},
    "site": {},
    "sheet": {"rows": [["Instagram", "Таргет", "Новая"], ["Google", "Поиск", "В работе"], ["WhatsApp", "Сайт", "Продажа"],
                       ["Telegram", "Бот", "Продажа"], ["2ГИС", "Карточка", "В работе"]]},
    "maps": {"name": "Кофейня «Ваше название»", "kind": "Кофейня", "address": "ул. Киевская, Бишкек", "hours": "Открыто до 22:00"},
    "notify": {"items": [["whatsapp", "Новая заявка", "Здравствуйте, сколько стоит?"], ["site", "Заявка с сайта", "Имя, телефон, услуга"],
                         ["instagram", "Сообщение в директ", "Можно записаться на завтра?"]]},
}

STATUS = {"Новая": ("#e8f0fe", "#1967d2"), "В работе": ("#fef7e0", "#b06000"), "Продажа": ("#e6f4ea", "#137333"),
          "Отказ": ("#fce8e6", "#c5221f")}
APP = {"whatsapp": ("#25D366", "W"), "telegram": ("#2AABEE", "T"), "instagram": ("#E1306C", "I"), "mail": ("#5E16EA", "@"),
       "site": ("#0B1220", "S")}

BAR = ('<div class="bar"><i style="background:#ff5f57"></i><i style="background:#febc2e"></i><i style="background:#28c840"></i>'
       '<span class="addr">{}</span></div>')


def ui_serp(u):
    others = "".join(f'<div class="res dim"><div class="site"><span class="fav">{n[0].upper()}</span><b>{n}</b></div><div class="t">{t}</div></div>'
                     for n, t in [("remont-kg.com", "Ремонт квартир - цены"), ("stroy-servis.kg", "Отделка помещений")])
    return f'''<div class="win full">{BAR.format("google.com/search?q=" + esc(u["query"]).replace(" ", "+"))}
<div class="pad"><div class="q">{esc(u["query"])}<span>⌕</span></div>
<div class="res hl"><div class="site"><span class="fav v">{esc(u["site"])[0].upper()}</span><div><b>{esc(u["site"])}</b><div class="url">https://{esc(u["site"])}</div></div></div>
<div class="t">{esc(u["headline"])}</div><div class="d">{esc(u["text"])}</div></div>{others}</div></div>'''


def ui_ads(u):
    links = "".join(f"<span>{esc(x)}</span>" for x in u.get("links", [])[:4])
    bars = "".join(f'<i style="height:{v}%"></i>' for v in [28, 36, 33, 50, 46, 64, 78])
    return f'''<div class="win full">{BAR.format("google.com/search?q=" + esc(u["query"]).replace(" ", "+"))}
<div class="pad"><div class="q">{esc(u["query"])}<span>⌕</span></div>
<div class="res"><div style="font-weight:700;font-size:15px">Реклама</div>
<div class="site" style="margin-top:8px"><span class="fav v">{esc(u["site"])[0].upper()}</span><div><b>{esc(u["site"])}</b><div class="url">https://{esc(u["site"])}</div></div></div>
<div class="t">{esc(u["headline"])}</div><div class="d">{esc(u["text"])}</div><div class="links">{links}</div></div>
<div class="kpi"><div><small>Заявки по дням</small><div class="bars">{bars}</div></div></div></div></div>'''


def ui_insta(u):
    ph = u.get("photos", [])[:6]
    for p in ph:
        if not os.path.exists(os.path.join(ROOT, "assets", "photos", p + ".jpg")):
            raise R.Fail(f"Нет фото assets/photos/{p}.jpg")
    tiles = "".join(f'<div style="background:url({fileurl(os.path.join(ROOT, "assets", "photos", p + ".jpg"))}) center/cover"></div>' for p in ph)
    return f'''<div class="win phone">
<div style="padding:20px 18px 8px;display:flex;align-items:center;gap:18px">
<div class="ava"><div></div></div>
<div style="flex:1;display:flex;justify-content:space-around;text-align:center;font-size:14px"><div><b style="font-size:18px">Посты</b></div><div><b style="font-size:18px">Reels</b></div><div><b style="font-size:18px">Отметки</b></div></div></div>
<div style="padding:0 18px;font-size:15px;line-height:1.4"><b>{esc(u["name"])}</b><br>{esc(u["bio"])}</div>
<div style="display:flex;gap:8px;padding:12px 18px"><span class="btn">Подписаться</span><span class="btn">Сообщение</span></div>
<div class="grid3">{tiles}</div></div>'''


def ui_site(u):
    shot = fileurl(os.path.join(ROOT, "assets", "img", "site_dobroe.jpg"))
    return f'''<div class="win full">{BAR.format("🔒 dobroe.agency")}<div style="position:absolute;top:44px;left:0;right:0;bottom:0;background:url({shot}) top center/100% auto no-repeat"></div></div>'''


def ui_sheet(u):
    rows = ""
    for src, ch, st in u["rows"][:6]:
        bg, fg = STATUS.get(st, STATUS["Новая"])
        rows += f'<tr><td><b>{esc(src)}</b></td><td>{esc(ch)}</td><td><span class="st" style="background:{bg};color:{fg}">{esc(st)}</span></td></tr>'
    return f'''<div class="win full"><div class="bar" style="background:#f8f9fa"><i style="background:#0f9d58;border-radius:4px;width:22px;height:22px"></i><b style="font-size:16px;margin-left:8px">Заявки - все каналы</b></div>
<div class="pad"><table><tr class="th"><td>Источник</td><td>Канал</td><td>Статус</td></tr>{rows}</table></div></div>'''


def ui_maps(u):
    return f'''<div class="win full" style="background:#e8eef3">
<div style="position:absolute;inset:0;background:
 linear-gradient(90deg,transparent 47%,#fff 47%,#fff 50%,transparent 50%),linear-gradient(0deg,transparent 30%,#fff 30%,#fff 33%,transparent 33%),
 linear-gradient(25deg,transparent 60%,#fbe7a1 60%,#fbe7a1 63%,transparent 63%),#e3ebe3"></div>
<div style="position:absolute;left:46%;top:18%;width:54px;height:54px;border-radius:50% 50% 50% 0;transform:rotate(-45deg);background:#E5243B;box-shadow:0 8px 16px rgba(0,0,0,.3)"></div>
<div style="position:absolute;left:18px;right:18px;bottom:18px;background:#fff;border-radius:18px;padding:22px 24px;box-shadow:0 10px 30px rgba(0,0,0,.18)">
 <div style="font-size:24px;font-weight:800">{esc(u["name"])}</div>
 <div style="font-size:16px;color:#5f6368;margin-top:4px">{esc(u["kind"])} · {esc(u["address"])}</div>
 <div style="font-size:16px;color:#137333;font-weight:700;margin-top:8px">{esc(u["hours"])}</div>
 <div style="display:flex;gap:10px;margin-top:16px">{"".join(f'<span class="mbtn">{x}</span>' for x in ["Маршрут", "Позвонить", "Сайт"])}</div>
</div></div>'''


def ui_notify(u):
    items = ""
    for app, t, d in u["items"][:3]:
        col, ch = APP.get(app, APP["site"])
        items += f'''<div class="note"><span class="app" style="background:{col}">{ch}</span><div style="flex:1"><div style="display:flex;justify-content:space-between"><b>{esc(t)}</b><small>сейчас</small></div><div>{esc(d)}</div></div></div>'''
    return f'''<div class="win phone lock"><div style="text-align:center;color:#fff;margin-top:34px"><div style="font-size:20px;opacity:.85">вторник</div><div style="font-size:92px;font-weight:300;line-height:1">9:41</div></div>
<div style="padding:26px 14px;display:flex;flex-direction:column;gap:10px">{items}</div></div>'''


UIS = {"serp": ui_serp, "ads": ui_ads, "insta": ui_insta, "site": ui_site, "sheet": ui_sheet, "maps": ui_maps, "notify": ui_notify}

CSS = '''
@font-face{font-family:Jost;src:url(%(fd)s/Jost[wght].ttf);font-weight:100 900}
@font-face{font-family:Manrope;src:url(%(fd)s/Manrope[wght].ttf);font-weight:200 800}
*{box-sizing:border-box;margin:0;padding:0}
body{width:1080px;height:1350px;overflow:hidden;font-family:Manrope,sans-serif;-webkit-font-smoothing:antialiased}
.st0{position:relative;width:1080px;height:1350px;overflow:hidden;background:linear-gradient(%(ang)sdeg,%(b1)s,%(b2)s);color:%(ink)s}
.blob{position:absolute;border-radius:50%%;background:rgba(255,255,255,.18)}
.logo{position:absolute;left:72px;top:62px;height:52px;image-rendering:pixelated}
.label{position:absolute;right:72px;top:66px;border:2px solid %(ink)s;border-radius:999px;padding:8px 18px;font-weight:700;font-size:17px;letter-spacing:.08em}
h1{font-family:Jost;font-weight:800;line-height:1;letter-spacing:-.01em}
.sub{font-weight:700;font-size:30px;color:%(sub)s;margin-top:22px;line-height:1.3}
.tag{position:absolute;left:72px;top:1236px;height:54px;border-radius:999px;padding:0 22px;display:flex;align-items:center;font-weight:800;font-size:20px;letter-spacing:.06em;background:%(ink)s;color:%(tagfg)s}
.site_{position:absolute;right:72px;top:1250px;font-weight:800;font-size:22px;letter-spacing:.02em}
.stage{position:absolute;left:72px;right:72px}
.win{position:absolute;background:#fff;color:#202124;border-radius:22px;overflow:hidden;box-shadow:0 40px 80px rgba(0,0,0,.35),0 0 0 1px rgba(0,0,0,.05)}
.full{inset:0}
.phone{left:50%%;transform:translateX(-50%%);width:470px;top:0;bottom:0;border-radius:52px;border:12px solid #111}
.lock{background:linear-gradient(160deg,#6a5acd,#1e3a8a 60%%,#0f172a)}
.bar{height:44px;background:#f1f3f4;display:flex;align-items:center;gap:8px;padding:0 18px;border-bottom:1px solid #e3e3e3}
.bar i{width:13px;height:13px;border-radius:50%%;display:block}
.addr{flex:1;margin-left:14px;height:26px;border-radius:13px;background:#fff;font-size:14px;color:#5f6368;display:flex;align-items:center;padding:0 14px}
.pad{padding:24px 30px;zoom:1.32}
.q{display:flex;align-items:center;border:1px solid #dfe1e5;border-radius:26px;height:50px;padding:0 22px;font-size:20px;box-shadow:0 1px 6px rgba(32,33,36,.18)}
.q span{margin-left:auto;color:#4285f4}
.res{margin-top:20px}.res .site{display:flex;align-items:center;gap:10px;font-size:15px}
.fav{width:28px;height:28px;border-radius:50%%;background:#f1f3f4;display:grid;place-items:center;font-size:14px;font-weight:800;color:#888}
.fav.v{color:#5E16EA}.url{color:#4d5156;font-size:13px}
.res .t{font-size:23px;color:#1a0dab;margin-top:6px}.res .d{font-size:16px;color:#4d5156;margin-top:4px;line-height:1.45}
.hl{background:#f5f0ff;border:2px solid #8B5CF6;border-radius:14px;padding:14px 16px;margin-left:-16px;margin-right:-16px}
.dim{opacity:.35}
.links{display:grid;grid-template-columns:1fr 1fr;gap:10px 40px;margin-top:14px;font-size:17px;color:#1a0dab}
.kpi{margin-top:22px;border:1px solid #e3e3e3;border-radius:14px;padding:14px 16px}.kpi small{color:#5f6368;font-size:13px}
.bars{display:flex;align-items:flex-end;gap:8px;height:70px;margin-top:8px}.bars i{flex:1;background:#49B5E7;border-radius:4px;display:block}
.ava{width:84px;height:84px;border-radius:50%%;padding:3px;background:conic-gradient(#feda75,#fa7e1e,#d62976,#962fbf,#4f5bd5,#feda75)}
.ava div{width:100%%;height:100%%;border-radius:50%%;background:#fff;border:3px solid #fff}
.btn{flex:1;background:#efefef;border-radius:8px;text-align:center;font-size:14px;font-weight:700;padding:8px}
.grid3{display:grid;grid-template-columns:repeat(3,1fr);gap:2px}.grid3 div{aspect-ratio:1}
table{width:100%%;border-collapse:collapse;font-size:19px}td{padding:16px 0;border-top:1px solid #f1f1f1}
.th td{color:#5f6368;font-size:14px;border:0}
.st{border-radius:14px;padding:4px 12px;font-weight:700;font-size:15px}
.mbtn{flex:1;text-align:center;background:#eef3fe;color:#1967d2;border-radius:12px;padding:10px;font-weight:700;font-size:15px}
.note{display:flex;gap:12px;background:rgba(255,255,255,.88);backdrop-filter:blur(8px);border-radius:20px;padding:14px 16px;font-size:15px;line-height:1.35}
.note small{color:#666}.app{width:40px;height:40px;border-radius:10px;color:#fff;display:grid;place-items:center;font-weight:800;flex:none}
'''


def count(v):
    return R.count_words(v)


def build_html(cfg):
    R.check_dashes(cfg)
    kind = cfg.get("screen")
    if kind not in UIS:
        raise R.Fail(f"Неизвестный screen «{kind}». Доступны: {', '.join(UIS)}")
    main = {k: v for k, v in cfg.items() if k not in ("ui", "screen")}
    R.check_words(main)
    ui = {**DEFAULTS[kind], **cfg.get("ui", {})}
    if count(ui) > UI_MAX:
        raise R.Fail(f"Внутри экрана {count(ui)} слов, максимум {UI_MAX}: сократи поле ui")
    th = R.theme(cfg, "white")
    b1, b2, ink, hot, sub, dark = th
    logo = R.logo_img(dark)
    tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
    logo.save(tmp.name)
    title = cfg["title"]
    n = len(title.replace("[[", "").replace("]]", ""))
    size = 112 if n <= 22 else 96 if n <= 34 else 80 if n <= 48 else 68
    lab = f'<div class="label">{esc(cfg["label"])}</div>' if cfg.get("label") else ""
    tag = f'<div class="tag">{esc(cfg["tag"])}</div>' if cfg.get("tag") else ""
    subt = f'<div class="sub">{rich(cfg["subtitle"], rgb(hot))}</div>' if cfg.get("subtitle") else ""
    ang = (sum(map(ord, title)) % 4) * 40 + 20
    css = CSS % {"fd": fileurl(FD), "b1": rgb(b1), "b2": rgb(b2), "ink": rgb(ink), "sub": rgb(sub), "ang": ang,
                 "tagfg": rgb(b1) if ink == R.WHITE else "#fff"}
    top_ui = 190 + 0  # заголовок сверху, экран занимает остаток
    body = f'''<div class="st0"><div class="blob" style="width:760px;height:760px;right:-260px;top:-200px"></div>
<div class="blob" style="width:420px;height:420px;left:-160px;bottom:-140px;opacity:.6"></div>
<img class="logo" src="{fileurl(tmp.name)}">{lab}
<div class="stage" id="head" style="top:{top_ui}px"><h1 style="font-size:{size}px">{rich(title, rgb(hot))}</h1>{subt}</div>
<div class="stage" id="ui" style="bottom:150px;overflow:visible">{UIS[kind](ui)}</div>
{tag}<div class="site_">dobroe.agency</div></div>
<script>
const h=document.getElementById('head'),u=document.getElementById('ui');
u.style.top=(h.offsetTop+h.offsetHeight+46)+'px';
</script>'''
    return f'<!doctype html><html><head><meta charset="utf-8"><style>{css}</style></head><body>{body}</body></html>', tmp.name


def render(cfg, out):
    try:
        from playwright.sync_api import sync_playwright
    except Exception:
        raise R.Fail("Для макета screen нужен playwright (Chromium). Выбери другой макет.")
    doc, logo_tmp = build_html(cfg)
    with tempfile.NamedTemporaryFile("w", suffix=".html", delete=False, encoding="utf-8") as f:
        f.write(doc)
        hp = f.name
    with sync_playwright() as p:
        exe = "/opt/pw-browsers/chromium" if os.path.exists("/opt/pw-browsers/chromium") and os.path.isfile("/opt/pw-browsers/chromium") else None
        b = p.chromium.launch(**({"executable_path": exe} if exe else {}))
        pg = b.new_page(viewport={"width": 1080, "height": 1350})
        pg.goto("file://" + hp, wait_until="load")
        pg.evaluate("document.fonts.ready")
        pg.wait_for_timeout(200)
        # заголовок не должен залезать на экран слишком сильно: экран минимум 520 px
        hgt = pg.evaluate("document.getElementById('ui').getBoundingClientRect().height")
        if hgt < 480:
            b.close()
            raise R.Fail("Заголовок слишком длинный - экрану не хватает места: сократи title/subtitle")
        pg.screenshot(path=out, type="jpeg", quality=93)
        b.close()
    os.unlink(hp)
    os.unlink(logo_tmp)
    print("saved", out, "layout screen", cfg.get("screen"))


if __name__ == "__main__":
    render(json.load(open(sys.argv[1], encoding="utf-8")), sys.argv[2])
