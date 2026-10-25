"""Streamlit UI: uv run streamlit run ui/app.py  (needs the "ui" extra).

Every link goes to the API's readable pages (judgment at the cited paragraph, statute pages),
so keep `python -m helperinlaw.api` running alongside."""

from html import escape

import streamlit as st
from art import hero_scales, pattern

from helperinlaw.core.config import Settings
from helperinlaw.core.types import Filters, Response
from helperinlaw.service import Service

st.set_page_config(page_title="Helper in Law", page_icon="⚖️", layout="wide")

st.markdown(
    f"""
<style>
.stApp {{
  background:
    radial-gradient(1200px 600px at 85% -10%, rgba(232,185,74,.16), transparent 60%),
    radial-gradient(900px 500px at -10% 110%, rgba(224,122,63,.10), transparent 60%),
    url("{pattern()}"), #0B1020;
  background-attachment: fixed;
}}
.block-container {{ padding-top: 2rem; max-width: 1200px; }}
.hero {{ display:flex; align-items:center; justify-content:space-between; gap:24px;
  padding: 28px 36px; border-radius: 28px; margin-bottom: 18px;
  background: linear-gradient(135deg, rgba(21,27,48,.92), rgba(11,16,32,.75));
  border: 1px solid rgba(232,185,74,.25); box-shadow: 0 20px 60px rgba(0,0,0,.35); }}
.hero h1 {{ font-size: 3rem; margin: 0; letter-spacing: -.02em; line-height:1.05; }}
.hero h1 span {{ background: linear-gradient(90deg,#FFD27A,#E07A3F); -webkit-background-clip:text;
  background-clip:text; color: transparent; }}
.hero p {{ color:#A1A1AA; font-size:1.1rem; margin:.5rem 0 0; }}
.hero img {{ width: 170px; filter: drop-shadow(0 8px 24px rgba(232,185,74,.35)); }}
div[data-testid="stForm"] {{ border:none; padding:0; }}
div[data-testid="stTextInput"] input {{ border-radius: 999px !important; padding: 18px 26px !important;
  font-size: 1.1rem !important; background: rgba(255,255,255,.06) !important;
  border: 1px solid rgba(232,185,74,.35) !important; }}
div[data-testid="stTextInput"] div[data-baseweb="input"] {{ border-radius: 999px !important;
  background: transparent !important; border: none !important; }}
div[data-testid="stTextInput"] input:focus {{ border-color:#E8B94A !important;
  box-shadow: 0 0 0 4px rgba(232,185,74,.18) !important; }}
.stButton button {{ border-radius: 999px !important; }}
div[data-testid="stFormSubmitButton"] button {{ height: 58px; border-radius: 999px !important;
  font-weight: 700; font-size: 1.05rem; border: none !important; color:#141414 !important;
  background: linear-gradient(90deg,#FFD27A,#E07A3F) !important;
  box-shadow: 0 8px 24px rgba(232,185,74,.25); transition: transform .15s; }}
div[data-testid="stFormSubmitButton"] button:hover {{ transform: translateY(-1px) scale(1.02); }}
.card {{ background: rgba(21,27,48,.85); border:1px solid rgba(255,255,255,.08); border-radius: 20px;
  padding: 18px 20px; margin: 10px 0; backdrop-filter: blur(6px); transition: border-color .2s; }}
.card:hover {{ border-color: rgba(232,185,74,.35); }}
.answer {{ font-size: 1.07rem; line-height: 1.65; border-left: 3px solid #E8B94A; }}
.cite {{ display:inline-block; margin-left:6px; padding:1px 9px; border-radius:999px; font-size:.8rem;
  background: rgba(232,185,74,.16); color:#FFD27A !important; text-decoration:none !important; }}
.cite:hover {{ background:#E8B94A; color:#141414 !important; }}
.src h4 {{ margin:0 0 4px; font-size:1.02rem; }}
.src h4 a {{ color:#ECECF1 !important; text-decoration:none; }}
.src h4 a:hover {{ color:#FFD27A !important; }}
.meta {{ color:#A1A1AA; font-size:.85rem; }}
blockquote.q {{ margin:10px 0; padding:8px 14px; border-left:3px solid rgba(232,185,74,.6);
  color:#D4D4D8; font-style: italic; background: rgba(255,255,255,.03); border-radius: 0 12px 12px 0; }}
.chip {{ display:inline-block; margin:6px 6px 0 0; padding:3px 11px; border-radius:999px; font-size:.8rem;
  background: rgba(255,255,255,.07); color:#ECECF1 !important; text-decoration:none !important;
  border:1px solid rgba(255,255,255,.1); }}
.chip:hover {{ border-color:#E8B94A; color:#FFD27A !important; }}
.badge {{ display:inline-block; padding:4px 12px; border-radius:999px; font-weight:600; font-size:.85rem;
  margin: 0 8px 6px 0; }}
.b-high {{ background:rgba(48,209,88,.18); color:#5BE584; }}
.b-medium {{ background:rgba(255,214,10,.16); color:#FFD60A; }}
.b-low {{ background:rgba(255,159,10,.18); color:#FFB340; }}
.b-not_found {{ background:rgba(255,255,255,.1); color:#D4D4D8; }}
.b-bad {{ background:rgba(255,69,58,.2); color:#FF6961; }}
.b-ok {{ background:rgba(232,185,74,.14); color:#FFD27A; }}
.law {{ border-left: 3px solid #E07A3F; }}
.empty {{ text-align:center; padding: 34px; }}
.empty h3 {{ margin:.2rem 0; }}
</style>
<div class="hero">
  <div><h1>Helper <span>in Law</span></h1>
  <p>Research over Indian court judgments. Every claim verified against the source, or not shown.</p></div>
  <img src="{hero_scales()}" alt="Scales of justice">
</div>
""",
    unsafe_allow_html=True,
)


