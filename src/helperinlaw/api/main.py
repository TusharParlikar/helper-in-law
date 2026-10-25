"""FastAPI adapter. Phase 1: no auth, single user, binds to 127.0.0.1. Do not expose publicly."""

from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from helperinlaw.core.types import Filters, Profile, Response
from helperinlaw.service import Service

app = FastAPI(title="Helper in Law", version="0.1.0",
              description="Citation-first research over Indian court judgments. Not legal advice.")
_service: Service | None = None


def svc() -> Service:
    global _service
    if _service is None:
        _service = Service()
    return _service


def set_service(s: Service) -> None:
    global _service
    _service = s


@app.exception_handler(KeyError)
async def not_found(_: Request, e: KeyError) -> JSONResponse:
    return JSONResponse(status_code=404, content={"detail": f"not found: {e.args[0]}"})


@app.exception_handler(ValueError)
async def bad_request(_: Request, e: ValueError) -> JSONResponse:
    return JSONResponse(status_code=422, content={"detail": str(e)})


class AskIn(BaseModel):
    question: str = Field(min_length=3, max_length=2000)
    filters: Filters | None = None
    style: dict[str, Any] | None = None
    profile_id: str = "default"


class SearchIn(BaseModel):
    query: str = Field(min_length=2, max_length=500)
    filters: Filters | None = None
    limit: int = Field(10, ge=1, le=20)


class ChatIn(BaseModel):
    question: str = Field(min_length=3, max_length=2000)
    style: dict[str, Any] | None = None
    profile_id: str = "default"


class FeedbackIn(BaseModel):
    answer_id: int
    rating: int
    reason: str = ""
    profile_id: str = "default"


@app.post("/ask")
def ask(body: AskIn) -> Response:
    return svc().ask(body.question, body.filters, body.style, body.profile_id)


@app.post("/search")
def search(body: SearchIn) -> list[dict[str, Any]]:
    return svc().search(body.query, body.filters, body.limit)


@app.get("/cases/{case_id}")
def get_case(case_id: str) -> dict[str, Any]:
    return svc().get_case(case_id)


@app.get("/cases/{case_id}/paragraphs/{n}")
def get_paragraph(case_id: str, n: int, to: int | None = None) -> list[dict[str, Any]]:
    paras = svc().get_paragraphs(case_id, n, to)
    if not paras:
        raise HTTPException(404, f"paragraph {n} not found")
    return paras


@app.get("/cases/{case_id}/citing")
def citing(case_id: str) -> list[dict[str, Any]]:
    return svc().find_citing_cases(case_id)


@app.post("/cases/{case_id}/chat")
def chat(case_id: str, body: ChatIn) -> Response:
    return svc().chat_case(case_id, body.question, body.style, body.profile_id)


@app.get("/statutes/{act}/{section}")
def statute(act: str, section: str) -> dict[str, Any]:
    return svc().lookup_statute(act, section)


@app.get("/profile")
def get_profile(profile_id: str = "default") -> Profile:
    return svc().get_profile(profile_id)


@app.put("/profile")
def put_profile(changes: dict[str, Any], profile_id: str = "default") -> Profile:
    return svc().update_profile(profile_id, changes)


@app.delete("/profile")
def delete_profile(profile_id: str = "default") -> dict[str, bool]:
    svc().delete_profile(profile_id)
    return {"deleted": True}


@app.post("/feedback")
def feedback(body: FeedbackIn) -> dict[str, Any]:
    return svc().feedback(body.answer_id, body.rating, body.reason, body.profile_id)


@app.get("/health")
def health() -> dict[str, Any]:
    return {"ok": True, "cases": len(svc().store.list_cases()), "index": svc().cfg.index_version}
