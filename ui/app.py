"""Streamlit UI: uv run streamlit run ui/app.py  (needs the "ui" extra).

Judgment links open the API's reader pages, so keep `python -m helperinlaw.api` running too."""

from datetime import datetime
from html import escape

import streamlit as st
from art import colonnade, mark

from helperinlaw.core.config import Settings
from helperinlaw.core.types import Citation, Filters, Response
from helperinlaw.report import build_report, has_proof
from helperinlaw.service import Service

st.set_page_config(
    page_title="Helper in Law", page_icon="⚖", layout="wide", initial_sidebar_state="collapsed"
)

st.markdown(
    f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&family=Source+Serif+4:opsz,wght@8..60,500;8..60,600&display=swap');
:root {{ --navy:#1F3A5F; --ink:#1C1F23; --muted:#5F6B7A; --line:#E3E6EA; --soft:#F7F8FA; --gold:#B08D57; }}
html, body, .stApp, [class*="css"] {{ font-family: Inter, system-ui, sans-serif; color: var(--ink); }}
.stApp {{ background: #FFFFFF; }}
header[data-testid="stHeader"] {{ background: transparent; }}
.block-container {{ max-width: 1120px; padding-top: 1.2rem; }}
h1, h2, h3, .serif {{ font-family: 'Source Serif 4', Georgia, serif !important; letter-spacing: -.01em; }}
.topbar {{ display:flex; align-items:center; justify-content:space-between; padding: 6px 0 18px;
  border-bottom: 1px solid var(--line); margin-bottom: 28px; }}
.brand {{ display:flex; align-items:center; gap:12px; font-family:'Source Serif 4',Georgia,serif;
  font-size: 1.45rem; font-weight:600; color: var(--navy); }}
.status {{ color: var(--muted); font-size: .85rem; }}
.status b {{ color: var(--ink); font-weight: 600; }}
.hero {{ padding: 26px 0 8px; background: url("{colonnade()}") no-repeat right -40px top -30px / 560px auto; }}
.hero h1 {{ font-size: 2.6rem; line-height: 1.12; margin: 0 0 12px; color: var(--ink); max-width: 720px; }}
.hero p {{ color: var(--muted); font-size: 1.08rem; max-width: 640px; margin: 0 0 6px; }}
div[data-testid="stForm"] {{ border: 1px solid var(--line); border-radius: 18px; padding: 18px 20px 6px;
  background: #fff; box-shadow: 0 10px 30px rgba(16,24,40,.06); }}
div[data-testid="stTextArea"] textarea {{ border-radius: 14px !important; font-size: 1.02rem !important;
  line-height: 1.55 !important; padding: 14px 16px !important; background: var(--soft) !important;
  border: 1px solid var(--line) !important; }}
div[data-testid="stTextArea"] textarea:focus {{ border-color: var(--navy) !important;
  box-shadow: 0 0 0 3px rgba(31,58,95,.12) !important; }}
div[data-testid="stFormSubmitButton"] button {{ border-radius: 999px !important; height: 46px;
  padding: 0 28px !important; font-weight: 600; background: var(--navy) !important; color: #fff !important;
  border: none !important; }}
div[data-testid="stFormSubmitButton"] button:hover {{ background: #173052 !important; }}
.stButton button, div[data-testid="stPopover"] button {{ border-radius: 999px !important; }}
div[data-testid="stDownloadButton"] button {{ border-radius: 999px !important; background: var(--navy) !important;
  border: none !important; color: #fff !important; font-weight: 600; margin-top: 10px; }}
div[data-testid="stDownloadButton"] button:hover {{ background: #173052 !important; }}
.label {{ text-transform: uppercase; letter-spacing: .08em; font-size: .72rem; font-weight: 600;
  color: var(--muted); margin: 26px 0 10px; }}
.summary {{ display:flex; flex-wrap:wrap; gap:10px; align-items:center; padding: 14px 18px;
  border: 1px solid var(--line); border-radius: 14px; background: var(--soft); margin: 18px 0 4px; }}
.pill {{ display:inline-block; padding: 3px 12px; border-radius: 999px; font-size: .8rem; font-weight: 600; }}
.p-high {{ background:#E6F4EA; color:#1E7B3A; }} .p-medium {{ background:#FFF4D6; color:#8A5A00; }}
.p-low {{ background:#FDE7E2; color:#A33A1F; }} .p-not_found {{ background:#ECEEF1; color:#4A5361; }}
.p-neutral {{ background:#ECEEF1; color:#4A5361; }} .p-bad {{ background:#FDE7E2; color:#A33A1F; }}
.sumtext {{ color: var(--muted); font-size: .9rem; }}
.card {{ border: 1px solid var(--line); border-radius: 14px; padding: 18px 20px; margin: 10px 0;
  background: #fff; transition: box-shadow .15s, border-color .15s; }}
.card:hover {{ border-color: #C9CFD6; box-shadow: 0 6px 18px rgba(16,24,40,.06); }}
.prov {{ border-left: 4px solid var(--gold); }}
.prov h4, .case h4 {{ font-family:'Source Serif 4',Georgia,serif; font-size: 1.12rem; margin: 0 0 4px; color: var(--ink); }}
.meta {{ color: var(--muted); font-size: .84rem; }}
blockquote {{ margin: 12px 0 10px; padding: 2px 0 2px 14px; border-left: 2px solid var(--line);
  color: #2B3138; font-family:'Source Serif 4',Georgia,serif; font-size: 1.02rem; line-height: 1.6; }}
.links a {{ display:inline-block; margin: 2px 16px 0 0; font-size: .86rem; font-weight: 500;
  color: var(--navy) !important; text-decoration: none !important; border-bottom: 1px solid rgba(31,58,95,.25); }}
.links a:hover {{ border-color: var(--navy); }}
.point {{ display:flex; gap:12px; padding: 12px 0; border-bottom: 1px solid var(--line); line-height: 1.6; }}
.point:last-child {{ border-bottom: none; }}
.num {{ color: var(--gold); font-weight: 600; min-width: 22px; }}
sup a {{ color: var(--navy) !important; text-decoration: none !important; font-weight: 600; font-size: .72rem;
  padding: 0 3px; }}
.empty {{ text-align:center; padding: 40px 20px; color: var(--muted); }}
.emptyhead {{ font-family:'Source Serif 4',Georgia,serif; font-size: 1.4rem; font-weight: 600; color: var(--ink);
  margin-bottom: 8px; }}
.foot {{ color: var(--muted); font-size: .8rem; border-top: 1px solid var(--line); margin-top: 36px; padding-top: 14px; }}
.card, blockquote, .point, h4 {{ overflow-wrap: anywhere; }}
/* phones and small tablets */
@media (max-width: 640px) {{
  .block-container {{ padding: .6rem .9rem 2rem !important; }}
  .brand {{ font-size: 1.2rem; }} .brand img {{ height: 28px; }}
  .status, .kbd {{ display: none; }}
  .hero {{ padding: 10px 0 4px; background: none; }}
  .hero h1 {{ font-size: 1.65rem; }}
  .hero h1[style] {{ font-size: 1.45rem !important; }}
  .hero p {{ font-size: .97rem; }}
  div[data-testid="stForm"] {{ padding: 12px 12px 4px; border-radius: 14px; box-shadow: none; }}
  div[data-testid="stTextArea"] textarea, div[data-testid="stTextInput"] input {{ font-size: 16px !important; }}
  div[data-testid="stFormSubmitButton"] button, div[data-testid="stDownloadButton"] button {{ width: 100%; height: 48px; }}
  .card {{ padding: 14px 14px; border-radius: 12px; }}
  .card:hover {{ box-shadow: none; }}
  .prov h4, .case h4 {{ font-size: 1.02rem; }}
  blockquote {{ font-size: .96rem; padding-left: 10px; }}
  .point {{ gap: 8px; font-size: .96rem; }}
  .summary {{ padding: 10px 12px; }}
  .links a {{ display: inline-block; padding: 6px 0; margin-right: 14px; }}
  sup a {{ padding: 4px 4px; }}
  .label {{ margin: 20px 0 8px; }}
  .empty {{ padding: 24px 14px; }} .emptyhead {{ font-size: 1.15rem; }}
}}
</style>
""",
    unsafe_allow_html=True,
)


@st.cache_resource
def service(use_llm: bool) -> Service:
    return Service(cfg=Settings(use_llm=use_llm))


SCENARIOS = {
    "Arrest without grounds": "My client was arrested at night by the police and kept in custody for two days. "
    "He was not told why he was arrested and was not allowed to call a lawyer.",
    "Elderly parent's dignity": "My client is an 80-year-old widow with no income, abandoned by her children. "
    "The State has no old age home or pension scheme in her district. Can she claim a right to live with dignity?",
    "Unequal treatment in a scheme": "A state scheme gives benefits to one group of employees but excludes another "
    "group doing identical work, with no reason given. My client wants to challenge it.",
    "Temple entry ban": "Women of a certain age group are barred by custom from entering a public temple. "
    "My client wants to challenge the ban as unconstitutional.",
    "Speech restriction": "My client posted criticism of a government policy online and the authorities "
    "ordered the post removed and threatened action. Is her freedom of speech protected?",
}

ss = st.session_state
ss.setdefault("q", "")

top_l, top_r = st.columns([3, 2], vertical_alignment="center")
with top_r:
    s1, s2 = st.columns([5, 2], vertical_alignment="center")
    with s2.popover("Settings", use_container_width=True):
        use_llm = st.toggle(
            "AI drafting (Ollama)",
            value=False,
            help="Off: verbatim passages, instant. On: the local model drafts the analysis; "
            "every statement is still checked against the source before it is shown.",
        )
        detail = st.segmented_control(
            "Detail",
            ["quick", "standard", "deep"],
            default="standard",
            format_func={"quick": "Brief", "standard": "Standard", "deep": "Detailed"}.get,
        )
        layout = st.segmented_control(
            "Format",
            ["bullets", "irac", "memo"],
            default="bullets",
            format_func={"bullets": "Points", "irac": "IRAC", "memo": "Memo"}.get,
        )
        tone = st.segmented_control(
            "Language",
            ["technical", "plain"],
            default="technical",
            format_func={"technical": "Legal", "plain": "Plain"}.get,
        )
        years = st.slider("Judgments from", 1950, 2025, (1950, 2025))
svc = service(use_llm)
cov = svc.coverage()
with top_l:
    st.markdown(
        f"<div class='brand'><img src='{mark()}' height='34'>Helper in Law</div>",
        unsafe_allow_html=True,
    )
s1.markdown(
    f"<div class='status' style='text-align:right'><b>Indexed</b> · {escape(cov.corpus)}</div>",
    unsafe_allow_html=True,
)
st.markdown(
    "<div style='border-bottom:1px solid var(--line);margin:4px 0 8px'></div>",
    unsafe_allow_html=True,
)

research, lookup = st.tabs(["Research", "Constitution lookup"])


def link(label: str, url: str) -> str:
    return f"<a href='{escape(url)}' target='_blank' rel='noopener'>{escape(label)}</a>"


def quotes(cs: list[Citation], refs: dict[str, int]) -> str:
    return "".join(
        f"<blockquote><span class='meta'>[{refs[c.id]}]{' ¶ ' + c.para if c.kind == 'judgment' else ''}"
        f"</span> {escape(c.quote)}</blockquote>"
        for c in cs
    )


def provision_card(cs: list[Citation], refs: dict[str, int]) -> str:
    c = cs[0]
    art = c.citation.removeprefix("Art. ")
    return (
        f"<div class='card prov'><h4>{escape(c.case_title)}</h4>"
        f"<div class='meta'>{escape(c.neutral_citation)}</div>{quotes(cs, refs)}"
        f"<div class='links'>{link('Official text, exact page ↗', c.url)}"
        f"{link('Judgments applying it ↗', f'{svc.cfg.public_url}/statutes/CONST/{art}/view')}</div>"
        f"<div class='meta' style='margin-top:8px'>Source: {escape(c.source)}</div></div>"
    )


def judgment_card(cs: list[Citation], refs: dict[str, int]) -> str:
    c = cs[0]
    pdf = svc.store.get_case(c.case_id)
    flag = "<span class='pill p-bad'>Overruled</span> " if c.treatment == "overruled" else ""
    arts = ", ".join(x.replace("CONST ", "Art. ") for x in c.statutes if x.startswith("CONST"))[:80]
    return (
        f"<div class='card case'>{flag}<h4>{escape(c.case_title)}</h4>"
        f"<div class='meta'>{escape(c.court)} · {escape(c.date)} · {escape(c.citation)}"
        f"{' · ' + escape(c.neutral_citation) if c.neutral_citation else ''}</div>{quotes(cs, refs)}"
        f"<div class='links'>{link(f'Read judgment at ¶ {c.para} ↗', c.url)}"
        f"{link('Original PDF ↗', pdf.url) if pdf and pdf.url else ''}</div>"
        f"<div class='meta' style='margin-top:8px'>{'Applies ' + escape(arts) + ' · ' if arts else ''}"
        f"Source: {escape(c.source)}</div></div>"
    )


def by_case(cs: list[Citation]) -> list[list[Citation]]:
    """One card per document, holding every passage quoted from it."""
    grouped: dict[str, list[Citation]] = {}
    for c in cs:
        grouped.setdefault(c.case_id, []).append(c)
    return list(grouped.values())


def render(r: Response) -> None:
    v = r.verification
    conf = {
        "high": "High confidence",
        "medium": "Moderate confidence",
        "low": "Review carefully",
        "not_found": "No support found",
    }[r.confidence]
    mode = {
        "synthesised": "AI-drafted, then verified",
        "extractive": "Verbatim from sources",
        "abstained": "No answer given",
    }[v.mode]
    st.markdown(
        f"<div class='summary'><span class='pill p-{r.confidence}'>{conf}</span>"
        f"<span class='sumtext'>{v.verified} of {v.claims_proposed} statements verified against the source text"
        f" · {mode}</span></div>",
        unsafe_allow_html=True,
    )
    if has_proof(r):  # a report only when there is verified proof to put in it
        st.download_button(
            "Download research report (PDF)",
            data=build_report(r, ss.q, svc.store),
            file_name=f"helper-in-law-report-{datetime.now():%Y%m%d-%H%M}.pdf",
            mime="application/pdf",
            type="primary",
            icon=":material/description:",
        )
    for n in r.notices:
        if r.confidence == "not_found" and n.startswith("Not found in the indexed"):
            continue  # the card below says it
        (st.warning if "overruled" in n.lower() or "conflict" in n.lower() else st.info)(n)
    if r.confidence == "not_found":
        st.markdown(
            "<div class='card empty'><div class='emptyhead'>Nothing in the indexed sources supports an answer</div>"
            "Helper in Law does not guess. Try describing the facts differently, or widen the year range."
            "</div>",
            unsafe_allow_html=True,
        )
        return
    cites = {c.id: c for c in r.citations}
    provisions = [c for c in r.citations if c.kind == "provision"]
    judgments = [c for c in r.citations if c.kind == "judgment"]
    order = {c.id: i + 1 for i, c in enumerate(provisions + judgments)}
    if provisions:
        st.markdown("<div class='label'>Constitutional provisions</div>", unsafe_allow_html=True)
        groups = by_case(provisions)
        cols = st.columns(min(2, len(groups)))
        for i, g in enumerate(groups):
            cols[i % len(cols)].markdown(provision_card(g, order), unsafe_allow_html=True)
    st.markdown("<div class='label'>Analysis</div>", unsafe_allow_html=True)
    points = "".join(
        f"<div class='point'><span class='num'>{i + 1}</span><div>{escape(b.text.removeprefix('- '))}"
        + "".join(f"<sup>{link(f'[{order[x]}]', cites[x].url)}</sup>" for x in b.citation_ids)
        + "</div></div>"
        for i, b in enumerate(r.answer_blocks)
    )
    st.markdown(f"<div class='card'>{points}</div>", unsafe_allow_html=True)
    if judgments:
        st.markdown("<div class='label'>Supporting judgments</div>", unsafe_allow_html=True)
        for g in by_case(judgments):
            st.markdown(judgment_card(g, order), unsafe_allow_html=True)
    fb_l, _ = st.columns([1, 3])
    with fb_l:
        fb = st.feedback("thumbs", key=f"fb-{hash(ss.q)}")
        if fb is not None and not ss.get(f"sent-{hash(ss.q)}"):
            svc.feedback(r.answer_id or 0, 1 if fb == 1 else -1, "" if fb == 1 else "unhelpful")
            ss[f"sent-{hash(ss.q)}"] = True
            st.toast("Feedback recorded")
    st.markdown(
        f"<div class='foot'>{escape(' '.join(r.coverage.limits))} Indexed: {escape(r.coverage.corpus)}. "
        f"{escape(r.disclaimer)}</div>",
        unsafe_allow_html=True,
    )


with research:
    st.markdown(
        "<div class='hero'><h1>Constitutional research, grounded in precedent.</h1>"
        "<p>Describe your client's situation. Helper in Law finds the governing provisions of the "
        "Constitution and the Supreme Court judgments that apply them. Every statement is checked "
        "against the official text before it is shown.</p></div>",
        unsafe_allow_html=True,
    )
    with st.form("ask", border=True):
        typed = st.text_area(
            "Situation",
            value=ss.q,
            height=120,
            label_visibility="collapsed",
            placeholder="e.g. My client was detained by the police for two days without being "
            "told the reason for his arrest…",
        )
        f1, f2 = st.columns([5, 1], vertical_alignment="center")
        f1.markdown(
            "<div class='meta'><span class='kbd'>Press Ctrl + Enter or click Analyse. </span>"
            "Facts stay on this machine.</div>",
            unsafe_allow_html=True,
        )
        if f2.form_submit_button("Analyse", use_container_width=True):
            ss.q = typed.strip()
    pick = st.pills("Example situations", list(SCENARIOS), key="pick")
    if pick and pick != ss.get("last_pick"):
        ss.last_pick = pick
        ss.q = SCENARIOS[pick]
        st.rerun()
    if ss.q:
        style = {
            "depth": detail or "standard",
            "structure": layout or "bullets",
            "tone": tone or "technical",
        }
        filters = Filters(
            year_from=years[0] if years[0] > 1950 else None,
            year_to=years[1] if years[1] < 2025 else None,
        )
        with st.spinner("Reading the Constitution and the judgments…"):
            resp = svc.ask(ss.q, filters, style)
        render(resp)

with lookup:
    st.markdown(
        "<div class='hero'><h1 style='font-size:2rem'>Look up an Article</h1><p>Official text from the "
        "Government of India's publication of the Constitution, with the exact page and the judgments "
        "that apply it.</p></div>",
        unsafe_allow_html=True,
    )
    with st.form("lookup", border=True):
        l1, l2 = st.columns([5, 1], vertical_alignment="bottom")
        number = l1.text_input("Article", placeholder="Article number, e.g. 21, 21A, 300A")
        go = l2.form_submit_button("Look up", use_container_width=True)
    quick = st.pills(
        "Frequently cited",
        ["14", "15", "19", "21", "21A", "22", "32", "226", "300A"],
        key="artpick",
    )
    art = number.strip() if go and number.strip() else quick
    if art:
        try:
            with st.spinner("Fetching the official text…"):
                a = svc.get_article(art)
        except KeyError:
            st.error(
                f"Article {art} was not found in the official text. It may have been omitted or repealed."
            )
        except OSError as e:
            st.error(f"Could not reach the official source: {e}")
        else:
            st.markdown(
                f"<div class='card prov'><h4>Article {escape(a['article'])}. {escape(a['title'])}</h4>"
                f"<blockquote>{escape(a['text'])}</blockquote><div class='links'>"
                f"{link('Official text, exact page ↗', a['official_url'])}</div>"
                f"<div class='meta' style='margin-top:8px'>Source: {escape(a['source'])}</div></div>",
                unsafe_allow_html=True,
            )
            st.markdown(
                f"<div class='label'>Indexed judgments applying Article {escape(a['article'])}</div>",
                unsafe_allow_html=True,
            )
            if not a["judgments"]:
                st.caption("None of the indexed judgments applies this Article yet.")
            for c in a["judgments"]:
                pdf = svc.store.get_case(c["case_id"])
                st.markdown(
                    f"<div class='card case'><h4>{escape(c['title'])}</h4><div class='meta'>{escape(c['citation'])}"
                    f" · {escape(c['date'])}</div><div class='links' style='margin-top:6px'>"
                    f"{link('Read judgment ↗', c['url'])}{link('Original PDF ↗', pdf.url) if pdf and pdf.url else ''}"
                    f"</div></div>",
                    unsafe_allow_html=True,
                )
