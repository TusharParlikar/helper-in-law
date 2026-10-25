"""Hand-drawn SVG artwork (no third-party images): a scales-of-justice mark and a faint
court-columns line drawing for the header."""

import base64

NAVY = "#1F3A5F"
GOLD = "#B08D57"


def _uri(svg: str) -> str:
    return "data:image/svg+xml;base64," + base64.b64encode(svg.encode()).decode()


def mark(color: str = NAVY) -> str:
    """Scales of justice, for the wordmark."""
    return _uri(f"""<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 120 110' width='40' height='36'>
<g fill='none' stroke='{color}' stroke-width='5' stroke-linecap='round' stroke-linejoin='round'>
<path d='M60 10 v82 M36 98 h48'/><path d='M14 28 h92'/>
<path d='M22 28 l-14 32 h28 z M98 28 l-14 32 h28 z'/></g>
<circle cx='60' cy='28' r='6' fill='{GOLD}'/></svg>""")


def colonnade() -> str:
    """A courthouse facade in hairlines, placed faintly behind the header."""
    cols = "".join(
        f"<rect x='{70 + i * 70}' y='120' width='26' height='190' rx='3'/>"
        f"<path d='M{66 + i * 70} 120 h34 M{66 + i * 70} 310 h34'/>"
        for i in range(8)
    )
    return _uri(f"""<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 700 360' width='700' height='360'>
<g fill='none' stroke='{NAVY}' stroke-width='2' opacity='0.09'>
<path d='M40 110 L350 20 L660 110 Z'/><path d='M40 110 h620 M30 320 h640 M20 340 h660'/>{cols}
<circle cx='350' cy='75' r='18'/></g></svg>""")
