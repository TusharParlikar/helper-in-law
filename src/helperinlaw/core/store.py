"""SQLite storage: cases, paragraphs, chunks (+FTS5 for BM25), embeddings, citation graph,
profiles, answers, feedback.

ponytail: SQLite + FTS5 + brute-force vectors stand in for Postgres + Qdrant in single-user
Phase 1. Move to Postgres/Qdrant when the corpus outgrows one process (~100k chunks).
"""

import json
import sqlite3
import struct
from collections.abc import Iterable
from pathlib import Path
from typing import Any

from helperinlaw.core.types import Case, Chunk, Paragraph, Profile

SCHEMA = """
CREATE TABLE IF NOT EXISTS cases (
    id TEXT PRIMARY KEY, title TEXT, court TEXT, date TEXT, bench TEXT, case_no TEXT,
    citation TEXT, neutral_citation TEXT, url TEXT, pdf_sha256 TEXT UNIQUE
);
CREATE TABLE IF NOT EXISTS paragraphs (
    case_id TEXT, n INTEGER, text TEXT, section TEXT, PRIMARY KEY (case_id, n)
);
CREATE TABLE IF NOT EXISTS statutes (case_id TEXT, act TEXT, section TEXT);
CREATE INDEX IF NOT EXISTS statutes_idx ON statutes(act, section);
CREATE TABLE IF NOT EXISTS citations (
    citing_id TEXT, cited_id TEXT, treatment TEXT, para INTEGER
);
CREATE INDEX IF NOT EXISTS citations_cited ON citations(cited_id);
CREATE TABLE IF NOT EXISTS chunks (
    id TEXT, index_version TEXT, case_id TEXT, para_from INTEGER, para_to INTEGER,
    text TEXT, prefix TEXT, PRIMARY KEY (id, index_version)
);
CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts USING fts5(
    text, chunk_id UNINDEXED, index_version UNINDEXED, tokenize = 'porter unicode61'
);
CREATE TABLE IF NOT EXISTS embeddings (
    chunk_id TEXT, index_version TEXT, vec BLOB, PRIMARY KEY (chunk_id, index_version)
);
CREATE TABLE IF NOT EXISTS dead_letter (path TEXT, reason TEXT, at TEXT DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS user_profiles (
    profile_id TEXT PRIMARY KEY, profile_json TEXT, version INTEGER,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS answers (
    id INTEGER PRIMARY KEY, profile_id TEXT, question TEXT, filters TEXT, index_version TEXT,
    claim_set_json TEXT, mode TEXT, confidence TEXT, created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS feedback (
    answer_id INTEGER, profile_id TEXT, rating INTEGER, reason TEXT,
    at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS eval_runs (
    id INTEGER PRIMARY KEY, git_sha TEXT, dataset TEXT, metrics_json TEXT,
    at TEXT DEFAULT CURRENT_TIMESTAMP
);
"""


def pack(vec: list[float]) -> bytes:
    return struct.pack(f"{len(vec)}f", *vec)


def unpack(blob: bytes) -> list[float]:
    return list(struct.unpack(f"{len(blob) // 4}f", blob))


