"""Render ARWEB Instagram visuals (1080x1350 PNG) from a content JSON file.

Usage: python3 tools/render.py content/mois-1.json [post_id ...]
Output: <YYYY-MM>/<id>-<slug>/<n>.png at the repo root.
"""
import html
import json
import re
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
TOOLS = ROOT / "tools"
LOGO = (TOOLS / "logo.svg").read_text()
MARK = (TOOLS / "mark.svg").read_text()

PILLARS = {
    "Diagnostic": ("#e8f0fe", "#0b57d0"),
    "Visibilité locale": ("#e6f4ea", "#137333"),
    "SEO": ("#fef7e0", "#b06000"),
    "Méthode": ("#f1f3f4", "#202124"),
}


def fr(text: str) -> str:
    """Escape for HTML and apply French typography (apostrophes, non-breaking spaces)."""
    t = text.replace("'", "’")
    t = re.sub(r" ([:])", " \\1", t)
    t = re.sub(r" ([;!?])", " \\1", t)
    t = t.replace("« ", "« ").replace(" »", " »")
    t = re.sub(r"(\d) (?=\w)", "\\1\u00a0", t)
    return html.escape(t, quote=False)


CSS = f"""
@font-face{{font-family:Bricolage;src:url('{(TOOLS / "fonts/bricolage-grotesque-latin-600-normal.woff2").as_uri()}');font-weight:600}}
@font-face{{font-family:Bricolage;src:url('{(TOOLS / "fonts/bricolage-grotesque-latin-700-normal.woff2").as_uri()}');font-weight:700}}
:root{{--blue:#0b57d0;--ink:#202124;--muted:#5f6368;--line:#dadce0;--pale:#e8f0fe;--pale2:#f0f6ff;
--green:#137333;--gpale:#e6f4ea;--red:#b3261e;--rpale:#fce8e6;--amber:#b06000;--apale:#fef7e0}}
*{{box-sizing:border-box;margin:0;padding:0}}
html,body{{width:1080px;height:1350px}}
body{{font-family:Inter,Arial,sans-serif;color:var(--ink);background:#fff;-webkit-font-smoothing:antialiased;
display:flex;flex-direction:column;padding:88px 96px 72px;position:relative;overflow:hidden}}
h1,h2,.big{{font-family:Bricolage,Inter,sans-serif;font-weight:600;letter-spacing:-.03em;line-height:1.05}}
.top{{display:flex;justify-content:space-between;align-items:center}}
.chip{{display:inline-block;font-weight:700;font-size:24px;letter-spacing:.1em;text-transform:uppercase;
padding:14px 26px;border-radius:999px}}
.main{{flex:1;display:flex;flex-direction:column;justify-content:center}}
.foot{{display:flex;justify-content:space-between;align-items:center;border-top:2px solid var(--line);padding-top:32px}}
.foot .logo svg{{height:52px;width:auto}}
.foot span{{font-size:26px;color:var(--muted);font-weight:600}}
/* cover */
body.cover{{background:var(--pale2)}}
body.cover .bgmark{{position:absolute;right:-230px;bottom:120px;width:720px;opacity:.06}}
body.cover h1{{font-size:96px;margin:40px 0 44px}}
body.cover .sub{{font-size:40px;color:var(--muted);line-height:1.35}}
body.cover .swipe{{margin-top:64px;font-size:30px;font-weight:700;color:var(--blue)}}
body.cover .foot{{border-color:#d2e3fc}}
/* point */
.num{{width:132px;height:132px;border-radius:36px;background:var(--blue);color:#fff;display:grid;place-items:center;
font-family:Bricolage,sans-serif;font-weight:700;font-size:72px}}
body.point h2{{font-size:84px;margin:56px 0 40px}}
body.point p{{font-size:44px;line-height:1.42;color:var(--muted);max-width:860px}}
/* note */
.notecard{{background:var(--apale);border-radius:40px;padding:72px 64px}}
.notecard .ico{{width:96px;height:96px;border-radius:50%;background:var(--amber);color:#fff;font:700 60px Bricolage,sans-serif;
display:grid;place-items:center;margin-bottom:44px}}
.notecard h2{{font-size:68px;margin-bottom:32px}}
.notecard p{{font-size:40px;line-height:1.42;color:#5c3d00}}
/* cta */
body.cta{{background:var(--blue);color:#fff}}
body.cta h2{{font-size:84px}}
body.cta .action{{display:inline-block;margin-top:64px;background:#fff;color:var(--blue);font-weight:700;font-size:38px;
padding:28px 48px;border-radius:999px;align-self:flex-start}}
body.cta .foot{{border-color:rgba(255,255,255,.3)}}
body.cta .foot span{{color:#dbe7ff}}
body.cta .foot svg path,body.cta .foot svg g{{fill:#fff}}
body.cta .foot svg text{{fill:#fff}}
/* myth */
.panel{{border-radius:40px;padding:56px 60px}}
.panel .lab{{display:flex;align-items:center;gap:20px;font-weight:700;font-size:28px;letter-spacing:.1em;text-transform:uppercase;margin-bottom:28px}}
.panel .lab i{{width:56px;height:56px;border-radius:50%;display:grid;place-items:center;color:#fff;font-style:normal;font-size:32px}}
.panel.m{{background:var(--rpale)}} .panel.m .lab{{color:var(--red)}} .panel.m .lab i{{background:var(--red)}}
.panel.m .big{{font-size:66px;color:#410e0b}}
.panel.r{{background:var(--gpale);margin-top:36px}} .panel.r .lab{{color:var(--green)}} .panel.r .lab i{{background:var(--green)}}
.panel.r p{{font-size:42px;line-height:1.4;color:#0d3b1e}}
/* checklist */
.over{{color:var(--blue);font-weight:700;font-size:28px;letter-spacing:.1em;text-transform:uppercase}}
body.checklist h2,body.message h2,body.serp h2,body.grid h2{{font-size:64px;margin:24px 0 44px}}
.main{{padding:32px 0}}
.items{{list-style:none;display:flex;flex-direction:column;gap:22px}}
.items li{{display:flex;gap:32px;align-items:center;border:2px solid var(--line);border-radius:32px;padding:30px 36px;font-size:40px;line-height:1.3;font-weight:600}}
.items li b{{flex:0 0 84px;height:84px;border-radius:50%;background:var(--pale);color:var(--blue);display:grid;place-items:center;
font:700 44px Bricolage,sans-serif}}
.footnote{{margin-top:36px;font-size:32px;line-height:1.42;color:var(--muted)}}
/* message */
.bubble{{background:var(--gpale);border-radius:40px 40px 40px 8px;padding:48px 52px;font-size:40px;line-height:1.45;color:#0d3b1e}}
.bubble em{{font-style:normal;color:var(--green);font-weight:700}}
.tips{{margin-top:48px;display:flex;flex-direction:column;gap:20px}}
.tips div{{font-size:36px;display:flex;gap:20px;align-items:center}}
.tips div:before{{content:"✓";color:#fff;background:var(--blue);width:52px;height:52px;flex:0 0 52px;border-radius:50%;display:grid;place-items:center;font-size:28px;font-weight:700}}
/* serp */
.res{{border:2px solid var(--line);border-radius:32px;padding:30px 40px;background:#fff}}
.res+.res{{margin-top:24px}}
.tag{{display:inline-block;font-weight:700;font-size:24px;letter-spacing:.1em;text-transform:uppercase;padding:10px 20px;border-radius:999px;margin-bottom:20px}}
.res.b .tag{{background:var(--rpale);color:var(--red)}} .res.a .tag{{background:var(--gpale);color:var(--green)}}
.res small{{display:block;font-size:30px;color:var(--green);margin-bottom:12px}}
.res strong{{display:block;font-size:46px;color:#1a0dab;font-weight:500;line-height:1.25}}
.res.b{{opacity:.85}}
/* grid */
.tiles{{display:grid;grid-template-columns:1fr 1fr;gap:18px}}
.tiles div{{border:2px solid var(--line);border-radius:28px;padding:22px 30px}}
.tiles b{{display:block;font-size:34px;margin-bottom:4px}}
.tiles span{{font-size:30px;color:var(--muted)}}
.tiles div:last-child{{grid-column:1/-1;background:var(--pale)}}
.pill{{display:inline-block;align-self:flex-start;margin-top:32px;background:var(--blue);color:#fff;font-weight:700;font-size:36px;padding:24px 44px;border-radius:999px}}
"""


