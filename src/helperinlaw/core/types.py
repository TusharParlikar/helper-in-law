"""Shared schemas. The claim schema (roadmap §4.2) and response model (§4.3) live here;
everything else hangs off them."""

from typing import Literal

from pydantic import BaseModel, Field, model_validator

ClaimType = Literal["holding", "ratio", "obiter", "fact", "statute", "procedural"]
Stance = Literal["supports", "contrary", "neutral"]
Treatment = Literal["good law", "followed", "distinguished", "overruled", "unknown"]
Confidence = Literal["high", "medium", "low", "not_found"]


# --- corpus ---------------------------------------------------------------


class Case(BaseModel):
    id: str
    title: str
    court: str = ""
    date: str = ""  # ISO YYYY-MM-DD
    bench: list[str] = []
    case_no: str = ""
    citation: str = ""
    neutral_citation: str = ""
    url: str = ""
    pdf_sha256: str = ""

    @property
    def year(self) -> int:
        return int(self.date[:4]) if self.date[:4].isdigit() else 0


class Paragraph(BaseModel):
    case_id: str
    n: int
    text: str
    section: str = "reasoning"


class Chunk(BaseModel):
    id: str
    case_id: str
    para_from: int
    para_to: int
    text: str
    prefix: str = ""


class Source(BaseModel):
    """A retrieved passage, shown to the LLM as [S1], [S2]..."""

    id: str
    chunk: Chunk
    score: float = 0.0


# --- LLM claim output (§4.2) ----------------------------------------------


class SupportRef(BaseModel):
    source_id: str
    quote: str = Field(min_length=1)


class Claim(BaseModel):
    text: str = Field(min_length=1)
    support: list[SupportRef] = Field(min_length=1)  # G2: no support -> rejected at parse
    type: ClaimType = "holding"
    stance: Stance = "supports"


class ClaimSet(BaseModel):
    claims: list[Claim] = []
    abstain: bool = False
    gaps: list[str] = []


class VerifiedRef(BaseModel):
    case_id: str
    para: int  # the paragraph the quote was found in, located by the verifier, not the LLM
    quote: str


class VerifiedClaim(BaseModel):
    id: str  # c1, c2...
    claim: Claim
    refs: list[VerifiedRef] = Field(min_length=1)


class VerificationReport(BaseModel):
    claims_proposed: int = 0
    verified: int = 0
    dropped: int = 0
    mode: Literal["synthesised", "extractive", "abstained"] = "synthesised"
    drop_reasons: dict[str, int] = {}
    conflicts: list[str] = []


class VerifiedClaimSet(BaseModel):
    """Stage A output. Style-independent and cacheable."""

    question: str
    claims: list[VerifiedClaim] = []
    report: VerificationReport = VerificationReport()
    gaps: list[str] = []
    nearest: list[str] = []  # case ids offered when abstaining


# --- response (§4.3) -------------------------------------------------------


class AnswerBlock(BaseModel):
    text: str
    citation_ids: list[str] = Field(min_length=1)  # no block renders without a citation


class Citation(BaseModel):
    id: str
    case_id: str
    case_title: str
    court: str
    date: str
    citation: str
    neutral_citation: str
    para: str
    quote: str
    url: str = ""
    treatment: Treatment = "unknown"


class Coverage(BaseModel):
    corpus: str
    as_of: str
    limits: list[str]


DISCLAIMER = "Research aid, not legal advice."
LIMITS = [
    "Completeness: retrieval may miss a relevant case.",
    "Currency: a cited case may have been overruled after the corpus date.",
    "Interpretation: a faithful paraphrase can still be a wrong reading of the law.",
]


class Response(BaseModel):
    answer_blocks: list[AnswerBlock]
    citations: list[Citation]
    verification: VerificationReport
    coverage: Coverage
    confidence: Confidence
    profile_applied: dict[str, str] = {}
    notices: list[str] = []
    nearest: list[str] = []  # case titles offered when not found
    answer_id: int | None = None  # set only when history is on
    disclaimer: str = DISCLAIMER

    @model_validator(mode="after")
    def _grounded(self) -> "Response":
        ids = {c.id for c in self.citations}
        for block in self.answer_blocks:
            missing = set(block.citation_ids) - ids
            if missing:
                raise ValueError(f"answer block cites unknown citations {missing}")
        if self.confidence != "not_found" and not self.answer_blocks:
            raise ValueError("an answer needs at least one cited block")
        if self.disclaimer != DISCLAIMER:
            raise ValueError("disclaimer is not configurable")
        return self


# --- user profile (§5.3) ---------------------------------------------------


class Profile(BaseModel):
    profile_id: str = "default"
    role: Literal["advocate", "student", "researcher", "counsel", "general"] = "advocate"
    depth: Literal["quick", "standard", "deep"] = "standard"
    structure: Literal["bullets", "paragraphs", "irac", "memo", "table"] = "bullets"
    tone: Literal["technical", "plain", "new"] = "technical"
    answer_language: Literal["en", "hi"] = "en"
    citation_style: Literal["case_name", "neutral", "inline_para", "footnotes"] = "case_name"
    quotes: Literal["always", "hover", "on_request"] = "always"
    contrary_authority: Literal["always", "if_found", "never"] = "always"
    obiter: Literal["highlight", "hide", "ignore"] = "highlight"
    jurisdiction: list[str] = []
    recency: Literal["newest", "landmark", "balanced"] = "balanced"
    max_words: int | None = None
    suggest_followups: bool = True
    history_opt_in: bool = False
    version: int = 1


STYLE_FIELDS = set(Profile.model_fields) - {"profile_id", "version"}


class Filters(BaseModel):
    court: str | None = None
    year_from: int | None = None
    year_to: int | None = None
    statute: str | None = None
    case_id: str | None = None  # chat-with-a-judgment scope