class Store:
    def __init__(self, path: str | Path) -> None:
        if str(path) != ":memory:":
            Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(str(path), check_same_thread=False)
        self.db.row_factory = sqlite3.Row
        self.db.executescript(SCHEMA)

    # --- cases & paragraphs ---------------------------------------------

    def has_sha(self, sha: str) -> bool:
        return self.db.execute("SELECT 1 FROM cases WHERE pdf_sha256=?", (sha,)).fetchone() is not None

    def add_case(self, case: Case, paras: list[Paragraph]) -> None:
        with self.db:
            self.db.execute(
                "INSERT OR REPLACE INTO cases VALUES (?,?,?,?,?,?,?,?,?,?)",
                (case.id, case.title, case.court, case.date, json.dumps(case.bench), case.case_no,
                 case.citation, case.neutral_citation, case.url, case.pdf_sha256),
            )
            self.db.execute("DELETE FROM paragraphs WHERE case_id=?", (case.id,))
            self.db.executemany(
                "INSERT INTO paragraphs VALUES (?,?,?,?)",
                [(p.case_id, p.n, p.text, p.section) for p in paras],
            )

    def _case(self, row: sqlite3.Row) -> Case:
        d = dict(row)
        d["bench"] = json.loads(d["bench"] or "[]")
        return Case(**d)

    def get_case(self, case_id: str) -> Case | None:
        row = self.db.execute("SELECT * FROM cases WHERE id=?", (case_id,)).fetchone()
        return self._case(row) if row else None

    def list_cases(self) -> list[Case]:
        return [self._case(r) for r in self.db.execute("SELECT * FROM cases ORDER BY date")]

    def get_paragraphs(self, case_id: str, n_from: int = 0, n_to: int = 10**9) -> list[Paragraph]:
        rows = self.db.execute(
            "SELECT * FROM paragraphs WHERE case_id=? AND n BETWEEN ? AND ? ORDER BY n",
            (case_id, n_from, n_to),
        )
        return [Paragraph(**dict(r)) for r in rows]

    # --- statutes & citation graph ----------------------------------------

    def add_statutes(self, case_id: str, refs: Iterable[tuple[str, str]]) -> None:
        with self.db:
            self.db.execute("DELETE FROM statutes WHERE case_id=?", (case_id,))
            self.db.executemany(
                "INSERT INTO statutes VALUES (?,?,?)", [(case_id, a, s) for a, s in set(refs)]
            )

    def cases_for_statute(self, act: str, section: str) -> list[str]:
        rows = self.db.execute(
            "SELECT DISTINCT case_id FROM statutes WHERE act=? AND section=?", (act, section)
        )
        return [r[0] for r in rows]

    def statutes_of(self, case_id: str) -> list[tuple[str, str]]:
        rows = self.db.execute("SELECT act, section FROM statutes WHERE case_id=?", (case_id,))
        return [(r[0], r[1]) for r in rows]

    def add_citations(self, citing_id: str, edges: Iterable[tuple[str, str, int]]) -> None:
        with self.db:
            self.db.execute("DELETE FROM citations WHERE citing_id=?", (citing_id,))
            self.db.executemany(
                "INSERT INTO citations VALUES (?,?,?,?)",
                [(citing_id, cited, t, para) for cited, t, para in edges],
            )

    def citing_cases(self, cited_id: str) -> list[dict[str, Any]]:
        rows = self.db.execute(
            "SELECT citing_id, treatment, para FROM citations WHERE cited_id=? ORDER BY citing_id",
            (cited_id,),
        )
        return [dict(r) for r in rows]

    def resolve_citation(self, text: str) -> str | None:
        """Map a reporter or neutral citation string to a case id in the corpus."""
        row = self.db.execute(
            "SELECT id FROM cases WHERE citation=? OR neutral_citation=?", (text, text)
        ).fetchone()
        return row[0] if row else None

    # --- chunks, FTS, embeddings ------------------------------------------

    def replace_chunks(self, index_version: str, chunks: list[Chunk]) -> None:
        with self.db:
            self.db.execute("DELETE FROM chunks WHERE index_version=?", (index_version,))
            self.db.execute("DELETE FROM chunks_fts WHERE index_version=?", (index_version,))
            self.db.executemany(
                "INSERT INTO chunks VALUES (?,?,?,?,?,?,?)",
                [(c.id, index_version, c.case_id, c.para_from, c.para_to, c.text, c.prefix)
                 for c in chunks],
            )
            self.db.executemany(
                "INSERT INTO chunks_fts (text, chunk_id, index_version) VALUES (?,?,?)",
                [(c.prefix + "\n" + c.text, c.id, index_version) for c in chunks],
            )

    def get_chunk(self, index_version: str, chunk_id: str) -> Chunk | None:
        row = self.db.execute(
            "SELECT id, case_id, para_from, para_to, text, prefix FROM chunks "
            "WHERE index_version=? AND id=?", (index_version, chunk_id)
        ).fetchone()
        return Chunk(**dict(row)) if row else None

    def all_chunks(self, index_version: str) -> list[Chunk]:
        rows = self.db.execute(
            "SELECT id, case_id, para_from, para_to, text, prefix FROM chunks WHERE index_version=?",
            (index_version,),
        )
        return [Chunk(**dict(r)) for r in rows]

    def bm25(self, index_version: str, match: str, limit: int) -> list[tuple[str, float]]:
        rows = self.db.execute(
            "SELECT chunk_id, bm25(chunks_fts) AS s FROM chunks_fts "
            "WHERE chunks_fts MATCH ? AND index_version=? ORDER BY s LIMIT ?",
            (match, index_version, limit),
        )
        return [(r[0], -r[1]) for r in rows]  # FTS5 bm25 is lower-is-better

    def put_embeddings(self, index_version: str, items: list[tuple[str, list[float]]]) -> None:
        with self.db:
            self.db.executemany(
                "INSERT OR REPLACE INTO embeddings VALUES (?,?,?)",
                [(cid, index_version, pack(v)) for cid, v in items],
            )

    def embedded_ids(self, index_version: str) -> set[str]:
        rows = self.db.execute(
            "SELECT chunk_id FROM embeddings WHERE index_version=?", (index_version,)
        )
        return {r[0] for r in rows}

    def all_embeddings(self, index_version: str) -> list[tuple[str, list[float]]]:
        rows = self.db.execute(
            "SELECT chunk_id, vec FROM embeddings WHERE index_version=?", (index_version,)
        )
        return [(r[0], unpack(r[1])) for r in rows]

    # --- ops ------------------------------------------------------------------

    def dead_letter(self, path: str, reason: str) -> None:
        with self.db:
            self.db.execute("INSERT INTO dead_letter (path, reason) VALUES (?,?)", (path, reason))

    def dead_letters(self) -> list[dict[str, Any]]:
        return [dict(r) for r in self.db.execute("SELECT * FROM dead_letter")]

    # --- profiles, answers, feedback ----------------------------------------

    def get_profile(self, profile_id: str) -> Profile:
        row = self.db.execute(
            "SELECT profile_json FROM user_profiles WHERE profile_id=?", (profile_id,)
        ).fetchone()
        return Profile.model_validate_json(row[0]) if row else Profile(profile_id=profile_id)

    def put_profile(self, profile: Profile) -> None:
        with self.db:
            self.db.execute(
                "INSERT OR REPLACE INTO user_profiles (profile_id, profile_json, version) "
                "VALUES (?,?,?)",
                (profile.profile_id, profile.model_dump_json(), profile.version),
            )

    def delete_profile(self, profile_id: str) -> None:
        with self.db:
            for table in ("user_profiles", "answers", "feedback"):
                self.db.execute(f"DELETE FROM {table} WHERE profile_id=?", (profile_id,))

    def save_answer(self, profile_id: str, question: str, filters: str, index_version: str,
                    claim_set_json: str, mode: str, confidence: str) -> int:
        with self.db:
            cur = self.db.execute(
                "INSERT INTO answers (profile_id, question, filters, index_version, claim_set_json,"
                " mode, confidence) VALUES (?,?,?,?,?,?,?)",
                (profile_id, question, filters, index_version, claim_set_json, mode, confidence),
            )
        return int(cur.lastrowid or 0)

    def count_answers(self, profile_id: str) -> int:
        row = self.db.execute("SELECT COUNT(*) FROM answers WHERE profile_id=?", (profile_id,))
        return int(row.fetchone()[0])

    def add_feedback(self, answer_id: int, profile_id: str, rating: int, reason: str) -> None:
        with self.db:
            self.db.execute(
                "INSERT INTO feedback (answer_id, profile_id, rating, reason) VALUES (?,?,?,?)",
                (answer_id, profile_id, rating, reason),
            )

    def recent_feedback(self, profile_id: str, limit: int = 10) -> list[dict[str, Any]]:
        rows = self.db.execute(
            "SELECT * FROM feedback WHERE profile_id=? ORDER BY rowid DESC LIMIT ?",
            (profile_id, limit),
        )
        return [dict(r) for r in rows]

    def save_eval_run(self, git_sha: str, dataset: str, metrics: dict[str, Any]) -> None:
        with self.db:
            self.db.execute(
                "INSERT INTO eval_runs (git_sha, dataset, metrics_json) VALUES (?,?,?)",
                (git_sha, dataset, json.dumps(metrics)),
            )