@st.cache_resource
def service(use_llm: bool) -> Service:
    return Service(cfg=Settings(use_llm=use_llm))


EXAMPLES = [
    "Can bail be refused because the accused may tamper with witnesses?",
    "Is a 65B certificate mandatory for electronic evidence?",
    "What does soon before her death mean in dowry death cases?",
    "When is murder reduced to culpable homicide in a sudden fight?",
    "Can a wife capable of earning be denied maintenance under Section 125 CrPC?",
    "What does Section 103 BNS correspond to?",
    "What is the punishment for sedition under Section 124A IPC?",
]
ACT_LABEL = {"IEA": "Evidence Act (IEA)", "CONST": "Constitution"}

with st.sidebar:
    st.markdown("### ⚙️ Answer style")
    use_llm = st.toggle(
        "Use local AI (Ollama)",
        value=True,
        help="Off = instant, verbatim quotes only. On = qwen3 drafts claims; every one is verified.",
    )
    svc = service(use_llm)
    p = svc.get_profile()
    tone = st.radio(
        "Tone",
        ["technical", "plain", "new"],
        horizontal=True,
        index=["technical", "plain", "new"].index(p.tone),
        format_func={"technical": "Technical", "plain": "Plain", "new": "New to law"}.get,
    )
    styles = ["case_name", "neutral", "inline_para", "footnotes"]
    cstyle = st.selectbox("Citation style", styles, index=styles.index(p.citation_style))
    contrary = st.toggle("Show contrary authority", value=p.contrary_authority != "never")
    history = st.toggle("Save my history", value=p.history_opt_in)
    if st.button("💾 Save as default", use_container_width=True):
        svc.update_profile(
            "default",
            {
                "tone": tone,
                "citation_style": cstyle,
                "history_opt_in": history,
                "contrary_authority": "always" if contrary else "never",
            },
        )
        st.toast("Saved your answer style", icon="✅")
    st.markdown("### 🔎 Filters")
    court = st.selectbox(
        "Court", ["Any", "SC", "Delhi HC", "Bombay HC", "Kerala HC", "Karnataka HC"]
    )
    years = st.slider("Years", 2010, 2025, (2010, 2025))
    st.caption("Corpus: 8 fictional sample judgments. Research aid, not legal advice.")

filters = Filters(
    court=None if court == "Any" else court,
    year_from=years[0] if years[0] > 2010 else None,
    year_to=years[1] if years[1] < 2025 else None,
)
ss = st.session_state
ss.setdefault("q", "")
ss.setdefault("history", [])


def badges(r: Response) -> str:
    v = r.verification
    label = {
        "high": "High confidence",
        "medium": "Medium confidence",
        "low": "Low confidence",
        "not_found": "Not found",
    }[r.confidence]
    mode = {
        "synthesised": "AI-drafted, verified",
        "extractive": "Verbatim quotes",
        "abstained": "Abstained",
    }
    return (
        f"<span class='badge b-{r.confidence}'>{label}</span>"
        f"<span class='badge b-ok'>✓ {v.verified}/{v.claims_proposed} claims verified</span>"
        f"<span class='badge b-not_found'>{mode[v.mode]}</span>"
    )


def chip(label: str, url: str) -> str:
    return f"<a class='chip' href='{escape(url)}' target='_blank'>{escape(label)}</a>"


