from helperinlaw.core.config import Settings
from helperinlaw.core.store import Store
from helperinlaw.core.types import Filters, Profile
from helperinlaw.ground.pipeline import retrieve
from helperinlaw.retrieve.hybrid import cosine, fts_match
from helperinlaw.retrieve.rewrite import rewrite
from helperinlaw.retrieve.understand import understand


def test_understand_filters_and_statutes() -> None:
    q = understand("Supreme Court cases on Section 302 IPC after 2015")
    assert q.filters.court == "SC" and q.filters.year_from == 2015
    assert ("IPC", "302") in q.statutes
    q = understand("bail in the Bombay High Court between 2019 and 2022")
    assert q.filters.court == "Bombay HC"
    assert (q.filters.year_from, q.filters.year_to) == (2019, 2022)


def test_explicit_filters_win() -> None:
    q = understand("cases after 2015", Filters(year_from=2020))
    assert q.filters.year_from == 2020


def test_rewrite_adds_alias() -> None:
    qs = rewrite(understand("What does Section 103 BNS say?"))
    assert any("302" in q for q in qs)


def test_fts_match_is_safe() -> None:
    assert fts_match('bail" OR 1=1; DROP') == '"bail" OR "drop"'
    assert fts_match("the of and") == ""


def test_cosine() -> None:
    assert cosine([1, 0], [1, 0]) == 1.0 and cosine([1, 0], [0, 1]) == 0.0


def top_case(store: Store, cfg: Settings, q: str, f: Filters | None = None) -> str:
    sources, _ = retrieve(store, cfg, q, f, Profile())
    return sources[0].chunk.case_id


def test_alias_finds_old_code_judgment(store: Store, cfg: Settings) -> None:
    # BNS 103 question must reach IPC 302 judgments too.
    sources, ok = retrieve(store, cfg, "murder under Section 103 BNS", None, Profile())
    ids = {s.chunk.case_id for s in sources}
    assert ok and {"fs_2024_rao", "fs_2012_pillai"} <= ids


def test_filters_restrict_results(store: Store, cfg: Settings) -> None:
    # Filters choose precedents; Constitution articles always pass (they govern every court).
    sources, _ = retrieve(store, cfg, "bail", Filters(court="Bombay HC"), Profile())
    assert sources and all(s.chunk.case_id == "fs_2021_shaikh" for s in sources if not s.chunk.case_id.startswith("coi-"))
    sources, _ = retrieve(store, cfg, "bail", Filters(year_to=2016), Profile())
    assert all(
        s.chunk.case_id in {"fs_2015_mehta", "fs_2012_pillai", "fs_2016_verma"} for s in sources if not s.chunk.case_id.startswith("coi-")
    )


def test_evidence_gate(store: Store, cfg: Settings) -> None:
    _, ok = retrieve(
        store, cfg, "What is the punishment for sedition under Section 124A IPC?", None, Profile()
    )
    assert not ok
    _, ok = retrieve(
        store, cfg, "grounds for refusing bail under Section 439 CrPC", None, Profile()
    )
    assert ok


def test_excerpt_keeps_best_sentences_verbatim_in_order() -> None:
    from helperinlaw.ground.claim_extract import excerpt

    text = "⟦4⟧ The weather was fine. The arrest was made at night. ⟦5⟧ Lunch followed. The detenu was not told the grounds of arrest."
    out = excerpt(text, "arrested without being told the grounds of arrest", k=2)
    assert out == "The arrest was made at night. The detenu was not told the grounds of arrest."


