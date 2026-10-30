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


# Lay words the rewrite maps to legal terms ("told" -> informed, "water" -> right to water). Each is
# an everyday word, so one alone doesn't make a question legal ("boiling point of water").
LAY = {stem(k) for k in LEGAL_TERMS} - LEGAL_WORDS
LEGAL = LEGAL_WORDS | LAY  # kept for the ablation runner

_US_STATES = "|".join("""Alabama Alaska Arizona Arkansas California Colorado Connecticut Delaware Florida
Georgia Hawaii Idaho Illinois Indiana Iowa Kansas Kentucky Louisiana Maine Maryland Massachusetts
Michigan Minnesota Mississippi Missouri Montana Nebraska Nevada Ohio Oklahoma Oregon Pennsylvania
Tennessee Texas Utah Vermont Virginia Washington Wisconsin Wyoming""".split()) + (
    "|New Hampshire|New Jersey|New Mexico|New York|North Carolina|North Dakota|Rhode Island"
    "|South Carolina|South Dakota|West Virginia"
)
_PLACE = (r"(?:the\s+)?(?:US|U\.S\.|USA|United States|America|UK|U\.K\.|United Kingdom|England|Britain|"
          r"Canada|Ontario|Australia|Germany|Japan|Europe|European Union|" + _US_STATES + ")")
FOREIGN = re.compile(
    r"\b(?:American|British|English|Canadian|Australian|German|Japanese|European)\s+"
    r"(?i:law|laws|courts?|constitution|parliament|statutes?|convention)\b"
    # Case-sensitive "US" (not the pronoun "us"); the nouns after it in any case.
    r"|\b(?:US|U\.S\.|USA|UK|U\.K\.)\b.{0,30}?\b(?i:law|laws|courts?|constitution|congress|amendment|patent)\b"
    rf"|\b(?:in|of|under)\s+{_PLACE}\b"
    rf"|\bv(?:s)?\.?\s+{_PLACE}\b"  # a foreign party: "Miranda v. Arizona"
)
INDIA = re.compile(r"\b(?:India|Indian|Bharat)\b")


def legal_question(q: Query) -> bool:
    words = {stem(t) for t in terms(q.text)}
    return bool(q.statutes or SECTION_LIKE.search(q.text) or words & LEGAL_WORDS or len(words & LAY) >= 2)


def foreign(question: str) -> str:
    """The foreign jurisdiction a question is about ("" when none, or when India is named too).
    Answering it from Indian sources would mislead, so the pipeline declines instead."""
    m = FOREIGN.search(question)
    return m.group(0).strip() if m and not INDIA.search(question) else ""


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
