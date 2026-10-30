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
    "tortured": ["life", "personal liberty", "custody", "dignity"],
    "assaulted": ["life", "personal liberty", "custody"],
    "died": ["life", "deprived of his life"],
    "death": ["life", "deprived of his life"],
    "custody": ["custody", "personal liberty"],
    "undertrial": ["personal liberty", "speedy trial"],
    "trial": ["speedy trial", "procedure established by law"],
    "bail": ["personal liberty", "bail"],
    "prison": ["personal liberty", "custody"],
    "handcuffed": ["personal liberty", "dignity"],
    "passport": ["personal liberty", "travel abroad"],
    "tapping": ["privacy", "personal liberty"],
    "monitoring": ["privacy", "personal liberty"],
    "slum": ["shelter", "life", "livelihood"],
    "homes": ["shelter", "life"],
    "hospital": ["health", "medical", "life"],
    "treatment": ["health", "medical", "life"],
    "polluting": ["environment", "pollution", "life"],
    "pollution": ["environment", "life"],
    "water": ["environment", "life"],
    "internet": ["freedom of speech and expression", "reasonable restrictions"],
    "film": ["freedom of speech and expression"],
    "journalist": ["freedom of speech and expression", "press"],
    "banned": ["reasonable restrictions", "prohibited"],
    "licence": ["carry on any occupation, trade or business"],
    "business": ["carry on any occupation, trade or business"],
    "profession": ["practise any profession"],
    "tender": ["equality before the law", "arbitrary"],
    "contract": ["equality before the law", "arbitrary"],
    "favoured": ["arbitrary", "equality"],
    "arbitrarily": ["arbitrary", "equality before the law"],
    "identical": ["equal protection", "equality", "classification"],
    "pay": ["equal pay for equal work"],
    "paid": ["equal pay for equal work"],
    "admission": ["educational institutions", "discriminate"],
    "born": ["place of birth", "discriminate"],
    "dalit": ["untouchability", "scheduled castes"],
    "well": ["wells, tanks", "untouchability"],
    "bonded": ["forced labour", "begar"],
    "loan": ["forced labour", "begar"],
    "factory": ["employed to work in any factory"],
    "law": ["law in force at the time"],
    "poor": ["free and compulsory education", "weaker sections"],
    "compensation": ["deprived of his property", "authority of law"],
    "writ": ["issue writs", "directions, orders or writs"],
    "quash": ["writs", "certiorari"],
    "fundamental": ["enforcement of the rights conferred by this Part"],
    "approach": ["move the Supreme Court", "appropriate proceedings"],
    "employee": ["member of a civil service", "civil post"],
    "inquiry": ["inquiry", "reasonable opportunity of being heard"],
    "defend": ["reasonable opportunity of being heard"],
    "punished": ["law in force at the time of the commission"],
    "made": ["law in force at the time"],
    "caste": ["caste", "discriminate", "grounds only of religion, race, caste"],
    # Criminal practice (found missing by eval/run_criminal.py).
    "confession": ["witness against himself", "compelled"],
    "compel": ["witness against himself", "compelled"],
    "compelled": ["witness against himself", "compelled"],
    "narco": ["witness against himself", "compelled", "personal liberty"],
    "polygraph": ["witness against himself", "compelled", "personal liberty"],
    "specimen": ["witness against himself", "compelled"],
    "fingerprints": ["witness against himself", "compelled"],
    "handwriting": ["witness against himself", "compelled"],
    "encounter": ["deprived of his life", "procedure established by law"],
    "shoot": ["deprived of his life", "life"],
    "killed": ["deprived of his life", "life"],
    "lynching": ["deprived of his life", "life", "protection"],
    "juvenile": ["children", "child"],
    "sedition": ["freedom of speech and expression", "reasonable restrictions", "public order"],
    "uapa": ["personal liberty", "reasonable restrictions", "public order"],
    "terrorism": ["personal liberty", "public order", "security of the State"],
    "bulldozer": ["deprived of his property", "authority of law", "shelter"],
    "slaughter": ["slaughter of cows", "breeds"],
    "adultery": ["equality before the law", "dignity"],
    "detain": ["detention", "custody"],
    "sources": ["freedom of speech and expression", "press"],
    "copies": ["procedure established by law", "fair trial"],
    "mercy": ["pardons, reprieves, respites or remissions"],
    "pardon": ["pardons, reprieves, respites or remissions"],
    "remission": ["pardons, reprieves, respites or remissions"],
    "anthem": ["national anthem", "fundamental duties"],
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
