"""Gated outer-loop learning support for Hermes.

Canonical run record source: Hermes gateway/session events are persisted here after a
run completes via :class:`OuterLoopStore.record_run`.  In this hosted template the
admin process only observes gateway stdout, so this module is the append-only local
source of normalized run records until an upstream Hermes session database is wired
in directly.
"""
from __future__ import annotations

import difflib
import hashlib
import json
import re
import sqlite3
import time
import uuid
from contextlib import closing
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Iterable, Literal

EditCategory = Literal[
    "none", "tone change", "missing fact added", "commitment softened",
    "rejection/deletion", "structural rewrite", "other"
]
TargetArea = Literal["memory", "skill", "prompt", "retrieval", "routing"]
ScopeType = Literal["user", "project", "collaborator", "task_type"]


@dataclass(frozen=True)
class RunRecord:
    run_id: str
    timestamp: float
    task_type: str
    prompt: str
    retrieved_context: list[dict[str, Any]] = field(default_factory=list)
    tool_calls: list[dict[str, Any]] = field(default_factory=list)
    draft_output: str = ""
    final_output: str = ""
    human_edit_diff: str = ""
    edit_category: EditCategory = "none"
    status: str = "completed"
    downstream_outcome: str | None = None
    scope_type: ScopeType = "user"
    scope_value: str = "global"

    @classmethod
    def completed(
        cls, *, task_type: str, prompt: str, draft_output: str, final_output: str,
        retrieved_context: list[dict[str, Any]] | None = None,
        tool_calls: list[dict[str, Any]] | None = None,
        downstream_outcome: str | None = None,
        scope_type: ScopeType = "user", scope_value: str = "global",
    ) -> "RunRecord":
        diff = make_unified_diff(draft_output, final_output)
        return cls(
            run_id=str(uuid.uuid4()), timestamp=time.time(), task_type=task_type,
            prompt=prompt, retrieved_context=retrieved_context or [],
            tool_calls=tool_calls or [], draft_output=draft_output,
            final_output=final_output, human_edit_diff=diff,
            edit_category=classify_edit(draft_output, final_output, diff),
            downstream_outcome=downstream_outcome, scope_type=scope_type,
            scope_value=scope_value,
        )


@dataclass(frozen=True)
class CandidateLesson:
    candidate_id: str
    source_run_ids: list[str]
    target_area: TargetArea
    proposed_fix: str
    evidence_summary: str
    confidence_score: float
    rationale: str
    cluster_key: str
    frequency: int
    last_seen: float
    scope_type: ScopeType = "user"
    scope_value: str = "global"
    status: str = "candidate"


@dataclass(frozen=True)
class EvalResult:
    candidate_id: str
    passed: bool
    score: float
    checks: dict[str, bool]
    notes: str = ""


def make_unified_diff(draft: str, final: str) -> str:
    if draft == final:
        return ""
    return "\n".join(difflib.unified_diff(
        draft.splitlines(), final.splitlines(), fromfile="draft", tofile="final", lineterm=""
    ))


def classify_edit(draft: str, final: str, diff: str | None = None) -> EditCategory:
    if draft == final:
        return "none"
    dl, fl = draft.lower(), final.lower()
    if len(final.strip()) < max(12, len(draft.strip()) * 0.35):
        return "rejection/deletion"
    if any(w in fl for w in ["maybe", "might", "could", "likely", "tentatively"]) and any(w in dl for w in ["will", "must", "definitely", "guarantee"]):
        return "commitment softened"
    if len(final) > len(draft) * 1.2 and re.search(r"\b(source|because|according|date|fact|detail|context)\b", fl):
        return "missing fact added"
    if _paragraph_count(draft) != _paragraph_count(final) or abs(len(final) - len(draft)) > max(len(draft), 1) * 0.5:
        return "structural rewrite"
    if any(w in fl for w in ["please", "thanks", "appreciate", "gentle", "soften", "warm"]):
        return "tone change"
    return "other"


def _paragraph_count(text: str) -> int:
    return len([p for p in re.split(r"\n\s*\n", text.strip()) if p])


def _cluster_key(task_type: str, category: str, scope_type: str, scope_value: str) -> str:
    raw = f"{scope_type}:{scope_value}:{task_type}:{category}".lower()
    return hashlib.sha1(raw.encode()).hexdigest()[:16]


