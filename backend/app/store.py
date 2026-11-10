"""SQLite persistence: lectures, question bank, sessions and evaluation logs.

Lectures and sessions are stored as JSON documents, which keeps the MVP schema
small. The interface is the seam for moving to PostgreSQL later: nothing
outside this file runs SQL.
"""

from __future__ import annotations

import sqlite3
import threading
from collections import defaultdict
from contextlib import contextmanager
from pathlib import Path

from app.models import Lecture, QuestionItem, Session, now_iso

_SCHEMA = """
CREATE TABLE IF NOT EXISTS lectures (id TEXT PRIMARY KEY, data TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS questions (
    id TEXT PRIMARY KEY, lecture_id TEXT NOT NULL, concept_id TEXT NOT NULL, data TEXT NOT NULL);
CREATE INDEX IF NOT EXISTS questions_by_concept ON questions (lecture_id, concept_id);
CREATE TABLE IF NOT EXISTS sessions (id TEXT PRIMARY KEY, lecture_id TEXT NOT NULL, data TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS answer_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT, session_id TEXT NOT NULL, lecture_id TEXT NOT NULL,
    question_id TEXT NOT NULL, concept_id TEXT NOT NULL, question_type TEXT NOT NULL,
    correct INTEGER NOT NULL, p_before REAL, p_after REAL NOT NULL, next_action TEXT NOT NULL,
    latency_ms INTEGER NOT NULL, created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS llm_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT, scope_id TEXT NOT NULL, purpose TEXT NOT NULL,
    ok INTEGER NOT NULL, latency_ms INTEGER NOT NULL, prompt_chars INTEGER NOT NULL,
    reply_chars INTEGER NOT NULL, created_at TEXT NOT NULL);
"""


class Store:
    def __init__(self, path: Path | str):
        self.path = str(path)
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        self._local = threading.local()
        self._locks: dict[str, threading.Lock] = defaultdict(threading.Lock)
        self._locks_guard = threading.Lock()
        with self._tx() as db:
            db.executescript(_SCHEMA)

    def _conn(self) -> sqlite3.Connection:
        conn = getattr(self._local, "conn", None)
        if conn is None:
            conn = sqlite3.connect(self.path, timeout=30)
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA journal_mode=WAL")
            self._local.conn = conn
        return conn

    @contextmanager
    def _tx(self):
        conn = self._conn()
        with conn:  # commits, or rolls back on error
            yield conn

    def lock(self, key: str) -> threading.Lock:
        """One lock per session id: an answer is a read-modify-write of the whole session."""
        with self._locks_guard:
            return self._locks[key]

    # ---------- lectures ----------

    def save_lecture(self, lecture: Lecture) -> None:
        with self._tx() as db:
            db.execute(
                "INSERT INTO lectures (id, data) VALUES (?, ?) "
                "ON CONFLICT(id) DO UPDATE SET data = excluded.data",
                (lecture.id, lecture.model_dump_json()),
            )

    def get_lecture(self, lecture_id: str) -> Lecture | None:
        row = self._conn().execute("SELECT data FROM lectures WHERE id = ?", (lecture_id,)).fetchone()
        return Lecture.model_validate_json(row["data"]) if row else None

    # ---------- question bank ----------

    def add_questions(self, lecture_id: str, items: list[QuestionItem]) -> None:
        with self._tx() as db:
            db.executemany(
                "INSERT OR IGNORE INTO questions (id, lecture_id, concept_id, data) VALUES (?, ?, ?, ?)",
                [(q.id, lecture_id, q.concept_id, q.model_dump_json()) for q in items],
            )

    def list_questions(self, lecture_id: str, concept_id: str | None = None) -> list[QuestionItem]:
        sql, args = "SELECT data FROM questions WHERE lecture_id = ?", [lecture_id]
        if concept_id is not None:
            sql += " AND concept_id = ?"
            args.append(concept_id)
        rows = self._conn().execute(sql + " ORDER BY rowid", args).fetchall()
        return [QuestionItem.model_validate_json(r["data"]) for r in rows]

    # ---------- sessions ----------

    def save_session(self, session: Session) -> None:
        with self._tx() as db:
            db.execute(
                "INSERT INTO sessions (id, lecture_id, data) VALUES (?, ?, ?) "
                "ON CONFLICT(id) DO UPDATE SET data = excluded.data",
                (session.id, session.lecture_id, session.model_dump_json()),
            )

    def get_session(self, session_id: str) -> Session | None:
        row = self._conn().execute("SELECT data FROM sessions WHERE id = ?", (session_id,)).fetchone()
        return Session.model_validate_json(row["data"]) if row else None

    # ---------- evaluation logs ----------

    def log_answer(self, **row) -> None:
        row["created_at"] = now_iso()
        cols = ", ".join(row)
        marks = ", ".join("?" for _ in row)
        with self._tx() as db:
            db.execute(f"INSERT INTO answer_log ({cols}) VALUES ({marks})", list(row.values()))

    def list_answers(self, session_id: str) -> list[dict]:
        rows = (
            self._conn()
            .execute("SELECT * FROM answer_log WHERE session_id = ? ORDER BY id", (session_id,))
            .fetchall()
        )
        return [dict(r) | {"correct": bool(r["correct"])} for r in rows]

    def log_llm(
        self, scope_id: str, purpose: str, ok: bool, latency_ms: int, prompt_chars: int, reply_chars: int
    ):
        with self._tx() as db:
            db.execute(
                "INSERT INTO llm_log "
                "(scope_id, purpose, ok, latency_ms, prompt_chars, reply_chars, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (scope_id, purpose, int(ok), latency_ms, prompt_chars, reply_chars, now_iso()),
            )

    def llm_usage(self, scope_id: str) -> dict:
        """Calls, latency and size per purpose for one lecture or session (cost estimate input)."""
        rows = (
            self._conn()
            .execute(
                "SELECT purpose, COUNT(*) AS calls, SUM(ok) AS ok, SUM(latency_ms) AS latency_ms, "
                "SUM(prompt_chars) AS prompt_chars, SUM(reply_chars) AS reply_chars "
                "FROM llm_log WHERE scope_id = ? GROUP BY purpose",
                (scope_id,),
            )
            .fetchall()
        )
        return {r["purpose"]: {k: r[k] for k in r.keys() if k != "purpose"} for r in rows}
