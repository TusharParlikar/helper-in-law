"""Streamlit UI: uv run streamlit run ui/app.py  (needs the "ui" extra)."""

import streamlit as st

from helperinlaw.core.types import Filters
from helperinlaw.service import Service

st.set_page_config(page_title="Helper in Law", layout="wide")


@st.cache_resource
def service() -> Service:
    return Service()


svc = service()
st.title("Helper in Law")
st.caption("Research aid over Indian court judgments. Not legal advice.")

with st.sidebar:
    st.header("How do you like your answers?")
    p = svc.get_profile()
    changes = {
        "depth": st.selectbox(
            "Depth",
            ["quick", "standard", "deep"],
            index=["quick", "standard", "deep"].index(p.depth),
        ),
        "structure": st.selectbox(
            "Structure",
            ["bullets", "paragraphs", "irac", "memo", "table"],
            index=["bullets", "paragraphs", "irac", "memo", "table"].index(p.structure),
        ),
        "tone": st.selectbox(
            "Tone", ["technical", "plain", "new"], index=["technical", "plain", "new"].index(p.tone)
        ),
        "citation_style": st.selectbox(
            "Citation style",
            ["case_name", "neutral", "inline_para", "footnotes"],
            index=["case_name", "neutral", "inline_para", "footnotes"].index(p.citation_style),
        ),
        "history_opt_in": st.checkbox("Save my history", value=p.history_opt_in),
    }
    if st.button("Save settings"):
        svc.update_profile("default", changes)
        st.success("Saved")
    st.header("Filters")
    court = st.text_input("Court (e.g. SC, Delhi HC)") or None
    year_from = st.number_input("From year", 0, 2100, 0) or None

q = st.text_input("Ask a legal research question")
if q:
    r = svc.ask(q, Filters(court=court, year_from=year_from))
    v = r.verification
    badge = {"high": "🟢", "medium": "🟡", "low": "🟠", "not_found": "⚪"}[r.confidence]
    st.markdown(
        f"{badge} **Confidence: {r.confidence}** · verified {v.verified}/{v.claims_proposed}"
        f" claims · mode: {v.mode}"
    )
    for n in r.notices:
        st.info(n)
    if r.confidence == "not_found":
        st.warning("Not found in the indexed judgments.")
        if r.nearest:
            st.write("Closest judgments: " + "; ".join(r.nearest))
    cites = {c.id: c for c in r.citations}
    left, right = st.columns([3, 2])
    with left:
        for b in r.answer_blocks:
            st.markdown(f"{b.text} " + " ".join(f"`{i}`" for i in b.citation_ids))
    with right:
        for c in r.citations:
            with st.expander(f"{c.id} · {c.case_title}, para {c.para} ({c.treatment})"):
                st.caption(f"{c.court} · {c.date} · {c.citation} · {c.neutral_citation}")
                for para in svc.get_paragraphs(c.case_id, int(c.para)):
                    st.markdown(para["text"].replace(c.quote, f"**{c.quote}**"))
    with st.expander("Limits"):
        st.write(f"Corpus: {r.coverage.corpus} (as of {r.coverage.as_of})")
        for lim in r.coverage.limits:
            st.write("- " + lim)
    st.caption(r.disclaimer)
