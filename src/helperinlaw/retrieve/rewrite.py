"""Query rewrite. Deterministic:
- statute references expand to their old/new-code counterpart (BNS 103 <-> IPC 302);
- a lawyer's plain description expands to the words the Constitution and judgments use
  ("not told why" -> "informed of the grounds", "lawyer" -> "legal practitioner").

ponytail: a hand-kept lay-to-legal map. Embeddings (index build with Ollama) close the rest of
the vocabulary gap; add an LLM rewrite if the eval still shows misses.
"""

from helperinlaw.parse.statutes import ACT_NAMES, aliases
from helperinlaw.retrieve.understand import Query, terms

# lay word -> words the legal text uses for the same idea
LEGAL_TERMS: dict[str, list[str]] = {
    "lawyer": ["legal practitioner", "counsel", "advocate"],
    "lawyers": ["legal practitioner", "counsel", "advocate"],
    "attorney": ["legal practitioner", "counsel"],
    "told": ["informed", "grounds"],
    "tell": ["informed", "grounds"],
    "why": ["grounds"],
    "reason": ["grounds"],
    "jail": ["custody", "detention", "imprisonment"],
    "jailed": ["custody", "detention", "imprisonment"],
    "locked": ["custody", "detention"],
    "detained": ["detention", "custody"],
    "held": ["custody", "detention"],
    "police": ["arrest", "custody", "investigation"],
    "magistrate": ["magistrate", "produced"],
    "court": ["magistrate"],
    "speech": ["freedom of speech and expression"],
    "post": ["expression", "speech"],
    "posted": ["expression", "speech"],
    "criticism": ["expression", "speech"],
    "online": ["expression", "speech"],
    "protest": ["assemble peaceably", "expression"],
    "religion": ["religion", "conscience", "worship"],
    "temple": ["places of public worship", "religion"],
    "women": ["sex", "women"],
    "woman": ["sex", "women"],
    "caste": ["caste", "discrimination"],
    "discriminated": ["discrimination", "equality"],
    "unequal": ["equality", "equal protection", "arbitrary"],
    "unfair": ["arbitrary", "equality"],
    "excludes": ["discrimination", "classification"],
    "job": ["employment", "public employment"],
    "fired": ["dismissed", "removed", "service"],
    "sacked": ["dismissed", "removed", "service"],
    "dismissed": ["dismissed", "removed", "service"],
    "government": ["state"],
    "privacy": ["privacy", "personal liberty"],
    "phone": ["privacy", "surveillance"],
    "dignity": ["dignity", "life"],
    "shelter": ["shelter", "life"],
    "health": ["health", "life"],
    "school": ["education"],
    "education": ["education"],
    "children": ["children", "child"],
    "land": ["property", "acquisition"],
    "house": ["property", "shelter"],
    "demolished": ["property", "eviction"],
    "property": ["property", "deprived"],
    "pension": ["pension", "social security"],
    "old": ["elderly", "senior citizens", "aged"],
    "widow": ["widow", "destitute"],
    "torture": ["custodial", "life", "personal liberty"],
    "beaten": ["custodial violence", "torture"],
    "tried": ["prosecuted", "punished"],
    "twice": ["same offence more than once"],
    "confess": ["witness against himself", "compelled"],
    "forced": ["compelled", "forced labour"],
}


def legal_expansion(text: str) -> list[str]:
    seen = set(terms(text))
    out: list[str] = []
    for t in terms(text):
        for phrase in LEGAL_TERMS.get(t, []):
            if phrase not in out and phrase not in seen:
                out.append(phrase)
    return out


def rewrite(q: Query) -> list[str]:
    queries = [q.text]
    if extra := legal_expansion(q.text):
        queries.append(" ".join(extra))
    for act, section in q.statutes:
        for a, s in aliases(act, section):
            name = ACT_NAMES.get(a, [a])[0]
            queries.append(f"Section {s} {a} {name}")
    return list(dict.fromkeys(queries))