def chip(pillar):
    bg, fg = PILLARS.get(pillar, ("#e8f0fe", "#0b57d0"))
    return f'<span class="chip" style="background:{bg};color:{fg}">{fr(pillar)}</span>'


def foot(i, n):
    page = f"{i}/{n}" if n > 1 else "arweb.ma"
    return f'<div class="foot"><div class="logo">{LOGO}</div><span>{page}</span></div>'


def slide_html(s, post, i, n):
    t = s["t"]
    if t == "cover":
        body = (f'<div class="bgmark">{MARK}</div><div class="top">{chip(post["pillar"])}</div>'
                f'<div class="main"><h1>{fr(s["title"])}</h1><div class="sub">{fr(s["sub"])}</div>'
                f'<div class="swipe">Faites défiler →</div></div>')
    elif t == "point":
        body = (f'<div class="top">{chip(post["pillar"])}</div><div class="main"><div class="num">{s["n"]}</div>'
                f'<h2>{fr(s["title"])}</h2><p>{fr(s["body"])}</p></div>')
    elif t == "note":
        body = (f'<div class="top">{chip(post["pillar"])}</div><div class="main"><div class="notecard"><div class="ico">!</div>'
                f'<h2>{fr(s["title"])}</h2><p>{fr(s["body"])}</p></div></div>')
    elif t == "cta":
        body = f'<div class="main"><h2>{fr(s["title"])}</h2><div class="action">{fr(s["action"])}</div></div>'
    elif t == "myth":
        body = (f'<div class="top">{chip(post["pillar"])}</div><div class="main">'
                f'<div class="panel m"><div class="lab"><i>✕</i>Idée reçue</div><div class="big">{fr(s["myth"])}</div></div>'
                f'<div class="panel r"><div class="lab"><i>✓</i>En réalité</div><p>{fr(s["reality"])}</p></div></div>')
    elif t == "checklist":
        items = "".join(f"<li><b>{k}</b><span>{fr(x)}</span></li>" for k, x in enumerate(s["items"], 1))
        body = (f'<div class="top">{chip(post["pillar"])}</div><div class="main"><div class="over">{fr(s["over"])}</div>'
                f'<h2>{fr(s["title"])}</h2><ul class="items">{items}</ul><p class="footnote">{fr(s["foot"])}</p></div>')
    elif t == "message":
        msg = re.sub(r"\[([^\]]+)\]", r"<em>[\1]</em>", fr(s["msg"]))
        tips = "".join(f"<div>{fr(x)}</div>" for x in s["tips"])
        body = (f'<div class="top">{chip(post["pillar"])}</div><div class="main"><div class="over">{fr(s["over"])}</div>'
                f'<h2>{fr(s["title"])}</h2><div class="bubble">{msg}</div><div class="tips">{tips}</div></div>')
    elif t == "serp":
        b, a = s["before"], s["after"]
        body = (f'<div class="top">{chip(post["pillar"])}</div><div class="main"><div class="over">{fr(s["over"])}</div>'
                f'<h2>{fr(s["title"])}</h2>'
                f'<div class="res b"><span class="tag">Avant</span><small>{fr(b["url"])}</small><strong>{fr(b["title"])}</strong></div>'
                f'<div class="res a"><span class="tag">Après</span><small>{fr(a["url"])}</small><strong>{fr(a["title"])}</strong></div>'
                f'<p class="footnote">{fr(s["foot"])}</p></div>')
    elif t == "grid":
        tiles = "".join(f"<div><b>{fr(k)}</b><span>{fr(v)}</span></div>" for k, v in s["items"])
        body = (f'<div class="top">{chip(post["pillar"])}</div><div class="main"><div class="over">{fr(s["over"])}</div>'
                f'<h2>{fr(s["title"])}</h2><div class="tiles">{tiles}</div><div class="pill">{fr(s["foot"])}</div></div>')
    else:
        raise ValueError(f"unknown slide type {t}")
    return f'<!doctype html><html lang="fr"><head><meta charset="utf-8"><style>{CSS}</style></head><body class="{t}">{body}{foot(i, n)}</body></html>'


def main():
    data = json.loads(Path(sys.argv[1]).read_text())
    only = set(sys.argv[2:])
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path="/usr/bin/google-chrome")
        page = browser.new_page(viewport={"width": 1080, "height": 1350})
        for post in data["posts"]:
            if only and post["id"] not in only:
                continue
            out = ROOT / post["date"][:7] / f'{post["id"]}-{post["slug"]}'
            out.mkdir(parents=True, exist_ok=True)
            n = len(post["slides"])
            for i, s in enumerate(post["slides"], 1):
                page.set_content(slide_html(s, post, i, n), wait_until="load")
                page.evaluate("document.fonts.ready")
                overflow = page.evaluate("document.body.scrollHeight > 1350 || document.querySelector('.main') && document.querySelector('.main').scrollHeight > document.querySelector('.main').clientHeight + 2")
                if overflow:
                    print(f"WARNING overflow: post {post['id']} slide {i}")
                page.screenshot(path=str(out / f"{i}.png"))
            print(f"rendered {post['id']} ({n} slides) -> {out.relative_to(ROOT)}")
        browser.close()


if __name__ == "__main__":
    main()
