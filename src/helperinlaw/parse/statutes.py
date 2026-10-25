"""Statute references and the old-code <-> new-code alias table (IPC<->BNS, CrPC<->BNSS,
Evidence Act<->BSA)."""

import re

ACT_NAMES = {
    "IPC": ["Indian Penal Code", "IPC", "I.P.C."],
    "BNS": ["Bharatiya Nyaya Sanhita, 2023", "Bharatiya Nyaya Sanhita", "BNS"],
    "CrPC": ["Code of Criminal Procedure", "Cr.P.C.", "CrPC", "Cr.PC"],
    "BNSS": [
        "Bharatiya Nagarik Suraksha Sanhita, 2023",
        "Bharatiya Nagarik Suraksha Sanhita",
        "BNSS",
    ],
    "IEA": ["Indian Evidence Act", "Evidence Act", "IEA"],
    "BSA": ["Bharatiya Sakshya Adhiniyam, 2023", "Bharatiya Sakshya Adhiniyam", "BSA"],
}
_ALT = sorted(
    ((name, act) for act, names in ACT_NAMES.items() for name in names), key=lambda x: -len(x[0])
)
_ACT_RX = "|".join(re.escape(n) for n, _ in _ALT)
_NAME_TO_ACT = {n.lower(): a for n, a in _ALT}

SECTION = re.compile(
    rf"\b(?:Sections?|Sec\.|S\.)\s+(?P<s>\d+[A-Z]?)(?:\(\d+\))*(?:\s+Part\s+I{{1,2}})?"
    rf"\s+(?:of\s+the\s+)?(?P<act>{_ACT_RX})",
)
ARTICLE = re.compile(r"\bArticle\s+(?P<s>\d+[A-Z]?)(?:\(\d+\))?\s+of\s+the\s+Constitution")

# 🔍 Verify against the official correspondence tables before relying on these.
ALIASES: list[tuple[tuple[str, str], tuple[str, str]]] = [
    (("IPC", "34"), ("BNS", "3")),
    (("IPC", "120B"), ("BNS", "61")),
    (("IPC", "299"), ("BNS", "100")),
    (("IPC", "300"), ("BNS", "101")),
    (("IPC", "302"), ("BNS", "103")),
    (("IPC", "304"), ("BNS", "105")),
    (("IPC", "304A"), ("BNS", "106")),
    (("IPC", "304B"), ("BNS", "80")),
    (("IPC", "307"), ("BNS", "109")),
    (("IPC", "376"), ("BNS", "64")),
    (("IPC", "420"), ("BNS", "318")),
    (("IPC", "498A"), ("BNS", "85")),
    (("CrPC", "125"), ("BNSS", "144")),
    (("CrPC", "154"), ("BNSS", "173")),
    (("CrPC", "161"), ("BNSS", "180")),
    (("CrPC", "164"), ("BNSS", "183")),
    (("CrPC", "313"), ("BNSS", "351")),
    (("CrPC", "437"), ("BNSS", "480")),
    (("CrPC", "438"), ("BNSS", "482")),
    (("CrPC", "439"), ("BNSS", "483")),
    (("CrPC", "482"), ("BNSS", "528")),
    (("IEA", "32"), ("BSA", "26")),
    (("IEA", "65B"), ("BSA", "63")),
    (("IEA", "106"), ("BSA", "109")),
    (("IEA", "113B"), ("BSA", "118")),
]


def normalise_act(name: str) -> str | None:
    name = name.strip().rstrip(".").lower()
    for n, act in _NAME_TO_ACT.items():
        if n.rstrip(".") == name:
            return act
    return {"constitution": "CONST"}.get(name)


def extract_statutes(text: str) -> list[tuple[str, str]]:
    refs = [(_NAME_TO_ACT[m.group("act").lower()], m.group("s")) for m in SECTION.finditer(text)]
    refs += [("CONST", m.group("s")) for m in ARTICLE.finditer(text)]
    return sorted(set(refs))


def aliases(act: str, section: str) -> list[tuple[str, str]]:
    """The reference itself plus its counterpart in the other code, if known."""
    out = [(act, section)]
    for old, new in ALIASES:
        if (act, section) == old:
            out.append(new)
        elif (act, section) == new:
            out.append(old)
    return out
