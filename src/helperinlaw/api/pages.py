"""Readable HTML pages behind citation links: a full judgment (anchored per paragraph, the
cited one highlighted) and a statute page. Data comes from service.py; this only formats it."""

import re
from html import escape
from typing import Any

from helperinlaw.parse.statutes import _NAME_TO_ACT, ARTICLE, SECTION

STYLE = """
:root { --ink:#1d1d1f; --muted:#6e6e73; --line:#e5e5ea; --gold:#b7791f; --bg:#fbfbfd; }
* { box-sizing:border-box; }
body { margin:0; font:17px/1.65 -apple-system, "Segoe UI", system-ui, sans-serif; color:var(--ink);
       background:var(--bg); }
header { background:#0b1020; color:#fff; padding:40px 24px 32px; }
header .wrap, main { max-width:860px; margin:0 auto; }
h1 { font-size:34px; line-height:1.2; margin:0 0 8px; letter-spacing:-.01em; }
.meta { color:#c7c7cc; font-size:15px; }
.chips { margin-top:14px; display:flex; flex-wrap:wrap; gap:8px; }
.chip { display:inline-block; padding:4px 12px; border-radius:999px; font-size:13px;
        background:rgba(255,255,255,.12); color:#fff; text-decoration:none; }
main .chip { background:#f2f2f7; color:var(--ink); }
.chip.bad { background:#ff3b30; color:#fff; }
main { padding:28px 24px 80px; }
.para { display:flex; gap:16px; padding:14px 16px; border-radius:14px; margin:4px 0;
        scroll-margin-top:24px; transition:background .3s; }
.para:target { background:#fff4d6; box-shadow:inset 3px 0 0 var(--gold); }
.n { color:var(--muted); font-variant-numeric:tabular-nums; min-width:28px; }
.n a { color:inherit; text-decoration:none; }
.tag { font-size:11px; text-transform:uppercase; letter-spacing:.06em; color:var(--muted); }
a.law { color:var(--gold); text-decoration:none; border-bottom:1px dotted var(--gold); }
.card { background:#fff; border:1px solid var(--line); border-radius:16px; padding:18px 20px;
        margin:12px 0; }
.card a { color:var(--ink); font-weight:600; text-decoration:none; }
.note { color:var(--muted); font-size:14px; }
.fiction { background:#fff4d6; color:#7a4b00; border-radius:12px; padding:10px 14px; font-size:14px;
           margin-bottom:20px; }
"""


def page(title: str, header: str, body: str) -> str:
    return (
        f"<!doctype html><html lang='en'><head><meta charset='utf-8'>"
        f"<meta name='viewport' content='width=device-width,initial-scale=1'>"
        f"<title>{escape(title)}</title><style>{STYLE}</style></head><body>"
        f"<header><div class='wrap'>{header}</div></header><main>{body}</main></body></html>"
    )


def link_laws(text: str, base: str) -> str:
    """Escape paragraph text and turn statute references into links to their statute page."""
    out = escape(text)

    def section(m: re.Match[str]) -> str:
        act = _NAME_TO_ACT.get(m.group("act").lower(), "")
        return f"<a class='law' href='{base}/statutes/{act}/{m.group('s')}/view'>{m.group(0)}</a>"

    def article(m: re.Match[str]) -> str:
        return f"<a class='law' href='{base}/statutes/CONST/{m.group('s')}/view'>{m.group(0)}</a>"

    return ARTICLE.sub(article, SECTION.sub(section, out))


def judgment_page(
    case: dict[str, Any], paras: list[dict[str, Any]], citing: list[dict[str, Any]], base: str
) -> str:
    bad = case["treatment"] == "overruled"
    chips = "".join(
        f"<a class='chip' href='{escape(law['url'])}'>{escape(law['act'])} "
        f"{escape(law['section'])}</a>"
        for law in case["laws"]
    )
    status = f"<span class='chip{' bad' if bad else ''}'>{escape(case['treatment'])}</span>"
    header = (
        f"<h1>{escape(case['title'])}</h1><div class='meta'>{escape(case['court'])} · "
        f"{escape(case['date'])} · {escape(case['citation'])} · "
        f"{escape(case['neutral_citation'])}<br>Bench: {escape('; '.join(case['bench']))}"
        f"</div><div class='chips'>{status}{chips}</div>"
    )
    body = ""
    if case["id"].startswith("fs_"):
        body = "<div class='fiction'>Fictional sample judgment written for testing. Not a real case.</div>"
    elif case.get("url"):
        body = (
            f"<div class='card'><div class='tag'>Source</div><a href='{escape(case['url'])}' "
            "target='_blank' rel='noopener'>Original judgment PDF (Supreme Court e-SCR) ↗</a></div>"
        )
    if citing:
        body += (
            "<div class='card'><div class='tag'>Cited by</div>"
            + "".join(
                f"<div><a href='{escape(c['url'])}'>{escape(c['title'])}</a> "
                f"<span class='note'>({escape(c['treatment'])}, para {c['para']})</span></div>"
                for c in citing
            )
            + "</div>"
        )
    for p in paras:
        body += (
            f"<div class='para' id='para-{p['n']}'><div class='n'><a href='#para-{p['n']}'>"
            f"{p['n']}</a></div><div><div class='tag'>{escape(p['section'])}</div>"
            f"{link_laws(p['text'], base)}</div></div>"
        )
    return page(case["title"], header, body)


def statute_page(info: dict[str, Any]) -> str:
    law = info["law"]
    eq = "".join(f"<span class='chip'>{escape(e)}</span>" for e in info["equivalents"][1:])
    header = (
        f"<h1>{escape(law['label'])}</h1><div class='meta'>{escape(info['query'])}</div>"
        f"<div class='chips'>{eq}<a class='chip' href='{escape(law['official_url'])}' "
        f"target='_blank' rel='noopener'>"
        f"{'Official PDF ↗' if law.get('text') else 'Find official text on India Code ↗'}</a></div>"
    )
    cases = (
        "".join(
            f"<div class='card'><a href='{escape(c['url'])}'>{escape(c['title'])}</a>"
            f"<div class='note'>{escape(c['citation'])} · {escape(c['date'])} · {escape(c['treatment'])}"
            f"</div></div>"
            for c in info["cases"]
        )
        or "<p class='note'>No indexed judgment applies this provision.</p>"
    )
    official = ""
    if law.get("text"):
        official = (
            f"<div class='card'><div class='tag'>Official text</div><p>{escape(law['text'])}</p>"
            f"<div class='note'>Source: {escape(law['source'])}. <a href='{escape(law['official_url'])}' "
            "target='_blank' rel='noopener'>Open the official PDF at this article ↗</a></div></div>"
        )
    body = (
        f"{official}<div class='tag'>Judgments in the corpus applying it</div>{cases}"
        f"<p class='note'>{escape(info['note'])}</p>"
    )
    return page(law["label"], header, body)