def render(r: Response, key: str) -> None:
    st.markdown(badges(r), unsafe_allow_html=True)
    v = r.verification
    if v.claims_proposed:
        st.progress(
            v.verified / v.claims_proposed, text="Checked: quote · numbers · meaning · names"
        )
    for n in r.notices:
        if "overruled" in n.lower() or "conflict" in n.lower():
            st.warning(n, icon="⚠️")
        else:
            st.info(n, icon="ℹ️")
    if r.confidence == "not_found":
        near = "".join(f"<span class='chip'>{escape(t)}</span>" for t in r.nearest)
        st.markdown(
            "<div class='card empty'><div style='font-size:2.4rem'>🔍</div>"
            "<h3>Not found in the indexed judgments</h3><div class='meta'>Helper in Law doesn't "
            f"guess. Closest judgments:</div>{near}</div>",
            unsafe_allow_html=True,
        )
        return
    cites = {c.id: c for c in r.citations}
    left, right = st.columns([3, 2], gap="large")
    with left:
        st.markdown("#### Answer")
        for b in r.answer_blocks:
            links = "".join(
                f"<a class='cite' href='{escape(cites[i].url)}' target='_blank' "
                f"title='Open {escape(cites[i].case_title)} at para {cites[i].para}'>{i} ↗</a>"
                for i in b.citation_ids
            )
            st.markdown(
                f"<div class='card answer'>{escape(b.text)}{links}</div>", unsafe_allow_html=True
            )
        if r.laws:
            st.markdown("#### Laws referenced")
            for law in r.laws:
                eq = f" · counterpart: {', '.join(law.equivalents)}" if law.equivalents else ""
                st.markdown(
                    f"<div class='card law'><b>{escape(law.label)}</b>"
                    f"<span class='meta'>{escape(eq)}</span><br>"
                    + chip("Judgments applying it ↗", law.url)
                    + chip("Official text on India Code ↗", law.official_url)
                    + "</div>",
                    unsafe_allow_html=True,
                )
        st.markdown("<div class='meta'>Was this useful?</div>", unsafe_allow_html=True)
        fb = st.feedback("thumbs", key=f"fb-{key}")
        if fb is not None and not ss.get(f"sent-{key}"):
            svc.feedback(r.answer_id or 0, 1 if fb == 1 else -1, "" if fb == 1 else "unhelpful")
            ss[f"sent-{key}"] = True
            st.toast("Thanks, feedback saved", icon="🙏")
    with right:
        st.markdown("#### Sources")
        for c in r.citations:
            bad = c.treatment == "overruled"
            status = (
                f"<span class='badge {'b-bad' if bad else 'b-ok'}'>{escape(c.treatment)}</span>"
            )
            laws = "".join(
                chip(x, f"{svc.cfg.public_url}/statutes/{x.replace(' ', '/')}/view")
                for x in c.statutes
            )
            st.markdown(
                f"<div class='card src'><span class='cite'>{c.id}</span> {status}"
                f"<h4><a href='{escape(c.url)}' target='_blank'>{escape(c.case_title)} ↗</a></h4>"
                f"<div class='meta'>{escape(c.court)} · {escape(c.date)} · {escape(c.citation)} · "
                f"para {c.para}</div><blockquote class='q'>“{escape(c.quote)}”</blockquote>{laws}</div>",
                unsafe_allow_html=True,
            )
    with st.expander("What this answer can't promise"):
        for lim in r.coverage.limits:
            st.write("• " + lim)
        st.caption(f"{r.coverage.corpus}, as of {r.coverage.as_of}. {r.disclaimer}")


tab_ask, tab_browse, tab_law = st.tabs(["⚖️  Ask", "📚  Browse judgments", "📜  Statutes"])

with tab_ask:
    with st.form("ask", border=False):
        c1, c2 = st.columns([6, 1], vertical_alignment="bottom")
        typed = c1.text_input(
            "Question",
            value=ss.q,
            label_visibility="collapsed",
            placeholder="Ask a legal research question…  e.g. grounds for refusing bail",
        )
        if c2.form_submit_button("Ask  ⚖️", use_container_width=True):
            ss.q = typed.strip()
    recent = [h for h in ss.history if h not in EXAMPLES][-3:]
    pick = st.pills("Try one", EXAMPLES + recent, key="pick", label_visibility="collapsed")
    if pick and pick != ss.get("last_pick"):
        ss.last_pick = pick
        ss.q = pick
        st.rerun()
    if ss.q:
        d1, d2 = st.columns(2)
        depth = d1.segmented_control(
            "Depth",
            ["quick", "standard", "deep"],
            default="standard",
            format_func=str.title,
            key="depth",
        )
        structure = d2.segmented_control(
            "Layout",
            ["bullets", "paragraphs", "irac", "memo", "table"],
            default="bullets",
            key="structure",
            format_func=lambda s: {"irac": "IRAC"}.get(s, s.title()),
        )
        style = {
            "depth": depth or "standard",
            "structure": structure or "bullets",
            "tone": tone,
            "citation_style": cstyle,
            "contrary_authority": "always" if contrary else "never",
        }
        with st.spinner("Searching judgments · checking every quote against its paragraph…"):
            resp = svc.ask(ss.q, filters, style)
        if ss.q not in ss.history:
            ss.history.append(ss.q)
        render(resp, ss.q)
    else:
        st.markdown(
            "<div class='card empty'><div style='font-size:2.4rem'>⚖️</div><h3>Ask anything about the "
            "indexed judgments</h3><div class='meta'>Press Enter or click Ask, or pick a question above. "
            "After answering, switch Depth and Layout: the verified facts stay identical.</div></div>",
            unsafe_allow_html=True,
        )

