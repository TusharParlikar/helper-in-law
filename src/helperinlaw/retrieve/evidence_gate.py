"""G7 evidence gate: weak evidence -> abstain, no generation."""

import re

from helperinlaw.core.store import Store
from helperinlaw.core.types import Chunk
from helperinlaw.parse.statutes import aliases
from helperinlaw.retrieve.rerank import stem
from helperinlaw.retrieve.rewrite import LEGAL_TERMS
from helperinlaw.retrieve.understand import Query, terms

# Words a legal question almost always uses; off-topic questions ("best way to lose weight",
# "which smartphone for twenty thousand rupees") use none, yet can match a passage by accident.
LEGAL_WORDS = {stem(w) for w in """
accused acquitted act acts administration admission advocate appeal arrest arrested article
articles assembly authorities authority bail ban banned board case caste censor challenge
charge citizen citizens civil client clients compensation complaint confession constitution
constitutional contract conviction convicted counsel court courts crime criminal custody
death defend demolished department detained detention dignity discriminate discrimination
dismissed due employee employees employment equality equal evicted eviction evidence fir
freedom fundamental government guilty hearing illegal inquiry institution jail job judge
judgment judgments justice labour labourers land law laws lawyer legal liberty licence
magistrate minority notice offence officer officers order ordinance parliament passport
penalty pension permit petition police policy post posts practice prison privacy property
prosecuted prosecution protest public punish punished punishment quota recruitment religion
religious remedy reservation right rights rule rules scheme school service speech state
statute surety temple tender trial tribunal unconstitutional undertrial violated violation
vote wages warrant women writ certificate mandatory valid invalid void lawful unlawful entitled
liable liability obligation duty duties exempt exemption maintenance divorce marriage wife
husband dowry murder theft fraud cheating tax""".split()}
SECTION_LIKE = re.compile(r"\b\d{1,4}[A-Z]{1,3}\b")  # "65B", "304B", "21A": a provision, whatever the Act


LEGAL = LEGAL_WORDS | {stem(k) for k in LEGAL_TERMS}


def legal_question(q: Query) -> bool:
    return bool(q.statutes or SECTION_LIKE.search(q.text) or {stem(t) for t in terms(q.text)} & LEGAL)


def enough_evidence(
    store: Store, q: Query, ranked: list[tuple[Chunk, float]], min_score: float, min_passages: int
) -> bool:
    if not legal_question(q):
        return False
    strong = [c for c, s in ranked if s >= min_score]
    if len(strong) < min_passages:
        return False
    # A question about a specific provision needs a passage from a case that applies it.
    if q.statutes:
        wanted = {a for act, s in q.statutes for a in aliases(act, s)}
        return any(wanted & set(store.statutes_of(c.case_id)) for c in strong)
    return True