def test_stair_constrains_to_the_table_and_falls_back(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    from helperinlaw.core import ollama
    from helperinlaw.core.types import TocEntry
    from helperinlaw.retrieve import stair

    s = Store(":memory:")
    s.replace_toc([
        TocEntry(number="14", title="Equality before law", part="PART III — FUNDAMENTAL RIGHTS", group="Right to Equality"),
        TocEntry(number="21", title="Protection of life and personal liberty", part="PART III — FUNDAMENTAL RIGHTS", group="Right to Freedom"),
        TocEntry(number="22", title="Protection against arrest and detention in certain cases", part="PART III — FUNDAMENTAL RIGHTS", group="Right to Freedom"),
    ])
    seen = {}

    def fake(model, system, user, schema, options=None, timeout=120):  # type: ignore[no-untyped-def]
        seen.update(system=system, enum=schema["properties"]["articles"]["items"]["enum"])
        return {"articles": ["22", "21", "22"]}

    monkeypatch.setattr(ollama, "chat_json", fake)
    stair._pick.cache_clear()
    on = Settings(use_stair=True, db_path=":memory:")
    assert stair.stair_articles(s, on, "arrested without being told why") == ["22", "21"]  # order kept, no repeats
    assert seen["enum"] == ["14", "21", "22"]  # only Articles in the table can be named
    assert "Right to Freedom\n   21. Protection of life and personal liberty" in seen["system"]

    def down(*a, **k):  # type: ignore[no-untyped-def]
        raise ollama.OllamaError("offline")

    monkeypatch.setattr(ollama, "chat_json", down)
    stair._pick.cache_clear()
    assert stair.stair_articles(s, on, "another situation") == []  # offline: keyword search alone
    assert stair.stair_articles(s, Settings(use_stair=False, db_path=":memory:"), "x") == []


def test_stair_picks_are_boosted(store: Store, cfg: Settings, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    import helperinlaw.ground.pipeline as pipeline

    question = "My client's freedom of speech was restricted after an online post."

    def score(sources: list) -> float:  # type: ignore[type-arg]
        return max((x.score for x in sources if x.chunk.case_id == "coi-21"), default=0.0)

    base, _ = retrieve(store, cfg, question, None, Profile())
    monkeypatch.setattr(pipeline, "stair_articles", lambda *a: ["21"])
    with_stair, _ = retrieve(store, cfg, question, None, Profile())
    assert score(with_stair) >= score(base) + pipeline.STAIR_BOOST - 1e-6  # Article 21 is a candidate, boosted


def test_gate_needs_a_legal_word_or_two_lay_words() -> None:
    from helperinlaw.retrieve.evidence_gate import legal_question

    # One everyday word the rewrite knows ("water", "old", "tell") is not a legal question...
    assert not legal_question(understand("What is the boiling point of water at high altitude?"))
    assert not legal_question(understand("What should I feed a two-month-old puppy?"))
    # ...two of them, or one legal word, are.
    assert legal_question(understand("Factories are polluting the river the village depends on for drinking water."))
    assert legal_question(understand("My client was arrested at night."))


def test_foreign_law_is_declined() -> None:
    from helperinlaw.retrieve.evidence_gate import foreign

    assert foreign("Under the US Fourth Amendment, can police search my car?")
    assert foreign("How do I file for divorce in California?")
    assert foreign("What are the requirements for a valid will under English law?")
    assert not foreign("Tell us about the law on arrest.")  # the pronoun, not the country
    assert not foreign("My client, an NRI back from the US, was arrested at Delhi airport.")
    assert not foreign("My client in India studied in the UK and was denied a passport.")
    assert foreign("What does Miranda v. Arizona require police to tell a suspect?")
    assert not foreign("Does Maneka Gandhi v. Union of India apply to passports?")


def test_spelling_is_corrected_against_the_corpus() -> None:
    from collections import Counter

    from helperinlaw.retrieve.understand import correct_spelling

    counts = Counter({"arrested": 50, "warrant": 40, "arrest": 90})
    assert correct_spelling("He was arersted without a wararnt.", counts) == "He was arrested without a warrant."
    assert correct_spelling("Rakesh was arrested.", counts) == "Rakesh was arrested."  # names are kept
    assert correct_spelling("an unknownword here", counts) == "an unknownword here"


def test_conversational_words_do_not_outrank_facts() -> None:
    from helperinlaw.retrieve.understand import terms

    assert terms("Sir, urgent query. Kindly advise: my client was arrested.") == ["arrested"]
