"""THE core API. REST, MCP and the UI are thin adapters over this module; no logic lives in
handlers."""

from typing import Any

from helperinlaw.core import ollama
from helperinlaw.core.config import Settings, settings
from helperinlaw.core.store import Store
from helperinlaw.core.types import (
    LIMITS,
    Confidence,
    Coverage,
    Filters,
    Profile,
    Response,
    VerifiedClaimSet,
)
from helperinlaw.ground.pipeline import answer_content, retrieve
from helperinlaw.ground.render import case_url, law_ref, render_citations, render_laws
from helperinlaw.ground.verify.graph import treatment
from helperinlaw.ingest.official import COI_EDITION, PREFIX, ingest_constitution, is_provision
from helperinlaw.parse.statutes import ACT_NAMES, aliases, extract_statutes, normalise_act
from helperinlaw.present.final_guard import guard
from helperinlaw.present.overrides import parse_overrides, strip_overrides
from helperinlaw.present.presenter import present
from helperinlaw.present.profile import apply_style, suggest_setting, update_profile
from helperinlaw.present.translate import translate

MAX_SEARCH = 20


def extract_statutes_in(text: str, act: str, section: str) -> bool:
    return (act, section) in extract_statutes(text)


MAX_PARAS = 10


class Service:
    def __init__(self, store: Store | None = None, cfg: Settings | None = None) -> None:
        self.cfg = cfg or settings
        self.store = store or Store(self.cfg.db_path)
        # ponytail: in-process dict cache of Verified Claim Sets; Redis in Phase 2.
        self._claims: dict[tuple[str, ...], VerifiedClaimSet] = {}

    def coverage(self) -> Coverage:
        if self.cfg.corpus_name:
            return Coverage(corpus=self.cfg.corpus_name, as_of=self.cfg.corpus_as_of, limits=LIMITS)
        cases = self.store.list_cases()
        n_prov = sum(is_provision(c.id) for c in cases)
        judgments = [c for c in cases if not is_provision(c.id)]
        parts = []
        if n_prov:
            parts.append(f"Constitution of India, {n_prov} articles (official text as on 1 May 2024)")
        if judgments:
            years = sorted(c.date[:4] for c in judgments if c.date)
            parts.append(f"{len(judgments)} judgments ({years[0]}-{years[-1]})" if years else f"{len(judgments)} judgments")
        latest = max((c.date for c in judgments), default=self.cfg.corpus_as_of)
        return Coverage(corpus="; ".join(parts) or "empty", as_of=latest, limits=LIMITS)

    # --- ask -----------------------------------------------------------------

    def content(self, question: str, filters: Filters | None, profile: Profile) -> VerifiedClaimSet:
        """Stage A, cached per (question, filters, index_version, retrieval preferences)."""
        key = (
            question,
            (filters or Filters()).model_dump_json(),
            self.cfg.index_version,
            profile.recency,
            ",".join(profile.jurisdiction),
        )
        if key not in self._claims:
            self._claims[key] = answer_content(self.store, self.cfg, question, filters, profile)
        return self._claims[key]

    def ask(
        self,
        question: str,
        filters: Filters | None = None,
        style: dict[str, Any] | None = None,
        profile_id: str = "default",
    ) -> Response:
        question = question.strip()[:2000]
        patch, ignored = parse_overrides(question)
        profile = apply_style(self.store.get_profile(profile_id), {**patch, **(style or {})})
        legal_q = strip_overrides(question) or question
        vcs = self.content(legal_q, filters, profile)

        notices = [
            f'Ignored request "{x}": citations, verification and abstaining can\'t be turned off.'
            for x in ignored
        ]
        notices += vcs.report.conflicts
        applied: dict[str, str] = {
            "depth": profile.depth,
            "structure": profile.structure,
            "tone": profile.tone,
            "language": profile.answer_language,
            "citation_style": profile.citation_style,
        }

        citations, by_claim = render_citations(self.store, vcs.claims, self.cfg.public_url)
        blocks = present(vcs.claims, by_claim, citations, profile)
        if profile.answer_language != "en" and blocks:
            english = blocks
            try:
                translated, blocked = guard(
                    translate(blocks, profile.answer_language, self.cfg.llm_model),
                    vcs.claims,
                    citations,
                )
                blocks = translated if not blocked else english
                if blocked:
                    notices.append(
                        "Translation changed a number or name, so the English answer is shown."
                    )
            except ollama.OllamaError:
                notices.append(
                    "Translation unavailable; showing English. Quotes are always in the original."
                )
        blocks, blocked = guard(blocks, vcs.claims, citations)
        if blocked:
            notices.append(f"{blocked} sentence(s) removed by the final guard.")

        if not blocks:
            nearest = [c.title for cid in vcs.nearest if (c := self.store.get_case(cid))]
            return Response(
                answer_blocks=[],
                citations=[],
                verification=vcs.report,
                coverage=self.coverage(),
                confidence="not_found",
                profile_applied=applied,
                notices=notices + vcs.gaps,
                nearest=nearest,
            )

        used = {i for b in blocks for i in b.citation_ids}
        citations = [c for c in citations if c.id in used]
        if any(c.treatment == "overruled" for c in citations):
            notices.append("One or more cited cases have been overruled; see the treatment field.")
        r = vcs.report
        confidence: Confidence = (
            "low"
            if r.conflicts
            else "high"
            if r.mode == "synthesised" and r.verified >= 2
            else "medium"
        )
        answer_id = None
        if profile.history_opt_in:
            answer_id = self.store.save_answer(
                profile_id,
                legal_q,
                (filters or Filters()).model_dump_json(),
                self.cfg.index_version,
                vcs.model_dump_json(),
                r.mode,
                confidence,
            )
        if suggestion := suggest_setting(self.store, profile_id):
            notices.append(suggestion)
        return Response(
            answer_blocks=blocks,
            citations=citations,
            verification=r,
            coverage=self.coverage(),
            confidence=confidence,
            profile_applied=applied,
            notices=notices,
            answer_id=answer_id,
            laws=render_laws(
                self.store,
                citations,
                [legal_q] + [c.claim.text for c in vcs.claims],
                self.cfg.public_url,
            ),
        )

    def chat_case(
        self,
        case_id: str,
        question: str,
        style: dict[str, Any] | None = None,
        profile_id: str = "default",
    ) -> Response:
        if self.store.get_case(case_id) is None:
            raise KeyError(case_id)
        return self.ask(question, Filters(case_id=case_id), style, profile_id)

    # --- search & read --------------------------------------------------------

    def search(
        self, query: str, filters: Filters | None = None, limit: int = 10
    ) -> list[dict[str, Any]]:
        limit = max(1, min(limit, MAX_SEARCH))
        sources, _ = retrieve(self.store, self.cfg, query[:500], filters, Profile())
        out = []
        for s in sources[:limit]:
            case = self.store.get_case(s.chunk.case_id)
            if case:
                out.append(
                    {
                        "case_id": case.id,
                        "title": case.title,
                        "court": case.court,
                        "date": case.date,
                        "citation": case.citation,
                        "paras": f"{s.chunk.para_from}-{s.chunk.para_to}",
                        "snippet": s.chunk.text[:300],
                        "score": s.score,
                        "url": case_url(self.cfg.public_url, case.id, s.chunk.para_from),
                    }
                )
        return out

    def get_case(self, case_id: str) -> dict[str, Any]:
        case = self.store.get_case(case_id)
        if case is None:
            raise KeyError(case_id)
        sections: dict[str, list[int]] = {}
        for p in self.store.get_paragraphs(case_id):
            sections.setdefault(p.section, []).append(p.n)
        return {
            **case.model_dump(),
            "sections": sections,
            "treatment": treatment(self.store, case_id),
            "statutes": [f"{a} {s}" for a, s in self.store.statutes_of(case_id)],
            "laws": [
                law_ref(a, s, self.cfg.public_url).model_dump()
                for a, s in self.store.statutes_of(case_id)
            ],
            "url": case_url(self.cfg.public_url, case_id),
        }

    def list_cases(self) -> list[dict[str, Any]]:
        return [
            {
                "case_id": c.id,
                "title": c.title,
                "court": c.court,
                "date": c.date,
                "citation": c.citation,
                "treatment": treatment(self.store, c.id),
                "url": case_url(self.cfg.public_url, c.id),
            }
            for c in self.store.list_cases()
            if not is_provision(c.id)
        ]

    def get_paragraphs(
        self, case_id: str, start: int, end: int | None = None
    ) -> list[dict[str, Any]]:
        if self.store.get_case(case_id) is None:
            raise KeyError(case_id)
        end = min(end or start, start + MAX_PARAS - 1)
        return [p.model_dump() for p in self.store.get_paragraphs(case_id, start, end)]

    def find_citing_cases(self, case_id: str) -> list[dict[str, Any]]:
        if self.store.get_case(case_id) is None:
            raise KeyError(case_id)
        out = []
        for e in self.store.citing_cases(case_id):
            c = self.store.get_case(e["citing_id"])
            if c:
                out.append(
                    {
                        "case_id": c.id,
                        "title": c.title,
                        "citation": c.citation,
                        "date": c.date,
                        "treatment": e["treatment"],
                        "para": e["para"],
                        "url": case_url(self.cfg.public_url, c.id, e["para"]),
                    }
                )
        return out

    def get_article(self, number: str) -> dict[str, Any]:
        """Official text of a Constitution article. Fetches the Government of India's PDF from
        the internet on first use if it isn't indexed yet."""
        number = number.strip().upper().removeprefix("ARTICLE").strip()
        if self.store.get_case(f"{PREFIX}{number}") is None:
            ingest_constitution(self.store)  # downloads the official PDF, then parses it
        case = self.store.get_case(f"{PREFIX}{number}")
        if case is None:
            raise KeyError(f"Article {number}")
        info = self.lookup_statute("CONST", number)
        return {
            "article": number,
            "title": case.neutral_citation,
            "text": self.store.get_paragraphs(case.id)[0].text,
            "official_url": case.url,
            "source": COI_EDITION,
            "where": info["where"],
            "judgments": [c for c in info["cases"] if not is_provision(c["case_id"])],
        }

    def where(self, number: str) -> str:
        """An Article's place in the official table of contents: "PART III — ... › Right to Freedom"."""
        e = next((e for e in self.store.toc() if e.number == number), None)
        return " › ".join(x for x in (e.part, e.chapter, e.group) if x) if e else ""

    def lookup_statute(self, act: str, section: str) -> dict[str, Any]:
        code = normalise_act(act) or act.upper()
        if code in ("ART", "ARTICLE", "CONSTITUTION"):
            code = "CONST"
        section = section.strip().upper()
        refs = aliases(code, section)
        cases: list[dict[str, Any]] = []
        for a, s in refs:
            for cid in self.store.cases_for_statute(a, s):
                if is_provision(cid):
                    continue  # the article itself is returned as "law", not as a judgment
                c = self.store.get_case(cid)
                para = next(
                    (
                        p.n
                        for p in self.store.get_paragraphs(cid)
                        if extract_statutes_in(p.text, a, s)
                    ),
                    None,
                )
                if c and all(x["case_id"] != cid for x in cases):
                    cases.append(
                        {
                            "case_id": c.id,
                            "title": c.title,
                            "citation": c.citation,
                            "date": c.date,
                            "treatment": treatment(self.store, cid),
                            "url": case_url(self.cfg.public_url, c.id, para),
                        }
                    )
        return {
            "query": f"{code} {section}",
            "equivalents": [f"{a} {s} ({ACT_NAMES.get(a, [a])[0]})" for a, s in refs],
            "cases": cases[:MAX_SEARCH],
            "law": law_ref(code, section, self.cfg.public_url, self.store).model_dump(),
            "where": self.where(section) if code == "CONST" else "",
            "note": "Correspondence table: verify against the official mapping.",
        }

    # --- profile & feedback ------------------------------------------------------

    def get_profile(self, profile_id: str = "default") -> Profile:
        return self.store.get_profile(profile_id)

    def update_profile(self, profile_id: str, changes: dict[str, Any]) -> Profile:
        return update_profile(self.store, profile_id, changes)

    def delete_profile(self, profile_id: str) -> None:
        self.store.delete_profile(profile_id)

    def feedback(
        self, answer_id: int, rating: int, reason: str = "", profile_id: str = "default"
    ) -> dict[str, Any]:
        if rating not in (-1, 1):
            raise ValueError("rating must be 1 or -1")
        self.store.add_feedback(answer_id, profile_id, rating, reason[:200])
        return {"ok": True, "suggestion": suggest_setting(self.store, profile_id)}
