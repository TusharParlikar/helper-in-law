"""Hand-drawn SVG law artwork (scales, gavel, column, book), so the UI ships no third-party images."""

import base64

GOLD = "#E8B94A"

SCALES = """
<g fill="none" stroke-linecap="round" stroke-linejoin="round">
  <path d="M60 8 v84 M38 96 h44 M30 102 h60"/>
  <path d="M14 26 h92 M60 26 m-5 0 a5 5 0 1 0 10 0 a5 5 0 1 0 -10 0"/>
  <path d="M20 26 l-14 34 h28 z M100 26 l-14 34 h28 z"/>
  <path d="M6 60 a14 8 0 0 0 28 0 M86 60 a14 8 0 0 0 28 0"/>
</g>"""

GAVEL = """
<g fill="none" stroke-linecap="round" stroke-linejoin="round">
  <g transform="rotate(-35 50 40)">
    <rect x="22" y="22" width="56" height="22" rx="5"/>
    <path d="M30 22 v22 M70 22 v22"/>
    <path d="M50 44 v52"/>
  </g>
  <rect x="58" y="88" width="46" height="12" rx="4"/>
</g>"""

COLUMN = """
<g fill="none" stroke-linecap="round" stroke-linejoin="round">
  <path d="M10 14 h60 l-6 10 h-48 z"/>
  <path d="M20 24 v62 M32 24 v62 M48 24 v62 M60 24 v62"/>
  <path d="M14 86 h52 M8 96 h64"/>
</g>"""

BOOK = """
<g fill="none" stroke-linecap="round" stroke-linejoin="round">
  <path d="M50 20 c-14 -8 -30 -8 -44 -2 v62 c14 -6 30 -6 44 2 c14 -8 30 -8 44 -2 v-62 c-14 -6 -30 -6 -44 2 z"/>
  <path d="M50 20 v62 M16 34 h24 M16 46 h24 M60 34 h24 M60 46 h24"/>
</g>"""


def _uri(svg: str) -> str:
    return "data:image/svg+xml;base64," + base64.b64encode(svg.encode()).decode()


def pattern(opacity: float = 0.07) -> str:
    """A 420px tile of the four marks, faint gold on transparent."""
    svg = f"""<svg xmlns='http://www.w3.org/2000/svg' width='420' height='420' viewBox='0 0 420 420'>
<g stroke='{GOLD}' stroke-width='2' opacity='{opacity}'>
  <g transform='translate(40 40)'>{SCALES}</g>
  <g transform='translate(270 60)'>{GAVEL}</g>
  <g transform='translate(70 270)'>{BOOK}</g>
  <g transform='translate(290 280)'>{COLUMN}</g>
</g></svg>"""
    return _uri(svg)


def hero_scales() -> str:
    """Large scales of justice for the header, with a gold gradient stroke."""
    svg = f"""<svg xmlns='http://www.w3.org/2000/svg' width='240' height='220' viewBox='0 0 120 110'>
<defs><linearGradient id='g' x1='0' y1='0' x2='1' y2='1'>
<stop offset='0' stop-color='#FFD27A'/><stop offset='1' stop-color='#E07A3F'/></linearGradient></defs>
<g stroke='url(#g)' stroke-width='2.2'>{SCALES}</g></svg>"""
    return _uri(svg)
