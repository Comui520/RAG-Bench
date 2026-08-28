"""SQLite database operations for the evaluation platform."""

import sqlite3
import uuid
import json
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any

_db_path: Optional[str] = None
_db: Optional[sqlite3.Connection] = None

VALID_STATUSES = frozenset({
    "UPLOADING",
    "GENERATING_GOLDENS",
    "AWAITING_CONFIRM",
    "RUNNING_EVAL",
    "COMPLETED",
    "FAILED",
})

TERMINAL_STATUSES = frozenset({"COMPLETED", "FAILED"})


def get_db_path() -> str:
    global _db_path
    if _db_path is not None:
        return _db_path
    from app.config import DATABASE_URL
    _db_path = DATABASE_URL
    return _db_path


def get_db() -> sqlite3.Connection:
    global _db
    if _db is not None:
        return _db
    _db = sqlite3.connect(get_db_path())
    _db.row_factory = sqlite3.Row
    _db.execute("PRAGMA journal_mode=WAL")
    _db.execute("PRAGMA foreign_keys=ON")
    return _db


def init_db(db_path: Optional[str] = None) -> sqlite3.Connection:
    global _db, _db_path
    if db_path is not None:
        _db_path = db_path
    conn = get_db()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS tasks (
            id            TEXT PRIMARY KEY,
            task_name     TEXT,
            rag_base_url  TEXT NOT NULL,
            rag_api_key   TEXT NOT NULL,
            status        TEXT NOT NULL DEFAULT 'UPLOADING',
            error_message TEXT,
            created_at    TEXT NOT NULL,
            completed_at  TEXT
        );

        CREATE TABLE IF NOT EXISTS task_documents (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            task_id   TEXT NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
            filename  TEXT NOT NULL,
            file_path TEXT NOT NULL,
            file_size INTEGER NOT NULL DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS goldens (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            task_id         TEXT NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
            input           TEXT NOT NULL,
            expected_output TEXT NOT NULL,
            context         TEXT
        );

        CREATE TABLE IF NOT EXISTS eval_results (
            id                INTEGER PRIMARY KEY AUTOINCREMENT,
            task_id           TEXT NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
            golden_id         INTEGER NOT NULL REFERENCES goldens(id) ON DELETE CASCADE,
            actual_output     TEXT NOT NULL,
            retrieval_context TEXT,
            metrics_json      TEXT NOT NULL,
            passed            INTEGER NOT NULL DEFAULT 0,
            evaluated_at      TEXT NOT NULL
        );
    """)
    # Existing rag_eval.db files predate task_name. Keep them usable without
    # requiring a destructive migration.
    columns = {row[1] for row in conn.execute("PRAGMA table_info(tasks)").fetchall()}
    if "task_name" not in columns:
        conn.execute("ALTER TABLE tasks ADD COLUMN task_name TEXT")
    conn.commit()
    return conn


def create_task(
    rag_base_url: str,
    rag_api_key: str,
    task_id: Optional[str] = None,
    task_name: Optional[str] = None,
) -> str:
    if task_id is None:
        task_id = uuid.uuid4().hex
    now = datetime.now(timezone.utc).isoformat()
    get_db().execute(
        "INSERT OR IGNORE INTO tasks (id, task_name, rag_base_url, rag_api_key, status, created_at) VALUES (?, ?, ?, ?, 'UPLOADING', ?)",
        (task_id, task_name, rag_base_url, rag_api_key, now),
    )
    get_db().commit()
    return task_id


def set_task_name(task_id: str, task_name: Optional[str]) -> bool:
    """Set an optional user-facing task name."""
    cur = get_db().execute(
        "UPDATE tasks SET task_name = ? WHERE id = ?",
        ((task_name or "").strip() or None, task_id),
    )
    get_db().commit()
    return cur.rowcount > 0


def get_task(task_id: str) -> Optional[Dict[str, Any]]:
    row = get_db().execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
    if row is None:
        return None
    return dict(row)


def update_task_status(
    task_id: str,
    new_status: str,
    error_message: Optional[str] = None,
) -> None:
    if new_status not in VALID_STATUSES:
        raise ValueError(f"Invalid status: {new_status}")

    current = get_task(task_id)
    if current is None:
        raise ValueError(f"Task not found: {task_id}")

    if current["status"] in TERMINAL_STATUSES:
        raise ValueError(
            f"Cannot transition from {current['status']} to {new_status}"
        )

    now = datetime.now(timezone.utc).isoformat()
    if new_status in TERMINAL_STATUSES:
        get_db().execute(
            "UPDATE tasks SET status = ?, error_message = ?, completed_at = ? WHERE id = ?",
            (new_status, error_message, now, task_id),
        )
    else:
        get_db().execute(
            "UPDATE tasks SET status = ?, error_message = ? WHERE id = ?",
            (new_status, error_message, task_id),
        )
    get_db().commit()


def delete_task(task_id: str) -> bool:
    """Delete a task and all database children via foreign-key cascades."""
    cur = get_db().execute("DELETE FROM tasks WHERE id = ?", (task_id,))
    get_db().commit()
    return cur.rowcount > 0


def get_all_tasks() -> List[Dict[str, Any]]:
    rows = get_db().execute(
        "SELECT * FROM tasks ORDER BY created_at DESC"
    ).fetchall()
    return [dict(r) for r in rows]


def add_document(task_id: str, filename: str, file_path: str, file_size: int) -> int:
    cur = get_db().execute(
        "INSERT INTO task_documents (task_id, filename, file_path, file_size) VALUES (?, ?, ?, ?)",
        (task_id, filename, file_path, file_size),
    )
    get_db().commit()
    return cur.lastrowid


def get_documents(task_id: str) -> List[Dict[str, Any]]:
    rows = get_db().execute(
        "SELECT * FROM task_documents WHERE task_id = ?", (task_id,)
    ).fetchall()
    return [dict(r) for r in rows]


def add_golden(task_id: str, input_text: str, expected_output: str, context: Optional[str] = None) -> int:
    cur = get_db().execute(
        "INSERT INTO goldens (task_id, input, expected_output, context) VALUES (?, ?, ?, ?)",
        (task_id, input_text, expected_output, context),
    )
    get_db().commit()
    return cur.lastrowid


def update_golden(
    golden_id: int,
    input_text: Optional[str] = None,
    expected_output: Optional[str] = None,
    context: Optional[str] = None,
) -> bool:
    """Update a golden. Only provided fields are changed; context=None is kept
    unless `clear_context=True`-like semantics are needed (not exposed).
    Returns True if a row was updated."""
    row = get_db().execute(
        "SELECT * FROM goldens WHERE id = ?", (golden_id,)
    ).fetchone()
    if row is None:
        return False
    new_input = input_text if input_text is not None else row["input"]
    new_output = (
        expected_output if expected_output is not None else row["expected_output"]
    )
    new_context = context if context is not None else row["context"]
    get_db().execute(
        "UPDATE goldens SET input = ?, expected_output = ?, context = ? WHERE id = ?",
        (new_input, new_output, new_context, golden_id),
    )
    get_db().commit()
    return True


def delete_golden(golden_id: int) -> bool:
    """Delete a golden (eval_results cascade via FK). Returns True if deleted."""
    cur = get_db().execute("DELETE FROM goldens WHERE id = ?", (golden_id,))
    get_db().commit()
    return cur.rowcount > 0


def get_goldens(task_id: str) -> List[Dict[str, Any]]:
    rows = get_db().execute(
        "SELECT * FROM goldens WHERE task_id = ? ORDER BY id", (task_id,)
    ).fetchall()
    return [dict(r) for r in rows]


def save_eval_result(
    task_id: str,
    golden_id: int,
    actual_output: str,
    retrieval_context: Optional[str],
    metrics: Dict[str, float],
    passed: bool,
) -> int:
    now = datetime.now(timezone.utc).isoformat()
    cur = get_db().execute(
        "INSERT INTO eval_results (task_id, golden_id, actual_output, retrieval_context, metrics_json, passed, evaluated_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (
            task_id,
            golden_id,
            actual_output,
            retrieval_context,
            json.dumps(metrics),
            1 if passed else 0,
            now,
        ),
    )
    get_db().commit()
    return cur.lastrowid


def get_eval_results(task_id: str) -> List[Dict[str, Any]]:
    rows = get_db().execute(
        """SELECT er.*, g.input, g.expected_output
           FROM eval_results er
           JOIN goldens g ON er.golden_id = g.id
           WHERE er.task_id = ?
           ORDER BY er.id""",
        (task_id,),
    ).fetchall()
    return [dict(r) for r in rows]