class OuterLoopStore:
    def __init__(self, db_path: str | Path):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, isolation_level=None)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with closing(self._connect()) as conn:
            conn.executescript("""
            CREATE TABLE IF NOT EXISTS runs (
              run_id TEXT PRIMARY KEY, timestamp REAL NOT NULL, task_type TEXT NOT NULL,
              prompt TEXT NOT NULL, retrieved_context TEXT NOT NULL, tool_calls TEXT NOT NULL,
              draft_output TEXT NOT NULL, final_output TEXT NOT NULL,
              human_edit_diff TEXT NOT NULL, edit_category TEXT NOT NULL, status TEXT NOT NULL,
              downstream_outcome TEXT, scope_type TEXT NOT NULL, scope_value TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS candidate_lessons (
              candidate_id TEXT PRIMARY KEY, source_run_ids TEXT NOT NULL, target_area TEXT NOT NULL,
              proposed_fix TEXT NOT NULL, evidence_summary TEXT NOT NULL, confidence_score REAL NOT NULL,
              rationale TEXT NOT NULL, cluster_key TEXT NOT NULL UNIQUE, frequency INTEGER NOT NULL,
              last_seen REAL NOT NULL, scope_type TEXT NOT NULL, scope_value TEXT NOT NULL,
              status TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS eval_results (
              candidate_id TEXT PRIMARY KEY, passed INTEGER NOT NULL, score REAL NOT NULL,
              checks TEXT NOT NULL, notes TEXT NOT NULL, evaluated_at REAL NOT NULL
            );
            CREATE TABLE IF NOT EXISTS promoted_lessons (
              lesson_id TEXT PRIMARY KEY, candidate_id TEXT NOT NULL, title TEXT NOT NULL,
              body TEXT NOT NULL, target_area TEXT NOT NULL, scope_type TEXT NOT NULL,
              scope_value TEXT NOT NULL, active INTEGER NOT NULL, version INTEGER NOT NULL,
              promoted_at REAL NOT NULL, deactivated_at REAL
            );
            CREATE TABLE IF NOT EXISTS audit_log (
              id INTEGER PRIMARY KEY AUTOINCREMENT, timestamp REAL NOT NULL, event_type TEXT NOT NULL,
              entity_id TEXT NOT NULL, details TEXT NOT NULL
            );
            """)

    def record_run(self, run: RunRecord) -> None:
        with closing(self._connect()) as conn:
            conn.execute("""INSERT INTO runs VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", (
                run.run_id, run.timestamp, run.task_type, run.prompt,
                json.dumps(run.retrieved_context), json.dumps(run.tool_calls),
                run.draft_output, run.final_output, run.human_edit_diff,
                run.edit_category, run.status, run.downstream_outcome,
                run.scope_type, run.scope_value,
            ))
            self.audit("run_recorded", run.run_id, {"task_type": run.task_type}, conn)

    def get_run(self, run_id: str) -> RunRecord | None:
        with closing(self._connect()) as conn:
            row = conn.execute("SELECT * FROM runs WHERE run_id=?", (run_id,)).fetchone()
        return _row_to_run(row) if row else None

    def recent_completed_runs(self, limit: int = 100) -> list[RunRecord]:
        with closing(self._connect()) as conn:
            rows = conn.execute("SELECT * FROM runs WHERE status='completed' ORDER BY timestamp DESC LIMIT ?", (limit,)).fetchall()
        return [_row_to_run(r) for r in rows]

    def upsert_candidate(self, c: CandidateLesson) -> CandidateLesson:
        with closing(self._connect()) as conn:
            existing = conn.execute("SELECT * FROM candidate_lessons WHERE cluster_key=?", (c.cluster_key,)).fetchone()
            if existing:
                ids = sorted(set(json.loads(existing["source_run_ids"]) + c.source_run_ids))
                c = CandidateLesson(**{**dict(existing), "source_run_ids": ids, "frequency": len(ids), "last_seen": max(existing["last_seen"], c.last_seen), "confidence_score": min(0.99, max(existing["confidence_score"], c.confidence_score))})
                conn.execute("UPDATE candidate_lessons SET source_run_ids=?, frequency=?, last_seen=?, confidence_score=? WHERE candidate_id=?", (json.dumps(ids), c.frequency, c.last_seen, c.confidence_score, c.candidate_id))
            else:
                conn.execute("INSERT INTO candidate_lessons VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)", (c.candidate_id, json.dumps(c.source_run_ids), c.target_area, c.proposed_fix, c.evidence_summary, c.confidence_score, c.rationale, c.cluster_key, c.frequency, c.last_seen, c.scope_type, c.scope_value, c.status))
            self.audit("candidate_generated", c.candidate_id, asdict(c), conn)
        return c

    def list_candidates(self) -> list[CandidateLesson]:
        with closing(self._connect()) as conn:
            rows = conn.execute("SELECT * FROM candidate_lessons ORDER BY last_seen DESC").fetchall()
        return [_row_to_candidate(r) for r in rows]

    def save_eval(self, result: EvalResult) -> None:
        with closing(self._connect()) as conn:
            conn.execute("INSERT OR REPLACE INTO eval_results VALUES (?,?,?,?,?,?)", (result.candidate_id, int(result.passed), result.score, json.dumps(result.checks), result.notes, time.time()))
            self.audit("candidate_evaluated", result.candidate_id, asdict(result), conn)

    def eval_for(self, candidate_id: str) -> EvalResult | None:
        with closing(self._connect()) as conn:
            row = conn.execute("SELECT * FROM eval_results WHERE candidate_id=?", (candidate_id,)).fetchone()
        return EvalResult(row["candidate_id"], bool(row["passed"]), row["score"], json.loads(row["checks"]), row["notes"]) if row else None

    def promote(self, candidate: CandidateLesson, title: str, body: str) -> str:
        result = self.eval_for(candidate.candidate_id)
        if not result or not result.passed or candidate.frequency < 2:
            raise ValueError("candidate must pass eval and have repeated evidence before promotion")
        lesson_id = str(uuid.uuid4())
        with closing(self._connect()) as conn:
            conn.execute("INSERT INTO promoted_lessons VALUES (?,?,?,?,?,?,?,?,?,?,?)", (lesson_id, candidate.candidate_id, title, body, candidate.target_area, candidate.scope_type, candidate.scope_value, 1, 1, time.time(), None))
            conn.execute("UPDATE candidate_lessons SET status='promoted' WHERE candidate_id=?", (candidate.candidate_id,))
            self.audit("lesson_promoted", lesson_id, {"candidate_id": candidate.candidate_id}, conn)
        return lesson_id

    def active_lessons(self, scope_type: ScopeType | None = None, scope_value: str | None = None) -> list[dict[str, Any]]:
        sql = "SELECT * FROM promoted_lessons WHERE active=1"
        args: list[Any] = []
        if scope_type:
            sql += " AND scope_type=?"; args.append(scope_type)
        if scope_value:
            sql += " AND scope_value=?"; args.append(scope_value)
        with closing(self._connect()) as conn:
            return [dict(r) for r in conn.execute(sql, args).fetchall()]

    def rollback(self, lesson_id: str, reason: str) -> None:
        with closing(self._connect()) as conn:
            conn.execute("UPDATE promoted_lessons SET active=0, deactivated_at=? WHERE lesson_id=?", (time.time(), lesson_id))
            self.audit("lesson_rolled_back", lesson_id, {"reason": reason}, conn)

    def audit(self, event_type: str, entity_id: str, details: dict[str, Any], conn: sqlite3.Connection | None = None) -> None:
        def write(c: sqlite3.Connection) -> None:
            c.execute("INSERT INTO audit_log(timestamp,event_type,entity_id,details) VALUES (?,?,?,?)", (time.time(), event_type, entity_id, json.dumps(details, default=str)))
        if conn is None:
            with closing(self._connect()) as owned: write(owned); owned.commit()
        else:
            write(conn)


def generate_candidate_lessons(runs: Iterable[RunRecord], min_frequency: int = 2) -> list[CandidateLesson]:
    groups: dict[str, list[RunRecord]] = {}
    for r in runs:
        if r.edit_category == "none" or not r.human_edit_diff:
            continue
        groups.setdefault(_cluster_key(r.task_type, r.edit_category, r.scope_type, r.scope_value), []).append(r)
    out = []
    for key, items in groups.items():
        if len(items) < min_frequency:
            continue
        first = items[0]
        proposed, target = _lesson_text(first.edit_category, first.task_type)
        out.append(CandidateLesson(
            candidate_id=str(uuid.uuid4()), source_run_ids=[r.run_id for r in items[:3]],
            target_area=target, proposed_fix=proposed,
            evidence_summary=f"{len(items)} recent {first.task_type} runs had {first.edit_category} edits.",
            confidence_score=min(0.95, 0.45 + 0.15 * len(items)),
            rationale="Repeated human edits indicate a reusable correction pattern; hold for eval and review before applying.",
            cluster_key=key, frequency=len(items), last_seen=max(r.timestamp for r in items),
            scope_type=first.scope_type, scope_value=first.scope_value,
        ))
    return out


def _lesson_text(category: str, task_type: str) -> tuple[str, TargetArea]:
    mapping: dict[str, tuple[str, TargetArea]] = {
        "missing fact added": ("Before finalizing, retrieve or cite the source of truth for task-specific factual claims.", "retrieval"),
        "commitment softened": ("Avoid unsupported commitments; use qualified language unless the source of truth confirms certainty.", "prompt"),
        "tone change": ("Match the user's preferred tone for this scope before drafting the final response.", "memory"),
        "structural rewrite": ("Follow the established structure for this task type before producing the final answer.", "skill"),
        "rejection/deletion": ("Do not repeat the rejected response pattern for this task type without new evidence.", "routing"),
    }
    return mapping.get(category, (f"Review prior corrections before handling {task_type} tasks.", "memory"))


def run_replay_eval(candidate: CandidateLesson, replay_runs: Iterable[RunRecord]) -> EvalResult:
    runs = list(replay_runs)
    checks = {
        "has_repeated_evidence": candidate.frequency >= 2,
        "has_source_runs": bool(candidate.source_run_ids),
        "not_one_off": len(set(candidate.source_run_ids)) >= 2,
        "scope_is_explicit": bool(candidate.scope_type and candidate.scope_value),
        "no_conflict_marker": "conflict" not in candidate.proposed_fix.lower(),
    }
    score = sum(checks.values()) / len(checks)
    return EvalResult(candidate.candidate_id, score >= 0.8, score, checks, f"Evaluated against {len(runs)} replay runs.")


def write_agteo_brain_note(base_dir: str | Path, candidate: CandidateLesson, lesson_id: str) -> Path:
    safe = re.sub(r"[^a-z0-9]+", "-", candidate.proposed_fix.lower()).strip("-")[:64] or lesson_id
    path = Path(base_dir) / "outer-loop-lessons" / f"{safe}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        f"# {candidate.proposed_fix}\n\n"
        f"## Why it changed\n{candidate.rationale}\n\n"
        f"## Evidence\n{candidate.evidence_summary}\n\n"
        f"## When to use\nScope: `{candidate.scope_type}:{candidate.scope_value}`. Target area: `{candidate.target_area}`.\n\n"
        f"## When not to use\nDo not apply outside the stated scope or when it conflicts with higher-priority canonical rules.\n\n"
        f"## Linked runs\n" + "\n".join(f"- `{rid}`" for rid in candidate.source_run_ids) + "\n",
        encoding="utf-8",
    )
    return path


def _row_to_run(row: sqlite3.Row) -> RunRecord:
    d = dict(row); d["retrieved_context"] = json.loads(d["retrieved_context"]); d["tool_calls"] = json.loads(d["tool_calls"]); return RunRecord(**d)

def _row_to_candidate(row: sqlite3.Row) -> CandidateLesson:
    d = dict(row); d["source_run_ids"] = json.loads(d["source_run_ids"]); return CandidateLesson(**d)


class OuterLoopWorker:
    def __init__(self, store: OuterLoopStore, batch_size: int = 100, min_frequency: int = 2):
        self.store = store; self.batch_size = batch_size; self.min_frequency = min_frequency

    def run_once(self) -> list[CandidateLesson]:
        candidates = generate_candidate_lessons(self.store.recent_completed_runs(self.batch_size), self.min_frequency)
        return [self.store.upsert_candidate(c) for c in candidates]