with tab_browse:
    cases = svc.list_cases()
    cols = st.columns(2)
    for i, c in enumerate(cases):
        bad = c["treatment"] == "overruled"
        cols[i % 2].markdown(
            f"<div class='card src'><h4><a href='{escape(c['url'])}' target='_blank'>"
            f"{escape(c['title'])} ↗</a></h4><div class='meta'>{escape(c['court'])} · "
            f"{escape(c['date'])} · {escape(c['citation'])}</div>"
            f"<span class='badge {'b-bad' if bad else 'b-ok'}'>{escape(c['treatment'])}</span></div>",
            unsafe_allow_html=True,
        )
    st.markdown("#### Chat with one judgment")
    titles = {c["title"]: c["case_id"] for c in cases}
    chosen = st.selectbox("Judgment", list(titles))
    case = svc.get_case(titles[chosen])
    st.markdown(
        "".join(chip(law["label"], law["url"]) for law in case["laws"])
        + chip("Open full judgment ↗", case["url"]),
        unsafe_allow_html=True,
    )
    with st.form("chat", border=False):
        k1, k2 = st.columns([6, 1], vertical_alignment="bottom")
        cq = k1.text_input(
            "Ask this judgment", label_visibility="collapsed", placeholder=f"Ask about {chosen}…"
        )
        asked = k2.form_submit_button("Ask  ⚖️", use_container_width=True)
    if asked and cq.strip():
        with st.spinner("Reading the judgment…"):
            render(svc.chat_case(titles[chosen], cq.strip(), {"tone": tone}), f"chat-{chosen}-{cq}")
    with st.expander("Read the full judgment here"):
        for para in svc.store.get_paragraphs(titles[chosen]):
            st.markdown(
                f"**{para.n}.** <span class='meta'>{para.section}</span><br>{escape(para.text)}",
                unsafe_allow_html=True,
            )

with tab_law:
    quick = st.pills(
        "Popular",
        ["IPC 302", "BNS 103", "CrPC 439", "CrPC 438", "IEA 65B", "IPC 304B", "CrPC 125"],
        key="lawpick",
    )
    with st.form("law", border=False):
        a1, a2, a3 = st.columns([2, 2, 1], vertical_alignment="bottom")
        act = a1.selectbox(
            "Act",
            ["IPC", "BNS", "CrPC", "BNSS", "IEA", "BSA", "CONST"],
            format_func=lambda x: ACT_LABEL.get(x, x),
        )
        sec = a2.text_input("Section", placeholder="e.g. 302")
        go = a3.form_submit_button("Look up", use_container_width=True)
    if go and sec.strip():
        act, sec = act, sec.strip()
    elif quick:
        act, sec = quick.split(" ")
    if (go and sec) or quick:
        info = svc.lookup_statute(act, sec)
        law = info["law"]
        st.markdown(
            f"<div class='card law'><h3 style='margin:0'>{escape(law['label'])}</h3>"
            f"<div class='meta'>{escape(' ↔ '.join(info['equivalents']))}</div>"
            + chip("Official text on India Code ↗", law["official_url"])
            + chip("Statute page ↗", law["url"])
            + "</div>",
            unsafe_allow_html=True,
        )
        if not info["cases"]:
            st.info("No indexed judgment applies this provision.")
        for c in info["cases"]:
            st.markdown(
                f"<div class='card src'><h4><a href='{escape(c['url'])}' target='_blank'>{escape(c['title'])}"
                f" ↗</a></h4><div class='meta'>{escape(c['citation'])} · {escape(c['date'])} · "
                f"{escape(c['treatment'])}</div></div>",
                unsafe_allow_html=True,
            )
        st.caption(info["note"])
