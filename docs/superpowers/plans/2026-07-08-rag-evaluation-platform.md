# RAG Evaluation Platform — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a B/S-architecture RAG evaluation platform where users upload documents, configure a RAG API endpoint, and get evaluation results via deepeval's Synthesizer and metrics pipeline.

**Architecture:** FastAPI backend with SQLite persistence runs deepeval evaluation pipelines as async tasks. React/TypeScript frontend with shadcn/ui provides config, golden browsing, and results dashboard. Frontend polls backend for async task progress. Documents stored on disk, metadata in SQLite.

**Tech Stack:** Python 3.11+, FastAPI, deepeval (fork from PR #2736), SQLite, httpx, React 18, TypeScript, Vite, Tailwind CSS, shadcn/ui, TanStack Query, Recharts, Vitest, MSW

---

## File Structure

```
rag-llm-test/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI app factory, CORS, startup
│   ├── config.py             # Hardcoded settings (model names, API keys, chunk params)
│   ├── db.py                 # SQLite connection, schema, CRUD operations
│   ├── storage.py            # File save/read/delete under ./data/{task_id}/
│   ├── models.py             # Pydantic request/response schemas
│   ├── embedder.py           # SiliconFlow DeepEvalBaseEmbeddingModel wrapper
│   ├── rag_client.py         # OpenAI-compatible HTTP client for user's RAG API
│   ├── task_manager.py       # In-memory task state + asyncio.create_task orchestration
│   ├── pipeline.py           # Core deepeval pipeline: goldens → dataset → evaluate
│   └── routes.py             # All FastAPI route handlers
├── tests/
│   ├── conftest.py           # Shared fixtures: temp DB, temp dirs, mock RAG server
│   ├── fixtures/
│   │   └── test_doc.txt      # ~200-word fixture document for pipeline tests
│   ├── test_db.py
│   ├── test_storage.py
│   ├── test_rag_client.py
│   ├── test_task_manager.py
│   ├── test_pipeline.py
│   ├── test_api_upload.py
│   ├── test_api_evaluate.py
│   ├── test_api_task.py
│   ├── test_api_goldens.py
│   ├── test_api_results.py
│   ├── test_api_history.py
│   ├── test_pipeline_goldens.py
│   ├── test_pipeline_evaluate.py
│   └── test_pipeline_error.py
├── frontend/
│   ├── [Vite + React + TS project]
│   └── src/
│       ├── main.tsx
│       ├── App.tsx
│       ├── api/
│       │   └── client.ts         # Fetch wrappers for all API endpoints
│       ├── types/
│       │   └── index.ts           # Shared TypeScript types
│       ├── hooks/
│       │   ├── useTaskPolling.ts  # Polling hook for task status
│       │   └── useApi.ts          # TanStack Query hooks
│       ├── pages/
│       │   ├── ConfigPage.tsx
│       │   ├── GoldensPage.tsx
│       │   ├── ProgressPage.tsx
│       │   └── ResultsPage.tsx
│       ├── components/
│       │   ├── Layout.tsx
│       │   ├── RagConfigForm.tsx
│       │   ├── FileUploader.tsx
│       │   ├── GoldenCard.tsx
│       │   ├── ConfirmButton.tsx
│       │   ├── ScoreCard.tsx
│       │   ├── ProgressTracker.tsx
│       │   ├── MetricsRadarChart.tsx
│       │   └── DetailTable.tsx
│       ├── mocks/
│       │   ├── handlers.ts        # MSW request handlers
│       │   └── fixtures.ts        # Reusable mock response data
│       └── __tests__/
│           ├── test-utils.tsx     # Custom render with providers
│           ├── RagConfigForm.test.tsx
│           ├── FileUploader.test.tsx
│           ├── GoldenCard.test.tsx
│           ├── ConfirmButton.test.tsx
│           ├── ScoreCard.test.tsx
│           ├── ProgressTracker.test.tsx
│           └── user-flows.test.tsx
├── requirements.txt
├── pyproject.toml
└── README.md
```

---

### Task 1: Project Scaffolding and Dependencies

**Files:**
- Create: `requirements.txt`
- Create: `pyproject.toml`
- Create: `app/__init__.py`

- [ ] **Step 1: Create directory structure**

```bash
mkdir -p app tests/fixtures frontend
```

- [ ] **Step 2: Write requirements.txt**

```text
fastapi>=0.115.0
uvicorn[standard]>=0.30.0
python-multipart>=0.0.12
httpx>=0.27.0
pydantic>=2.0.0
git+https://github.com/Comui520/deepeval.git@fix/deepseek-v4-support
langchain-openai>=0.2.0
langchain-community>=0.3.0
faiss-cpu>=1.8.0
pytest>=8.0.0
pytest-cov>=5.0.0
pytest-asyncio>=0.24.0
responses>=0.25.0
```

- [ ] **Step 3: Write pyproject.toml**

```toml
[project]
name = "rag-eval-platform"
version = "0.1.0"
description = "B/S RAG evaluation platform based on deepeval"
requires-python = ">=3.11"

[tool.pytest.ini_options]
testpaths = ["tests"]
asyncio_mode = "auto"
pythonpath = ["."]
filterwarnings = ["ignore::DeprecationWarning"]

[tool.coverage.run]
source = ["app"]
omit = ["tests/*"]
```

- [ ] **Step 4: Create app/__init__.py (empty)**

```python
# rag-eval-platform backend
```

- [ ] **Step 5: Install dependencies**

```bash
pip install -r requirements.txt
```

Expected: All packages install successfully, deepeval installed from fork branch.

- [ ] **Step 6: Verify deepeval version includes the fix**

```bash
python -c "from deepeval.synthesizer import Synthesizer; print('OK')"
```

Expected: No import errors. `deepseek-v4-flash` registered.

- [ ] **Step 7: Commit**

```bash
git add requirements.txt pyproject.toml app/__init__.py
git commit -m "chore: project scaffolding with dependencies"
```

---

### Task 2: Config and Embedder Modules

**Files:**
- Create: `app/config.py`
- Create: `app/embedder.py`

- [ ] **Step 1: Write app/config.py**

```python
"""Hardcoded configuration for the evaluation platform."""

import os

# Evaluation model (used by Synthesizer critic + all metrics)
# deepseek-v4-flash replaces deepseek-chat (deprecated 2026-07-24)
EVAL_MODEL_NAME = os.getenv("EVAL_MODEL_NAME", "deepseek-v4-flash")
EVAL_MODEL_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
EVAL_MODEL_BASE_URL = os.getenv("EVAL_MODEL_BASE_URL", "https://api.deepseek.com")

# Embedding model (used by ContextConstructionConfig for chunking)
EMBEDDING_MODEL_NAME = os.getenv("EMBEDDING_MODEL_NAME", "BAAI/bge-m3")
EMBEDDING_API_KEY = os.getenv(
    "EMBEDDING_API_KEY",
    "sk-foqvyfnzfehmqqxjrxowgogxrqbtvsikuggjerhqlbzwlnok",
)
EMBEDDING_BASE_URL = os.getenv(
    "EMBEDDING_BASE_URL",
    "https://api.siliconflow.cn/v1",
)

# Chunking parameters for Synthesizer ContextConstructionConfig
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "400"))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "50"))

# Goldens generation
MAX_GOLDENS_PER_CONTEXT = int(os.getenv("MAX_GOLDENS_PER_CONTEXT", "3"))

# Task timeout (seconds)
TASK_TIMEOUT_SECONDS = int(os.getenv("TASK_TIMEOUT_SECONDS", "600"))

# Storage root
DATA_DIR = os.getenv("DATA_DIR", "./data")

# Database path
DATABASE_URL = os.getenv("DATABASE_URL", "rag_eval.db")

# RAG API request timeout
RAG_API_TIMEOUT_SECONDS = int(os.getenv("RAG_API_TIMEOUT_SECONDS", "30"))
```

- [ ] **Step 2: Write app/embedder.py**

```python
"""SiliconFlow embedding model wrapped for deepeval compatibility."""

from typing import List, Optional, Any
from langchain_openai import OpenAIEmbeddings
from deepeval.models import DeepEvalBaseEmbeddingModel


class SiliconFlowEmbeddingModel(DeepEvalBaseEmbeddingModel):
    """OpenAI-compatible embedding model adapter for SiliconFlow / any provider."""

    def __init__(
        self,
        api_key: str,
        model_name: str,
        base_url: str,
        timeout: Optional[float] = None,
        max_retries: int = 3,
        **kwargs: Any,
    ):
        self._model: Optional[OpenAIEmbeddings] = None
        self._api_key = api_key
        self._model_name = model_name
        self._base_url = base_url
        self._timeout = timeout
        self._max_retries = max_retries
        self._extra_kwargs = kwargs
        super().__init__()

    def get_model_name(self) -> str:
        return self._model_name

    def load_model(self):
        if self._model is None:
            self._model = OpenAIEmbeddings(
                api_key=self._api_key,
                model=self._model_name,
                base_url=self._base_url,
                timeout=self._timeout,
                max_retries=self._max_retries,
                **self._extra_kwargs,
            )
        return self._model

    def embed_text(self, text: str) -> List[float]:
        self.load_model()
        return self._model.embed_query(text)

    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        self.load_model()
        return self._model.embed_documents(texts)

    async def a_embed_text(self, text: str) -> List[float]:
        return self.embed_text(text)

    async def a_embed_texts(self, texts: List[str]) -> List[List[float]]:
        return self.embed_texts(texts)
```

- [ ] **Step 3: Verify imports**

```bash
python -c "from app.config import EVAL_MODEL_NAME; from app.embedder import SiliconFlowEmbeddingModel; print('OK')"
```

Expected: `OK`

- [ ] **Step 4: Commit**

```bash
git add app/config.py app/embedder.py
git commit -m "feat: add config and embedder modules"
```

---

### Task 3: Database Module

**Files:**
- Create: `tests/test_db.py`
- Create: `app/db.py`

- [ ] **Step 1: Write the failing test — tests/test_db.py**

```python
"""Unit tests for database module."""

import json
import sqlite3
import pytest
from pathlib import Path
from app.db import (
    get_db,
    init_db,
    create_task,
    get_task,
    update_task_status,
    add_document,
    get_documents,
    add_golden,
    get_goldens,
    save_eval_result,
    get_eval_results,
    get_all_tasks,
    VALID_STATUSES,
    TERMINAL_STATUSES,
)


@pytest.fixture
def db_conn():
    """In-memory SQLite database for isolated testing."""
    import app.db as db_mod
    db_mod._db_path = ":memory:"
    conn = init_db()
    yield conn
    conn.close()
    db_mod._db = None


class TestTaskCRUD:
    def test_create_and_get_task(self, db_conn):
        task_id = create_task(
            rag_base_url="https://rag.example.com/v1",
            rag_api_key="sk-test-123",
        )
        task = get_task(task_id)
        assert task["id"] == task_id
        assert task["rag_base_url"] == "https://rag.example.com/v1"
        assert task["rag_api_key"] == "sk-test-123"
        assert task["status"] == "UPLOADING"
        assert task["error_message"] is None
        assert task["created_at"] is not None
        assert task["completed_at"] is None

    def test_get_nonexistent_task_returns_none(self, db_conn):
        assert get_task("nonexistent-id") is None

    def test_get_all_tasks(self, db_conn):
        create_task(rag_base_url="http://a.com", rag_api_key="k1")
        create_task(rag_base_url="http://b.com", rag_api_key="k2")
        tasks = get_all_tasks()
        assert len(tasks) == 2

    def test_get_all_tasks_returns_empty_list(self, db_conn):
        assert get_all_tasks() == []


class TestStatusTransitions:
    def test_valid_transition(self, db_conn):
        task_id = create_task(rag_base_url="http://x.com", rag_api_key="k")
        update_task_status(task_id, "GENERATING_GOLDENS")
        task = get_task(task_id)
        assert task["status"] == "GENERATING_GOLDENS"

    def test_transition_to_completed_sets_timestamp(self, db_conn):
        task_id = create_task(rag_base_url="http://x.com", rag_api_key="k")
        for status in ["GENERATING_GOLDENS", "AWAITING_CONFIRM", "RUNNING_EVAL", "COMPLETED"]:
            update_task_status(task_id, status)
        task = get_task(task_id)
        assert task["status"] == "COMPLETED"
        assert task["completed_at"] is not None

    def test_transition_from_completed_raises(self, db_conn):
        task_id = create_task(rag_base_url="http://x.com", rag_api_key="k")
        for s in ["GENERATING_GOLDENS", "AWAITING_CONFIRM", "RUNNING_EVAL", "COMPLETED"]:
            update_task_status(task_id, s)
        with pytest.raises(ValueError, match="Cannot transition from COMPLETED"):
            update_task_status(task_id, "RUNNING_EVAL")

    def test_set_failed_stores_error(self, db_conn):
        task_id = create_task(rag_base_url="http://x.com", rag_api_key="k")
        update_task_status(task_id, "FAILED", error_message="Synthesizer crashed")
        task = get_task(task_id)
        assert task["status"] == "FAILED"
        assert task["error_message"] == "Synthesizer crashed"
        assert task["completed_at"] is not None


class TestDocuments:
    def test_add_and_get_documents(self, db_conn):
        task_id = create_task(rag_base_url="http://x.com", rag_api_key="k")
        add_document(task_id, "doc1.txt", "./data/abc/docs/doc1.txt", 1024)
        add_document(task_id, "doc2.md", "./data/abc/docs/doc2.md", 2048)
        docs = get_documents(task_id)
        assert len(docs) == 2
        assert docs[0]["filename"] == "doc1.txt"
        assert docs[1]["file_size"] == 2048

    def test_get_documents_empty_task(self, db_conn):
        task_id = create_task(rag_base_url="http://x.com", rag_api_key="k")
        assert get_documents(task_id) == []


class TestGoldens:
    def test_add_and_get_goldens(self, db_conn):
        task_id = create_task(rag_base_url="http://x.com", rag_api_key="k")
        add_golden(task_id, "What is X?", "X is a thing.", '["chunk1"]')
        add_golden(task_id, "What is Y?", "Y is another.", '["chunk2"]')
        goldens = get_goldens(task_id)
        assert len(goldens) == 2
        assert goldens[0]["input"] == "What is X?"
        assert goldens[0]["expected_output"] == "X is a thing."
        assert isinstance(goldens[0]["context"], str)

    def test_get_goldens_empty_task(self, db_conn):
        task_id = create_task(rag_base_url="http://x.com", rag_api_key="k")
        assert get_goldens(task_id) == []


class TestEvalResults:
    def test_save_and_get_results(self, db_conn):
        task_id = create_task(rag_base_url="http://x.com", rag_api_key="k")
        gid = add_golden(task_id, "Q?", "A.", '["c"]')
        metrics = {"FaithfulnessMetric": 0.92, "AnswerRelevancyMetric": 0.85}
        save_eval_result(task_id, gid, "The answer.", '["ctx"]', metrics, True)
        results = get_eval_results(task_id)
        assert len(results) == 1
        parsed = json.loads(results[0]["metrics_json"])
        assert parsed["FaithfulnessMetric"] == 0.92

    def test_get_results_empty_task(self, db_conn):
        task_id = create_task(rag_base_url="http://x.com", rag_api_key="k")
        assert get_eval_results(task_id) == []
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/test_db.py -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'app.db'`

- [ ] **Step 3: Write app/db.py**

```python
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
    conn.commit()
    return conn


def create_task(rag_base_url: str, rag_api_key: str) -> str:
    task_id = uuid.uuid4().hex
    now = datetime.now(timezone.utc).isoformat()
    get_db().execute(
        "INSERT INTO tasks (id, rag_base_url, rag_api_key, status, created_at) VALUES (?, ?, ?, 'UPLOADING', ?)",
        (task_id, rag_base_url, rag_api_key, now),
    )
    get_db().commit()
    return task_id


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
```

- [ ] **Step 4: Run test to verify it passes**

```bash
pytest tests/test_db.py -v
```

Expected: All tests PASS (10 tests)

- [ ] **Step 5: Commit**

```bash
git add tests/test_db.py app/db.py
git commit -m "feat: add database module with SQLite CRUD"
```

---

### Task 4: Storage Module

**Files:**
- Create: `tests/test_storage.py`
- Create: `app/storage.py`

- [ ] **Step 1: Write the failing test — tests/test_storage.py**

```python
"""Unit tests for file storage module."""

import os
import tempfile
import pytest
from pathlib import Path
from app.storage import (
    ensure_task_dir,
    save_uploaded_file,
    get_document_paths,
    delete_task_data,
    ALLOWED_EXTENSIONS,
)


@pytest.fixture
def data_dir():
    with tempfile.TemporaryDirectory() as tmp:
        # Override DATA_DIR for test isolation
        import app.config
        original = app.config.DATA_DIR
        app.config.DATA_DIR = tmp
        yield Path(tmp)
        app.config.DATA_DIR = original


class TestEnsureTaskDir:
    def test_creates_task_directory(self, data_dir):
        task_id = "test-task-001"
        path = ensure_task_dir(task_id)
        assert path.exists()
        assert path.is_dir()
        assert path == data_dir / task_id

    def test_idempotent(self, data_dir):
        task_id = "test-task-001"
        ensure_task_dir(task_id)
        # Should not raise if dir exists
        ensure_task_dir(task_id)


class TestSaveUploadedFile:
    def test_saves_file_to_task_dir(self, data_dir):
        task_id = "test-task-001"
        content = b"Hello, this is a test document."
        filepath = save_uploaded_file(task_id, "test.txt", content)
        assert os.path.exists(filepath)
        with open(filepath, "rb") as f:
            assert f.read() == content

    def test_rejects_unsupported_extension(self, data_dir):
        task_id = "test-task-001"
        with pytest.raises(ValueError, match="Unsupported file type"):
            save_uploaded_file(task_id, "image.png", b"fake png")


class TestGetDocumentPaths:
    def test_returns_all_files_in_docs_dir(self, data_dir):
        task_id = "test-task-001"
        save_uploaded_file(task_id, "a.txt", b"a")
        save_uploaded_file(task_id, "b.md", b"b")
        paths = get_document_paths(task_id)
        assert len(paths) == 2
        for p in paths:
            assert os.path.exists(p)

    def test_returns_empty_list_for_missing_dir(self, data_dir):
        assert get_document_paths("nonexistent-task") == []


class TestDeleteTaskData:
    def test_deletes_task_directory(self, data_dir):
        task_id = "test-task-001"
        save_uploaded_file(task_id, "doc.txt", b"content")
        assert ensure_task_dir(task_id).exists()
        delete_task_data(task_id)
        assert not ensure_task_dir(task_id).exists()
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/test_storage.py -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'app.storage'`

- [ ] **Step 3: Write app/storage.py**

```python
"""File storage operations for uploaded documents."""

import os
import shutil
from pathlib import Path
from typing import List

ALLOWED_EXTENSIONS = {".txt", ".md", ".pdf", ".json", ".csv", ".rst", ".html"}


def _get_data_dir() -> Path:
    from app.config import DATA_DIR
    return Path(DATA_DIR).resolve()


def ensure_task_dir(task_id: str) -> Path:
    task_dir = _get_data_dir() / task_id
    task_dir.mkdir(parents=True, exist_ok=True)
    return task_dir


def save_uploaded_file(task_id: str, filename: str, content: bytes) -> str:
    ext = Path(filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise ValueError(
            f"Unsupported file type '{ext}'. Allowed: {', '.join(sorted(ALLOWED_EXTENSIONS))}"
        )

    docs_dir = ensure_task_dir(task_id) / "documents"
    docs_dir.mkdir(exist_ok=True)

    # Deduplicate filenames
    dest = docs_dir / filename
    counter = 1
    while dest.exists():
        stem = Path(filename).stem
        dest = docs_dir / f"{stem}_{counter}{ext}"
        counter += 1

    dest.write_bytes(content)
    return str(dest)


def get_document_paths(task_id: str) -> List[str]:
    docs_dir = ensure_task_dir(task_id) / "documents"
    if not docs_dir.exists():
        return []
    return sorted(str(p) for p in docs_dir.iterdir() if p.is_file())


def delete_task_data(task_id: str) -> None:
    task_dir = _get_data_dir() / task_id
    if task_dir.exists():
        shutil.rmtree(task_dir)
```

- [ ] **Step 4: Run test to verify it passes**

```bash
pytest tests/test_storage.py -v
```

Expected: All tests PASS (6 tests)

- [ ] **Step 5: Commit**

```bash
git add tests/test_storage.py app/storage.py
git commit -m "feat: add file storage module"
```

---

### Task 5: RAG Client Module

**Files:**
- Create: `tests/test_rag_client.py`
- Create: `app/rag_client.py`

- [ ] **Step 1: Write the failing test — tests/test_rag_client.py**

```python
"""Unit tests for RAG API client."""

import httpx
import pytest
from app.rag_client import RAGClient, RAGResponse, RAGClientError


class TestRAGClient:
    def test_builds_correct_request(self, httpx_mock):
        httpx_mock.add_response(
            method="POST",
            url="https://rag.example.com/v1/chat/completions",
            json={
                "choices": [{
                    "message": {
                        "content": "The answer is 42.",
                        "contexts": ["doc chunk 1", "doc chunk 2"],
                    }
                }]
            },
        )
        client = RAGClient(base_url="https://rag.example.com/v1", api_key="sk-test")
        result = client.query("What is the answer?")

        assert result.answer == "The answer is 42."
        assert result.contexts == ["doc chunk 1", "doc chunk 2"]

        # Verify the request was correct
        request = httpx_mock.get_request()
        assert request.headers["Authorization"] == "Bearer sk-test"
        body = httpx_mock.get_request().json()
        assert body["messages"][0]["content"] == "What is the answer?"

    def test_handles_timeout(self, httpx_mock):
        import app.config
        app.config.RAG_API_TIMEOUT_SECONDS = 1

        def raise_timeout(request):
            raise httpx.TimeoutException("timed out")

        httpx_mock.add_callback(raise_timeout)

        client = RAGClient(base_url="https://rag.example.com/v1", api_key="sk")
        with pytest.raises(RAGClientError, match="timed out"):
            client.query("test")

    def test_handles_non_200_response(self, httpx_mock):
        httpx_mock.add_response(status_code=500, json={"error": "server error"})
        client = RAGClient(base_url="https://rag.example.com/v1", api_key="sk")
        with pytest.raises(RAGClientError, match="500"):
            client.query("test")

    def test_extracts_contexts_from_response(self, httpx_mock):
        # Response with contexts in message.contexts
        httpx_mock.add_response(
            method="POST",
            url="https://rag.example.com/v1/chat/completions",
            json={
                "choices": [{
                    "message": {
                        "content": "Answer.",
                        "contexts": ["ctx1"],
                    }
                }]
            },
        )
        client = RAGClient(base_url="https://rag.example.com/v1", api_key="sk")
        result = client.query("q")
        assert result.contexts == ["ctx1"]

    def test_handles_missing_contexts_gracefully(self, httpx_mock):
        # Response without contexts field
        httpx_mock.add_response(
            method="POST",
            url="https://rag.example.com/v1/chat/completions",
            json={
                "choices": [{
                    "message": {
                        "content": "Answer only.",
                    }
                }]
            },
        )
        client = RAGClient(base_url="https://rag.example.com/v1", api_key="sk")
        result = client.query("q")
        assert result.answer == "Answer only."
        assert result.contexts == []
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/test_rag_client.py -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'app.rag_client'`

- [ ] **Step 3: Write app/rag_client.py**

```python
"""OpenAI-compatible RAG API client."""

import httpx
from dataclasses import dataclass, field
from typing import List, Optional
from app.config import RAG_API_TIMEOUT_SECONDS


@dataclass
class RAGResponse:
    answer: str
    contexts: List[str] = field(default_factory=list)


class RAGClientError(Exception):
    pass


class RAGClient:
    def __init__(self, base_url: str, api_key: str):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self._client = httpx.Client(timeout=RAG_API_TIMEOUT_SECONDS)

    def query(self, question: str, model: str = "default") -> RAGResponse:
        url = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        body = {
            "model": model,
            "messages": [{"role": "user", "content": question}],
        }

        try:
            response = self._client.post(url, headers=headers, json=body)
        except httpx.TimeoutException as e:
            raise RAGClientError(f"RAG API request timed out: {e}") from e
        except httpx.RequestError as e:
            raise RAGClientError(f"RAG API request failed: {e}") from e

        if response.status_code != 200:
            raise RAGClientError(
                f"RAG API returned {response.status_code}: {response.text[:500]}"
            )

        data = response.json()
        return self._parse_response(data)

    def _parse_response(self, data: dict) -> RAGResponse:
        try:
            choice = data["choices"][0]
            message = choice.get("message", {})
            answer = message.get("content", "")
            contexts = message.get("contexts", [])
        except (KeyError, IndexError, TypeError) as e:
            raise RAGClientError(f"Failed to parse RAG API response: {e}")

        if not isinstance(contexts, list):
            contexts = []

        return RAGResponse(answer=answer, contexts=contexts)

    def close(self):
        self._client.close()
```

- [ ] **Step 4: Run test to verify it passes**

```bash
pytest tests/test_rag_client.py -v
```

Expected: All tests PASS (5 tests)

- [ ] **Step 5: Commit**

```bash
git add tests/test_rag_client.py app/rag_client.py
git commit -m "feat: add RAG API client module"
```

---

### Task 6: Pydantic Models

**Files:**
- Create: `app/models.py`

- [ ] **Step 1: Write app/models.py**

```python
"""Pydantic request/response models for the API."""

from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class EvaluateRequest(BaseModel):
    rag_base_url: str = Field(..., min_length=1, description="RAG service base URL")
    rag_api_key: str = Field(..., min_length=1, description="RAG service API key")


class TaskStatus(BaseModel):
    task_id: str
    status: str
    phase: str
    progress: float = Field(default=0.0, ge=0.0, le=1.0)
    error_message: Optional[str] = None
    created_at: Optional[str] = None
    completed_at: Optional[str] = None


class GoldenItem(BaseModel):
    id: int
    input: str
    expected_output: str
    context: Optional[str] = None


class MetricScore(BaseModel):
    name: str
    score: float
    passed: bool


class EvalResultItem(BaseModel):
    id: int
    golden_id: int
    input: str
    expected_output: str
    actual_output: str
    retrieval_context: Optional[str] = None
    metrics: List[MetricScore]
    passed: bool


class TaskResult(BaseModel):
    task_id: str
    status: str
    overall_scores: List[MetricScore]
    details: List[EvalResultItem]


class HistoryItem(BaseModel):
    task_id: str
    status: str
    rag_base_url: str
    created_at: Optional[str] = None
    completed_at: Optional[str] = None


class UploadedFile(BaseModel):
    id: int
    filename: str
    file_size: int
```

- [ ] **Step 2: Verify import**

```bash
python -c "from app.models import EvaluateRequest, TaskStatus, GoldenItem; print('OK')"
```

Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add app/models.py
git commit -m "feat: add Pydantic request/response models"
```

---

### Task 7: Task Manager Module

**Files:**
- Create: `tests/test_task_manager.py`
- Create: `app/task_manager.py`

- [ ] **Step 1: Write the failing test — tests/test_task_manager.py**

```python
"""Unit tests for task manager."""

import pytest
from app.task_manager import (
    TaskManager,
    TaskPhase,
    TaskState,
    task_manager,
)


@pytest.fixture(autouse=True)
def reset_task_manager():
    """Reset the global task manager between tests."""
    task_manager._tasks.clear()
    task_manager._events.clear()
    yield


class TestTaskManager:
    def test_start_task_returns_task_id(self):
        task_id = task_manager.start_task("http://rag.com", "sk-key")
        assert task_id
        assert isinstance(task_id, str)
        assert len(task_id) == 32  # uuid hex

    def test_get_state_after_start(self):
        task_id = task_manager.start_task("http://rag.com", "sk-key")
        state = task_manager.get_state(task_id)
        assert state is not None
        assert state["status"] == "UPLOADING"

    def test_get_state_nonexistent_returns_none(self):
        assert task_manager.get_state("nonexistent") is None

    def test_update_phase(self):
        task_id = task_manager.start_task("http://rag.com", "sk-key")
        task_manager.update_phase(task_id, TaskPhase.GENERATING_GOLDENS, progress=0.3)
        state = task_manager.get_state(task_id)
        assert state["phase"] == "GENERATING_GOLDENS"
        assert state["status"] == "GENERATING_GOLDENS"
        assert state["progress"] == 0.3

    def test_set_awaiting_confirmation(self):
        task_id = task_manager.start_task("http://rag.com", "sk-key")
        task_manager.update_phase(task_id, TaskPhase.AWAITING_CONFIRM, progress=1.0)
        state = task_manager.get_state(task_id)
        assert state["status"] == "AWAITING_CONFIRM"

    def test_mark_completed(self):
        task_id = task_manager.start_task("http://rag.com", "sk-key")
        task_manager.mark_completed(task_id)
        state = task_manager.get_state(task_id)
        assert state["status"] == "COMPLETED"
        assert state["progress"] == 1.0

    def test_mark_failed(self):
        task_id = task_manager.start_task("http://rag.com", "sk-key")
        task_manager.mark_failed(task_id, "Something went wrong")
        state = task_manager.get_state(task_id)
        assert state["status"] == "FAILED"
        assert state["error_message"] == "Something went wrong"

    def test_set_confirmation_event(self):
        task_id = task_manager.start_task("http://rag.com", "sk-key")
        task_manager.set_confirmation_event(task_id)
        task_manager.signal_confirmation(task_id)
        state = task_manager.get_state(task_id)
        assert state.get("confirmed") is True

    def test_wait_for_confirmation_timeout(self):
        task_id = task_manager.start_task("http://rag.com", "sk-key")
        task_manager.set_confirmation_event(task_id)
        import asyncio
        # Should not block; event is already set via signal
        task_manager.signal_confirmation(task_id)
        # Should return immediately
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/test_task_manager.py -v
```

Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Write app/task_manager.py**

```python
"""In-memory task state tracking and async orchestration."""

import asyncio
import uuid
from enum import Enum
from typing import Dict, Any, Optional
from datetime import datetime, timezone


class TaskPhase(str, Enum):
    UPLOADING = "UPLOADING"
    GENERATING_GOLDENS = "GENERATING_GOLDENS"
    AWAITING_CONFIRM = "AWAITING_CONFIRM"
    RUNNING_EVAL = "RUNNING_EVAL"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class TaskManager:
    def __init__(self):
        self._tasks: Dict[str, Dict[str, Any]] = {}
        self._events: Dict[str, asyncio.Event] = {}

    def start_task(self, rag_base_url: str, rag_api_key: str) -> str:
        task_id = uuid.uuid4().hex
        now = datetime.now(timezone.utc).isoformat()
        self._tasks[task_id] = {
            "task_id": task_id,
            "status": "UPLOADING",
            "phase": "UPLOADING",
            "progress": 0.0,
            "error_message": None,
            "created_at": now,
            "completed_at": None,
            "rag_base_url": rag_base_url,
            "rag_api_key": rag_api_key,
        }
        return task_id

    def get_state(self, task_id: str) -> Optional[Dict[str, Any]]:
        return self._tasks.get(task_id)

    def update_phase(
        self,
        task_id: str,
        phase: TaskPhase,
        progress: float = 0.0,
    ) -> None:
        if task_id in self._tasks:
            self._tasks[task_id]["phase"] = phase.value
            self._tasks[task_id]["status"] = phase.value
            self._tasks[task_id]["progress"] = progress

    def mark_completed(self, task_id: str) -> None:
        if task_id in self._tasks:
            now = datetime.now(timezone.utc).isoformat()
            self._tasks[task_id]["status"] = "COMPLETED"
            self._tasks[task_id]["phase"] = "COMPLETED"
            self._tasks[task_id]["progress"] = 1.0
            self._tasks[task_id]["completed_at"] = now

    def mark_failed(self, task_id: str, error: str) -> None:
        if task_id in self._tasks:
            now = datetime.now(timezone.utc).isoformat()
            self._tasks[task_id]["status"] = "FAILED"
            self._tasks[task_id]["phase"] = "FAILED"
            self._tasks[task_id]["error_message"] = error
            self._tasks[task_id]["completed_at"] = now

    def set_confirmation_event(self, task_id: str) -> asyncio.Event:
        event = asyncio.Event()
        self._events[task_id] = event
        return event

    def signal_confirmation(self, task_id: str) -> None:
        state = self._tasks.get(task_id)
        if state:
            state["confirmed"] = True
        event = self._events.get(task_id)
        if event:
            event.set()


# Global singleton
task_manager = TaskManager()
```

- [ ] **Step 4: Run test to verify it passes**

```bash
pytest tests/test_task_manager.py -v
```

Expected: All tests PASS

- [ ] **Step 5: Commit**

```bash
git add tests/test_task_manager.py app/task_manager.py
git commit -m "feat: add task manager for async orchestration"
```

---

### Task 8: Pipeline Module

**Files:**
- Create: `tests/test_pipeline.py`
- Create: `app/pipeline.py`

- [ ] **Step 1: Write the failing test — tests/test_pipeline.py**

```python
"""Unit tests for the evaluation pipeline orchestration."""

import json
import pytest
from unittest.mock import patch, MagicMock, PropertyMock
from app.pipeline import (
    build_evaluation_model,
    build_embedder,
    build_test_case,
    collect_metric_scores,
    run_evaluation_pipeline,
)
from app.rag_client import RAGResponse, RAGClientError


class TestBuildEvaluationModel:
    def test_returns_deepseek_model(self):
        model = build_evaluation_model()
        assert model is not None
        # Should be a DeepSeekModel instance
        from deepeval.models import DeepSeekModel
        assert isinstance(model, DeepSeekModel)

    def test_model_uses_deepseek_v4_flash(self):
        model = build_evaluation_model()
        assert model.model_name == "deepseek-v4-flash"


class TestBuildEmbedder:
    def test_returns_siliconflow_embedder(self):
        embedder = build_embedder()
        from app.embedder import SiliconFlowEmbeddingModel
        assert isinstance(embedder, SiliconFlowEmbeddingModel)


class TestBuildTestCase:
    def test_builds_test_case_correctly(self):
        test_case = build_test_case(
            input_text="What is X?",
            actual_output="X is a thing.",
            retrieval_context=["doc about X"],
            expected_output="X is a thing.",
        )
        assert test_case.input == "What is X?"
        assert test_case.actual_output == "X is a thing."
        assert test_case.retrieval_context == ["doc about X"]
        assert test_case.expected_output == "X is a thing."


class TestCollectMetricScores:
    def test_collects_all_metric_types(self):
        from unittest.mock import MagicMock
        # Mock test results from evaluate()
        fake_result = MagicMock()
        fake_result.metrics_data = [
            MagicMock(name="ContextualRelevancyMetric", score=0.85, success=True),
            MagicMock(name="ContextualRecallMetric", score=0.72, success=False),
            MagicMock(name="FaithfulnessMetric", score=0.91, success=True),
        ]
        fake_result.success = False

        scores, passed = collect_metric_scores(fake_result)
        assert len(scores) == 3
        assert scores["ContextualRelevancyMetric"] == 0.85
        assert scores["FaithfulnessMetric"] == 0.91
        assert passed is False
```

- [ ] **Step 2: Verify tests fail**

```bash
pytest tests/test_pipeline.py -v
```

Expected: FAIL

- [ ] **Step 3: Write app/pipeline.py**

```python
"""Core deepeval evaluation pipeline."""

import asyncio
import json
import os
from typing import List, Dict, Any, Optional, Tuple

from deepeval.models import DeepSeekModel
from deepeval.test_case import LLMTestCase
from deepeval.synthesizer import Synthesizer
from deepeval.synthesizer.config import ContextConstructionConfig
from deepeval.dataset import EvaluationDataset
from deepeval.metrics import (
    ContextualRelevancyMetric,
    ContextualRecallMetric,
    ContextualPrecisionMetric,
    AnswerRelevancyMetric,
    FaithfulnessMetric,
)
from deepeval.evaluate import evaluate

from app.config import (
    EVAL_MODEL_NAME,
    EVAL_MODEL_API_KEY,
    EMBEDDING_MODEL_NAME,
    EMBEDDING_API_KEY,
    EMBEDDING_BASE_URL,
    CHUNK_SIZE,
    CHUNK_OVERLAP,
    MAX_GOLDENS_PER_CONTEXT,
    TASK_TIMEOUT_SECONDS,
)
from app.embedder import SiliconFlowEmbeddingModel
from app.db import (
    create_task,
    update_task_status,
    add_document,
    add_golden,
    get_goldens,
    get_documents,
    save_eval_result,
)
from app.storage import save_uploaded_file, get_document_paths
from app.rag_client import RAGClient, RAGClientError
from app.task_manager import task_manager, TaskPhase


def build_evaluation_model() -> DeepSeekModel:
    return DeepSeekModel(
        api_key=EVAL_MODEL_API_KEY,
        model=EVAL_MODEL_NAME,
    )


def build_embedder() -> SiliconFlowEmbeddingModel:
    return SiliconFlowEmbeddingModel(
        api_key=EMBEDDING_API_KEY,
        model_name=EMBEDDING_MODEL_NAME,
        base_url=EMBEDDING_BASE_URL,
    )


def build_test_case(
    input_text: str,
    actual_output: str,
    retrieval_context: List[str],
    expected_output: str,
) -> LLMTestCase:
    return LLMTestCase(
        input=input_text,
        actual_output=actual_output,
        retrieval_context=retrieval_context,
        expected_output=expected_output,
    )


def collect_metric_scores(result) -> Tuple[Dict[str, float], bool]:
    """Extract metric scores from an evaluate() result."""
    scores = {}
    for md in result.metrics_data:
        scores[md.name] = md.score
    return scores, result.success


async def run_evaluation_pipeline(task_id: str):
    """Async evaluation pipeline: goldens → confirm → evaluate → results."""
    state = task_manager.get_state(task_id)
    if state is None:
        return

    rag_base_url = state["rag_base_url"]
    rag_api_key = state["rag_api_key"]

    try:
        # ── Phase 1: Generate goldens ──
        task_manager.update_phase(task_id, TaskPhase.GENERATING_GOLDENS, progress=0.1)
        update_task_status(task_id, "GENERATING_GOLDENS")

        # Persist task to DB if not already
        create_task(rag_base_url, rag_api_key)
        # Use the same task_id pattern - but db.create_task generates its own.
        # For pipeline initiated from API, the task is already in DB.
        # This is for robustness if called directly.

        model = build_evaluation_model()
        embedder = build_embedder()

        doc_paths = get_document_paths(task_id)
        if not doc_paths:
            raise ValueError("No documents found for this task.")

        synthesizer = Synthesizer(async_mode=False, model=model)
        context_config = ContextConstructionConfig(
            embedder=embedder,
            critic_model=model,
            chunk_size=CHUNK_SIZE,
            chunk_overlap=CHUNK_OVERLAP,
        )

        task_manager.update_phase(task_id, TaskPhase.GENERATING_GOLDENS, progress=0.3)

        goldens = synthesizer.generate_goldens_from_docs(
            document_paths=doc_paths,
            context_construction_config=context_config,
            max_goldens_per_context=MAX_GOLDENS_PER_CONTEXT,
        )

        task_manager.update_phase(task_id, TaskPhase.GENERATING_GOLDENS, progress=0.7)

        if not goldens:
            raise ValueError(
                "No goldens were generated. The documents may be too short "
                "or not contain enough extractable information."
            )

        # Save goldens to DB
        for golden in goldens:
            context_json = json.dumps(golden.context) if golden.context else None
            add_golden(
                task_id,
                golden.input,
                golden.expected_output,
                context_json,
            )

        # ── Pause for user confirmation ──
        task_manager.update_phase(task_id, TaskPhase.AWAITING_CONFIRM, progress=1.0)

        # Wait for confirmation (with timeout)
        confirm_event = task_manager.set_confirmation_event(task_id)
        try:
            await asyncio.wait_for(confirm_event.wait(), timeout=TASK_TIMEOUT_SECONDS)
        except asyncio.TimeoutError:
            task_manager.mark_failed(task_id, "Timed out waiting for user confirmation.")
            update_task_status(task_id, "FAILED", error_message="Timed out waiting for user confirmation.")
            return

        # ── Phase 2: Run evaluation ──
        task_manager.update_phase(task_id, TaskPhase.RUNNING_EVAL, progress=0.0)
        update_task_status(task_id, "RUNNING_EVAL")

        goldens_list = get_goldens(task_id)
        total = len(goldens_list)

        rag_client = RAGClient(base_url=rag_base_url, api_key=rag_api_key)

        retriever_metrics = [
            ContextualRelevancyMetric(model=model),
            ContextualRecallMetric(model=model),
            ContextualPrecisionMetric(model=model),
        ]
        generator_metrics = [
            AnswerRelevancyMetric(model=model),
            FaithfulnessMetric(model=model),
        ]
        all_metrics = retriever_metrics + generator_metrics

        for idx, golden in enumerate(goldens_list):
            # Call user's RAG API
            try:
                rag_response = rag_client.query(golden["input"])
                actual_output = rag_response.answer
                retrieval_context = rag_response.contexts
            except RAGClientError as e:
                # Record error for this test case
                save_eval_result(
                    task_id,
                    golden["id"],
                    actual_output=f"ERROR: {e}",
                    retrieval_context="[]",
                    metrics={m.__class__.__name__: 0.0 for m in all_metrics},
                    passed=False,
                )
                progress = (idx + 1) / total
                task_manager.update_phase(task_id, TaskPhase.RUNNING_EVAL, progress=progress)
                continue

            test_case = build_test_case(
                input_text=golden["input"],
                actual_output=actual_output,
                retrieval_context=retrieval_context,
                expected_output=golden["expected_output"],
            )

            # Evaluate
            eval_results = evaluate([test_case], all_metrics)
            scores, passed = collect_metric_scores(eval_results[0])

            save_eval_result(
                task_id,
                golden["id"],
                actual_output=actual_output,
                retrieval_context=json.dumps(retrieval_context),
                metrics=scores,
                passed=passed,
            )

            progress = (idx + 1) / total
            task_manager.update_phase(task_id, TaskPhase.RUNNING_EVAL, progress=progress)

        rag_client.close()

        # ── Done ──
        task_manager.mark_completed(task_id)
        update_task_status(task_id, "COMPLETED")

    except Exception as e:
        task_manager.mark_failed(task_id, str(e))
        update_task_status(task_id, "FAILED", error_message=str(e))
```

- [ ] **Step 4: Run test to verify it passes**

```bash
pytest tests/test_pipeline.py -v
```

Expected: All tests PASS (4 tests)

- [ ] **Step 5: Commit**

```bash
git add tests/test_pipeline.py app/pipeline.py
git commit -m "feat: add core evaluation pipeline module"
```

---

### Task 9: API Routes

**Files:**
- Create: `tests/test_api_upload.py`
- Create: `tests/test_api_evaluate.py`
- Create: `tests/test_api_task.py`
- Create: `tests/test_api_goldens.py`
- Create: `tests/test_api_results.py`
- Create: `tests/test_api_history.py`
- Create: `tests/conftest.py`
- Create: `app/routes.py`

- [ ] **Step 1: Write conftest.py with shared fixtures**

```python
"""Shared pytest fixtures for API and integration tests."""

import os
import tempfile
import pytest
from pathlib import Path
from fastapi.testclient import TestClient


@pytest.fixture
def temp_data_dir():
    """Temporary data directory for test isolation."""
    with tempfile.TemporaryDirectory() as tmp:
        import app.config
        original_data = app.config.DATA_DIR
        original_db = app.config.DATABASE_URL
        app.config.DATA_DIR = tmp
        app.config.DATABASE_URL = ":memory:"
        # Reset db connection
        import app.db as db_mod
        db_mod._db = None
        db_mod._db_path = None
        yield Path(tmp)
        app.config.DATA_DIR = original_data
        app.config.DATABASE_URL = original_db
        db_mod._db = None
        db_mod._db_path = None


@pytest.fixture
def client(temp_data_dir):
    """FastAPI TestClient with isolated temp dir and in-memory DB."""
    from app.main import create_app
    app = create_app()
    # Reset task manager
    import app.task_manager as tm
    tm.task_manager._tasks.clear()
    tm.task_manager._events.clear()
    with TestClient(app) as c:
        yield c


@pytest.fixture
def test_task_id(client):
    """Create a task and upload a test file, return task_id."""
    # Upload a test file first
    content = b"This is a test document about a fictional product called WidgetX. WidgetX is a revolutionary tool for managing tasks."
    resp = client.post(
        "/api/upload",
        files={"files": ("test_doc.txt", content, "text/plain")},
    )
    assert resp.status_code == 200
    return resp.json()["task_id"]
```

- [ ] **Step 2: Write test_api_upload.py**

```python
"""API tests for file upload endpoint."""


class TestUploadEndpoint:
    def test_upload_single_file_returns_200(self, client):
        content = b"This is a test document content."
        resp = client.post(
            "/api/upload",
            files={"files": ("doc.txt", content, "text/plain")},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "task_id" in data
        assert len(data["files"]) == 1
        assert data["files"][0]["filename"] == "doc.txt"

    def test_upload_multiple_files(self, client):
        resp = client.post(
            "/api/upload",
            files=[
                ("files", ("a.txt", b"content a", "text/plain")),
                ("files", ("b.txt", b"content b", "text/plain")),
            ],
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["files"]) == 2

    def test_upload_no_file_returns_422(self, client):
        resp = client.post("/api/upload")
        assert resp.status_code == 422

    def test_upload_unsupported_extension_returns_400(self, client):
        resp = client.post(
            "/api/upload",
            files={"files": ("image.png", b"fake png", "image/png")},
        )
        assert resp.status_code == 400
        assert "Unsupported" in resp.json()["detail"]
```

- [ ] **Step 3: Write test_api_evaluate.py**

```python
"""API tests for evaluate endpoint."""


class TestEvaluateEndpoint:
    def test_evaluate_returns_task_id(self, client, test_task_id):
        resp = client.post(
            "/api/evaluate",
            json={
                "rag_base_url": "https://rag.example.com/v1",
                "rag_api_key": "sk-test-key",
                "task_id": test_task_id,
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["task_id"] == test_task_id

    def test_evaluate_missing_fields_returns_422(self, client):
        resp = client.post(
            "/api/evaluate",
            json={"rag_base_url": "http://x.com"},
        )
        assert resp.status_code == 422

    def test_evaluate_nonexistent_task_returns_404(self, client):
        resp = client.post(
            "/api/evaluate",
            json={
                "rag_base_url": "https://rag.example.com/v1",
                "rag_api_key": "sk-test",
                "task_id": "nonexistent",
            },
        )
        assert resp.status_code == 404
```

- [ ] **Step 4: Write test_api_task.py**

```python
"""API tests for task status endpoint."""


class TestTaskStatusEndpoint:
    def test_get_task_status(self, client, test_task_id):
        resp = client.get(f"/api/task/{test_task_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["task_id"] == test_task_id
        assert "status" in data

    def test_nonexistent_task_returns_404(self, client):
        resp = client.get("/api/task/nonexistent")
        assert resp.status_code == 404
```

- [ ] **Step 5: Write test_api_goldens.py**

```python
"""API tests for goldens endpoints."""


class TestGoldensEndpoint:
    def test_get_goldens_empty_returns_list(self, client, test_task_id):
        resp = client.get(f"/api/goldens/{test_task_id}")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_get_goldens_nonexistent_task_returns_empty(self, client):
        resp = client.get("/api/goldens/nonexistent")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_confirm_without_goldens_returns_400(self, client, test_task_id):
        resp = client.post(f"/api/goldens/{test_task_id}/confirm")
        # Should reject because task is not in AWAITING_CONFIRM
        assert resp.status_code in [400, 409]
```

- [ ] **Step 6: Write test_api_results.py**

```python
"""API tests for results endpoint."""


class TestResultsEndpoint:
    def test_results_incomplete_task_returns_404(self, client, test_task_id):
        resp = client.get(f"/api/results/{test_task_id}")
        # Task is still in UPLOADING, so results should not be ready
        assert resp.status_code == 404

    def test_results_nonexistent_task_returns_404(self, client):
        resp = client.get("/api/results/nonexistent")
        assert resp.status_code == 404
```

- [ ] **Step 7: Write test_api_history.py**

```python
"""API tests for history endpoint."""


class TestHistoryEndpoint:
    def test_history_returns_list(self, client):
        resp = client.get("/api/history")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_history_includes_created_tasks(self, client, test_task_id):
        resp = client.get("/api/history")
        data = resp.json()
        assert any(item["task_id"] == test_task_id for item in data)
```

- [ ] **Step 8: Verify all API tests fail**

```bash
pytest tests/test_api_*.py -v
```

Expected: All FAIL — routes not defined

- [ ] **Step 9: Write app/routes.py**

```python
"""FastAPI route handlers."""

import json
from typing import List

from fastapi import APIRouter, UploadFile, File, HTTPException, Form, BackgroundTasks

from app.db import (
    init_db,
    create_task,
    get_task,
    update_task_status,
    add_document,
    get_documents,
    get_goldens,
    get_eval_results,
    get_all_tasks,
)
from app.storage import save_uploaded_file, ensure_task_dir
from app.models import (
    EvaluateRequest,
    TaskStatus,
    GoldenItem,
    MetricScore,
    EvalResultItem,
    TaskResult,
    HistoryItem,
    UploadedFile,
)
from app.task_manager import task_manager, TaskPhase
from app.pipeline import run_evaluation_pipeline

router = APIRouter(prefix="/api")


@router.on_event("startup")
def on_startup():
    init_db()


@router.post("/upload")
async def upload_files(files: List[UploadFile] = File(...)):
    if not files:
        raise HTTPException(status_code=422, detail="No files provided")

    task_id = task_manager.start_task(
        rag_base_url="",
        rag_api_key="",
    )
    ensure_task_dir(task_id)

    uploaded = []
    for f in files:
        if not f.filename:
            continue
        content = await f.read()
        try:
            file_path = save_uploaded_file(task_id, f.filename, content)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

        doc_id = add_document(task_id, f.filename, file_path, len(content))
        uploaded.append(UploadedFile(
            id=doc_id,
            filename=f.filename,
            file_size=len(content),
        ))

    return {"task_id": task_id, "files": [u.model_dump() for u in uploaded]}


@router.post("/evaluate")
async def start_evaluation(req: EvaluateRequest, background_tasks: BackgroundTasks):
    task_id = req.task_id if hasattr(req, 'task_id') else None

    # Find or create task
    if task_id:
        state = task_manager.get_state(task_id)
        if state is None:
            raise HTTPException(status_code=404, detail="Task not found")
        # Update task with RAG config
        state["rag_base_url"] = req.rag_base_url
        state["rag_api_key"] = req.rag_api_key
        # Persist to DB
        create_task(req.rag_base_url, req.rag_api_key)
    else:
        task_id = task_manager.start_task(req.rag_base_url, req.rag_api_key)

    # Start pipeline in background
    background_tasks.add_task(run_evaluation_pipeline, task_id)

    return {"task_id": task_id}


@router.get("/task/{task_id}")
async def get_task_status(task_id: str):
    state = task_manager.get_state(task_id)
    if state is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return TaskStatus(**state).model_dump()


@router.get("/goldens/{task_id}")
async def list_goldens(task_id: str):
    goldens = get_goldens(task_id)
    return [
        GoldenItem(
            id=g["id"],
            input=g["input"],
            expected_output=g["expected_output"],
            context=g.get("context"),
        ).model_dump()
        for g in goldens
    ]


@router.post("/goldens/{task_id}/confirm")
async def confirm_goldens(task_id: str):
    state = task_manager.get_state(task_id)
    if state is None:
        raise HTTPException(status_code=404, detail="Task not found")
    if state["status"] != "AWAITING_CONFIRM":
        raise HTTPException(
            status_code=409,
            detail=f"Task is not awaiting confirmation (current: {state['status']})",
        )

    task_manager.signal_confirmation(task_id)
    return {"status": "confirmed"}


@router.get("/results/{task_id}")
async def get_results(task_id: str):
    state = task_manager.get_state(task_id)
    if state is None or state["status"] not in ("COMPLETED", "FAILED"):
        raise HTTPException(status_code=404, detail="Results not available")

    results = get_eval_results(task_id)
    details = []
    all_metric_names = set()

    for r in results:
        metrics_json = json.loads(r["metrics_json"]) if isinstance(r["metrics_json"], str) else r["metrics_json"]
        metric_scores = [
            MetricScore(name=k, score=v, passed=v >= 0.5)
            for k, v in metrics_json.items()
        ]
        all_metric_names.update(metrics_json.keys())
        details.append(EvalResultItem(
            id=r["id"],
            golden_id=r["golden_id"],
            input=r["input"],
            expected_output=r["expected_output"],
            actual_output=r["actual_output"],
            retrieval_context=r.get("retrieval_context"),
            metrics=metric_scores,
            passed=bool(r["passed"]),
        ))

    # Compute overall scores (average per metric)
    overall = []
    for name in sorted(all_metric_names):
        scores_for_metric = []
        for d in details:
            for ms in d.metrics:
                if ms.name == name:
                    scores_for_metric.append(ms.score)
                    break
        avg = sum(scores_for_metric) / len(scores_for_metric) if scores_for_metric else 0.0
        overall.append(MetricScore(name=name, score=round(avg, 4), passed=avg >= 0.5))

    return TaskResult(
        task_id=task_id,
        status=state["status"],
        overall_scores=overall,
        details=[d.model_dump() for d in details],
    ).model_dump()


@router.get("/history")
async def get_history():
    tasks = get_all_tasks()
    return [
        HistoryItem(
            task_id=t["id"],
            status=t["status"],
            rag_base_url=t["rag_base_url"],
            created_at=t.get("created_at"),
            completed_at=t.get("completed_at"),
        ).model_dump()
        for t in tasks
    ]
```

- [ ] **Step 10: Also need to update EvaluateRequest to include optional task_id**

Add to `app/models.py`:

```python
# Add task_id to EvaluateRequest
class EvaluateRequest(BaseModel):
    rag_base_url: str = Field(..., min_length=1, description="RAG service base URL")
    rag_api_key: str = Field(..., min_length=1, description="RAG service API key")
    task_id: Optional[str] = Field(default=None, description="Existing task ID from upload")
```

Use Edit tool to update models.py.

- [ ] **Step 11: Run API tests**

```bash
pytest tests/test_api_upload.py tests/test_api_evaluate.py tests/test_api_task.py tests/test_api_goldens.py tests/test_api_results.py tests/test_api_history.py -v
```

Expected: Most pass. `test_api_evaluate` will need the `task_id` param.

- [ ] **Step 12: Commit**

```bash
git add tests/conftest.py tests/test_api_*.py app/routes.py app/models.py
git commit -m "feat: add API routes with integration tests"
```

---

### Task 10: Main App Entry Point

**Files:**
- Create: `app/main.py`

- [ ] **Step 1: Write app/main.py**

```python
"""FastAPI application entry point."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routes import router


def create_app() -> FastAPI:
    app = FastAPI(
        title="RAG Evaluation Platform",
        description="B/S RAG evaluation platform powered by deepeval",
        version="0.1.0",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173"],  # Vite dev server
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(router)

    @app.get("/health")
    async def health():
        return {"status": "ok"}

    return app


app = create_app()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
```

- [ ] **Step 2: Verify the app starts**

```bash
python -c "from app.main import app; print('App created OK')"
```

Expected: `App created OK`

- [ ] **Step 3: Verify health endpoint**

Run the server briefly to check:
```bash
python -c "
from app.main import app
from fastapi.testclient import TestClient
c = TestClient(app)
r = c.get('/health')
assert r.status_code == 200
assert r.json() == {'status': 'ok'}
print('Health check OK')
"
```

Expected: `Health check OK`

- [ ] **Step 4: Commit**

```bash
git add app/main.py
git commit -m "feat: add FastAPI main entry point"
```

---

### Task 11: Pipeline Integration Tests — Goldens Generation

**Files:**
- Create: `tests/fixtures/test_doc.txt`
- Create: `tests/test_pipeline_goldens.py`

- [ ] **Step 1: Write test fixture document**

Create `tests/fixtures/test_doc.txt` with ~200 words:

```
WidgetX Product Manual

WidgetX is a revolutionary task management application designed for small teams.
It features real-time collaboration, Kanban boards, and automated workflow triggers.

Getting Started:
To begin using WidgetX, create an account at widgetx.example.com. After logging in,
you can create your first project by clicking the "New Project" button on the dashboard.

Core Features:
1. Kanban Boards: Organize tasks into columns like "To Do", "In Progress", and "Done".
   Drag and drop tasks between columns to update their status.
2. Workflow Automation: Set up triggers that automatically move tasks, send notifications,
   or update fields when certain conditions are met.
3. Team Collaboration: Invite team members by email. Assign tasks, leave comments, and
   track progress together in real time.

Pricing:
WidgetX offers three tiers: Free (up to 5 users, 3 projects), Pro ($12/user/month),
and Enterprise (custom pricing with SSO and priority support).

Troubleshooting:
If tasks are not syncing, check your internet connection and refresh the page.
For login issues, use the "Forgot Password" link on the login page.
Contact support@widgetx.example.com for further assistance.
```

- [ ] **Step 2: Write test_pipeline_goldens.py**

```python
"""Integration test: generate goldens from a real document via Synthesizer."""

import pytest
from unittest.mock import patch, MagicMock


@pytest.mark.integration
class TestPipelineGoldensGeneration:
    def test_generate_goldens_from_fixture_doc(self, temp_data_dir):
        """Generate goldens from a real .txt document using actual deepeval Synthesizer."""
        from app.pipeline import build_evaluation_model, build_embedder
        from app.storage import save_uploaded_file
        from app.db import init_db, create_task, add_document, get_goldens
        from app.task_manager import task_manager, TaskPhase
        from app.config import CHUNK_SIZE, CHUNK_OVERLAP, MAX_GOLDENS_PER_CONTEXT

        import os

        # Requires DEEPSEEK_API_KEY set
        if not os.getenv("DEEPSEEK_API_KEY"):
            pytest.skip("DEEPSEEK_API_KEY not set")

        task_id = task_manager.start_task(
            rag_base_url="https://test.example.com",
            rag_api_key="sk-test",
        )

        # Save fixture doc
        fixture_path = os.path.join(
            os.path.dirname(__file__), "fixtures", "test_doc.txt"
        )
        with open(fixture_path, "rb") as f:
            content = f.read()
        file_path = save_uploaded_file(task_id, "test_doc.txt", content)
        add_document(task_id, "test_doc.txt", file_path, len(content))

        # Run the goldens generation part of the pipeline
        from deepeval.synthesizer import Synthesizer
        from deepeval.synthesizer.config import ContextConstructionConfig

        model = build_evaluation_model()
        embedder = build_embedder()

        synthesizer = Synthesizer(async_mode=False, model=model)
        context_config = ContextConstructionConfig(
            embedder=embedder,
            critic_model=model,
            chunk_size=CHUNK_SIZE,
            chunk_overlap=CHUNK_OVERLAP,
        )

        from app.storage import get_document_paths
        doc_paths = get_document_paths(task_id)

        goldens = synthesizer.generate_goldens_from_docs(
            document_paths=doc_paths,
            context_construction_config=context_config,
            max_goldens_per_context=MAX_GOLDENS_PER_CONTEXT,
        )

        assert len(goldens) > 0, "Synthesizer should produce at least 1 golden"

        # Save to DB
        import json
        for golden in goldens:
            from app.db import add_golden
            golden_id = add_golden(
                task_id,
                golden.input,
                golden.expected_output,
                json.dumps(golden.context) if golden.context else None,
            )
            assert golden_id > 0

        # Verify goldens in DB
        saved = get_goldens(task_id)
        assert len(saved) == len(goldens)
        assert saved[0]["input"]
        assert saved[0]["expected_output"]
```

- [ ] **Step 3: Run the integration test**

```bash
DEEPSEEK_API_KEY=<your_key> pytest tests/test_pipeline_goldens.py -v -m integration
```

Expected: PASS (if DEEPSEEK_API_KEY is set), otherwise SKIPPED.

- [ ] **Step 4: Commit**

```bash
git add tests/fixtures/test_doc.txt tests/test_pipeline_goldens.py
git commit -m "test: add pipeline golden generation integration test"
```

---

### Task 12: Pipeline Integration Tests — Full Evaluation

**Files:**
- Create: `tests/test_pipeline_evaluate.py`
- Create: `tests/test_pipeline_error.py`

- [ ] **Step 1: Write test_pipeline_evaluate.py**

```python
"""Integration test: run full evaluation pipeline with mock RAG API."""

import json
import pytest
from unittest.mock import patch, MagicMock


class TestPipelineEvaluate:
    def test_evaluate_with_mock_rag(self, temp_data_dir):
        """Run evaluation with mock RAG responses."""
        import os
        if not os.getenv("DEEPSEEK_API_KEY"):
            pytest.skip("DEEPSEEK_API_KEY not set")

        from app.pipeline import build_evaluation_model, build_test_case, collect_metric_scores
        from app.db import init_db, create_task, add_golden, save_eval_result, get_eval_results
        from app.storage import save_uploaded_file, add_document as save_doc_meta
        from app.rag_client import RAGResponse

        from deepeval.metrics import (
            AnswerRelevancyMetric,
            FaithfulnessMetric,
        )

        task_id = "integration-test-001"
        init_db(":memory:")

        # Pre-seed goldens
        gid1 = add_golden(
            task_id, "What is WidgetX?", "WidgetX is a task management app.", '["chunk1"]'
        )
        gid2 = add_golden(
            task_id, "How many pricing tiers?", "Three tiers: Free, Pro, Enterprise.", '["chunk2"]'
        )

        model = build_evaluation_model()
        metrics = [
            AnswerRelevancyMetric(model=model),
            FaithfulnessMetric(model=model),
        ]

        # Test case 1: mock RAG response
        test_case_1 = build_test_case(
            input_text="What is WidgetX?",
            actual_output="WidgetX is a task management application.",
            retrieval_context=["WidgetX is a revolutionary task management application."],
            expected_output="WidgetX is a task management app.",
        )

        from deepeval.evaluate import evaluate
        results = evaluate([test_case_1], metrics)

        assert len(results) == 1
        scores, passed = collect_metric_scores(results[0])
        assert "AnswerRelevancyMetric" in scores
        assert "FaithfulnessMetric" in scores
        assert 0.0 <= scores["AnswerRelevancyMetric"] <= 1.0

        # Save result
        save_eval_result(
            task_id, gid1,
            actual_output="WidgetX is a task management application.",
            retrieval_context=json.dumps(["WidgetX is a revolutionary task management application."]),
            metrics=scores,
            passed=passed,
        )

        db_results = get_eval_results(task_id)
        assert len(db_results) == 1
```

- [ ] **Step 2: Write test_pipeline_error.py**

```python
"""Integration tests for error handling in the pipeline."""

import pytest
from app.pipeline import run_evaluation_pipeline


class TestPipelineErrors:
    def test_empty_docs_raises(self, temp_data_dir):
        """Pipeline should fail gracefully with empty documents."""
        from app.task_manager import task_manager
        task_id = task_manager.start_task("http://test.com", "sk")
        # Don't upload any documents — pipeline should handle this

        import asyncio
        async def run():
            await run_evaluation_pipeline(task_id)

        asyncio.run(run())

        state = task_manager.get_state(task_id)
        assert state["status"] == "FAILED"
        assert state["error_message"] is not None
```

- [ ] **Step 3: Run integration tests**

```bash
DEEPSEEK_API_KEY=<your_key> pytest tests/test_pipeline_evaluate.py tests/test_pipeline_error.py -v
```

Expected: Integration test PASS (with key) or SKIP (without key). Error test PASS.

- [ ] **Step 4: Commit**

```bash
git add tests/test_pipeline_evaluate.py tests/test_pipeline_error.py
git commit -m "test: add pipeline evaluation and error integration tests"
```

---

### Task 13: Frontend Scaffolding

**Files:**
- Create: `frontend/` (Vite project)

- [ ] **Step 1: Create Vite + React + TypeScript project**

```bash
cd frontend
npm create vite@latest . -- --template react-ts
npm install
```

Expected: Vite project created, `npm run dev` works.

- [ ] **Step 2: Install frontend dependencies**

```bash
cd frontend
npm install react-router-dom @tanstack/react-query recharts lucide-react
npm install -D tailwindcss @tailwindcss/vite postcss autoprefixer
npm install -D vitest @testing-library/react @testing-library/jest-dom @testing-library/user-event jsdom msw
```

Expected: All packages install.

- [ ] **Step 3: Initialize Tailwind + shadcn/ui**

```bash
cd frontend
npx tailwindcss init -p
npx shadcn@latest init -d
```

- [ ] **Step 4: Install shadcn/ui components**

```bash
cd frontend
npx shadcn@latest add button card input form label progress tabs table badge separator scroll-area
```

- [ ] **Step 5: Configure test setup**

Create `frontend/src/test-setup.ts`:
```typescript
import '@testing-library/jest-dom';
```

Update `vite.config.ts`:
```typescript
/// <reference types="vitest" />
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  test: {
    environment: 'jsdom',
    setupFiles: ['./src/test-setup.ts'],
    globals: true,
  },
})
```

- [ ] **Step 6: Verify dev server starts**

```bash
cd frontend && npm run dev
```

Expected: Vite dev server running at `http://localhost:5173`.

- [ ] **Step 7: Commit**

```bash
git add frontend/
git commit -m "feat: scaffold frontend with Vite, React, Tailwind, shadcn/ui"
```

---

### Task 14: Frontend API Client and Shared Types

**Files:**
- Create: `frontend/src/types/index.ts`
- Create: `frontend/src/api/client.ts`
- Create: `frontend/src/hooks/useApi.ts`

- [ ] **Step 1: Write types/index.ts**

```typescript
export interface UploadedFile {
  id: number;
  filename: string;
  file_size: number;
}

export interface UploadResponse {
  task_id: string;
  files: UploadedFile[];
}

export interface EvaluateRequest {
  rag_base_url: string;
  rag_api_key: string;
  task_id: string;
}

export interface EvaluateResponse {
  task_id: string;
}

export interface TaskStatus {
  task_id: string;
  status: string;
  phase: string;
  progress: number;
  error_message: string | null;
  created_at: string | null;
  completed_at: string | null;
}

export interface GoldenItem {
  id: number;
  input: string;
  expected_output: string;
  context: string | null;
}

export interface MetricScore {
  name: string;
  score: number;
  passed: boolean;
}

export interface EvalResultItem {
  id: number;
  golden_id: number;
  input: string;
  expected_output: string;
  actual_output: string;
  retrieval_context: string | null;
  metrics: MetricScore[];
  passed: boolean;
}

export interface TaskResult {
  task_id: string;
  status: string;
  overall_scores: MetricScore[];
  details: EvalResultItem[];
}

export interface HistoryItem {
  task_id: string;
  status: string;
  rag_base_url: string;
  created_at: string | null;
  completed_at: string | null;
}
```

- [ ] **Step 2: Write api/client.ts**

```typescript
const API_BASE = 'http://localhost:8000/api';

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { 'Content-Type': 'application/json', ...options?.headers },
    ...options,
  });
  if (!res.ok) {
    const detail = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(detail.detail || `HTTP ${res.status}`);
  }
  return res.json();
}

export async function uploadFiles(files: FileList | File[]): Promise<UploadResponse> {
  const form = new FormData();
  Array.from(files).forEach((f) => form.append('files', f));
  const res = await fetch(`${API_BASE}/upload`, { method: 'POST', body: form });
  if (!res.ok) throw new Error((await res.json()).detail || 'Upload failed');
  return res.json();
}

export const api = {
  upload: uploadFiles,

  evaluate: (data: EvaluateRequest) =>
    request<EvaluateResponse>('/evaluate', { method: 'POST', body: JSON.stringify(data) }),

  getTask: (taskId: string) =>
    request<TaskStatus>(`/task/${taskId}`),

  getGoldens: (taskId: string) =>
    request<GoldenItem[]>(`/goldens/${taskId}`),

  confirmGoldens: (taskId: string) =>
    request<{ status: string }>(`/goldens/${taskId}/confirm`, { method: 'POST' }),

  getResults: (taskId: string) =>
    request<TaskResult>(`/results/${taskId}`),

  getHistory: () =>
    request<HistoryItem[]>('/history'),
};
```

- [ ] **Step 3: Write hooks/useApi.ts**

```typescript
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '../api/client';
import type { EvaluateRequest, TaskStatus, GoldenItem, TaskResult, HistoryItem } from '../types';

export function useTaskPolling(taskId: string | null, enabled: boolean) {
  return useQuery<TaskStatus>({
    queryKey: ['task', taskId],
    queryFn: () => api.getTask(taskId!),
    enabled: !!taskId && enabled,
    refetchInterval: (query) => {
      const data = query.state.data;
      if (!data) return 2000;
      if (['COMPLETED', 'FAILED'].includes(data.status)) return false;
      return 2000;
    },
  });
}

export function useGoldens(taskId: string | null) {
  return useQuery<GoldenItem[]>({
    queryKey: ['goldens', taskId],
    queryFn: () => api.getGoldens(taskId!),
    enabled: !!taskId,
  });
}

export function useResults(taskId: string | null) {
  return useQuery<TaskResult>({
    queryKey: ['results', taskId],
    queryFn: () => api.getResults(taskId!),
    enabled: !!taskId,
  });
}

export function useHistory() {
  return useQuery<HistoryItem[]>({
    queryKey: ['history'],
    queryFn: api.getHistory,
  });
}

export function useConfirmGoldens() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (taskId: string) => api.confirmGoldens(taskId),
    onSuccess: (_data, taskId) => {
      qc.invalidateQueries({ queryKey: ['task', taskId] });
    },
  });
}

export function useStartEvaluation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (req: EvaluateRequest) => api.evaluate(req),
    onSuccess: (data) => {
      qc.invalidateQueries({ queryKey: ['task', data.task_id] });
    },
  });
}
```

- [ ] **Step 4: Verify TypeScript compiles**

```bash
cd frontend && npx tsc --noEmit
```

Expected: No type errors.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/api/ frontend/src/types/ frontend/src/hooks/
git commit -m "feat: add frontend API client, types, and TanStack Query hooks"
```

---

### Task 15: Frontend Config Page

**Files:**
- Create: `frontend/src/pages/ConfigPage.tsx`
- Create: `frontend/src/components/RagConfigForm.tsx`
- Create: `frontend/src/components/FileUploader.tsx`
- Create: `frontend/src/components/Layout.tsx`
- Modify: `frontend/src/App.tsx`

- [ ] **Step 1: Write component tests**

Create `frontend/src/__tests__/test-utils.tsx`:
```typescript
import { ReactElement } from 'react';
import { render, RenderOptions } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';

function createTestQueryClient() {
  return new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
}

export function renderWithProviders(ui: ReactElement, options?: RenderOptions) {
  const queryClient = createTestQueryClient();
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>{ui}</MemoryRouter>
    </QueryClientProvider>,
    options
  );
}

export { render as bareRender } from '@testing-library/react';
```

Create `frontend/src/__tests__/RagConfigForm.test.tsx`:
```typescript
import { describe, it, expect, vi } from 'vitest';
import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { renderWithProviders } from './test-utils';
import { RagConfigForm } from '../components/RagConfigForm';

describe('RagConfigForm', () => {
  it('renders url and api key inputs', () => {
    renderWithProviders(<RagConfigForm onSubmit={vi.fn()} />);
    expect(screen.getByLabelText(/base url/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/api key/i)).toBeInTheDocument();
  });

  it('calls onSubmit with form data when valid', async () => {
    const onSubmit = vi.fn();
    renderWithProviders(<RagConfigForm onSubmit={onSubmit} />);
    const user = userEvent.setup();

    await user.type(screen.getByLabelText(/base url/i), 'https://rag.test.com/v1');
    await user.type(screen.getByLabelText(/api key/i), 'sk-test-123');
    await user.click(screen.getByRole('button', { name: /save/i }));

    expect(onSubmit).toHaveBeenCalledWith({
      rag_base_url: 'https://rag.test.com/v1',
      rag_api_key: 'sk-test-123',
    });
  });

  it('shows validation error when fields are empty', async () => {
    const onSubmit = vi.fn();
    renderWithProviders(<RagConfigForm onSubmit={onSubmit} />);
    const user = userEvent.setup();

    await user.click(screen.getByRole('button', { name: /save/i }));
    expect(onSubmit).not.toHaveBeenCalled();
  });
});
```

Create `frontend/src/__tests__/FileUploader.test.tsx`:
```typescript
import { describe, it, expect, vi } from 'vitest';
import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { renderWithProviders } from './test-utils';
import { FileUploader } from '../components/FileUploader';

describe('FileUploader', () => {
  it('renders drop zone', () => {
    renderWithProviders(<FileUploader onUpload={vi.fn()} />);
    expect(screen.getByText(/drag.*file/i)).toBeInTheDocument();
  });

  it('shows uploaded file names', () => {
    renderWithProviders(
      <FileUploader
        onUpload={vi.fn()}
        files={[{ id: 1, filename: 'doc.txt', file_size: 1024 }]}
      />
    );
    expect(screen.getByText('doc.txt')).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd frontend && npx vitest run
```

Expected: FAIL — components not implemented

- [ ] **Step 3: Write Layout.tsx**

```tsx
import { NavLink, Outlet } from 'react-router-dom';
import { useHistory } from '../hooks/useApi';
import { ScrollArea } from '@/components/ui/scroll-area';
import { ClipboardList, History } from 'lucide-react';

export function Layout() {
  const { data: history } = useHistory();

  return (
    <div className="flex h-screen bg-slate-50">
      <aside className="w-64 border-r bg-white p-4 flex flex-col gap-4">
        <h1 className="text-lg font-bold flex items-center gap-2">
          <ClipboardList className="w-5 h-5" /> RAG Eval
        </h1>
        <nav className="flex flex-col gap-1">
          <NavLink
            to="/"
            className={({ isActive }) =>
              `px-3 py-2 rounded-md text-sm ${isActive ? 'bg-slate-100 font-medium' : 'hover:bg-slate-50'}`
            }
          >
            New Evaluation
          </NavLink>
        </nav>
        <div className="flex items-center gap-2 text-sm text-slate-500 mt-4">
          <History className="w-4 h-4" /> History
        </div>
        <ScrollArea className="flex-1">
          {history?.map((item) => (
            <NavLink
              key={item.task_id}
              to={`/task/${item.task_id}/results`}
              className="block px-3 py-1.5 text-xs text-slate-600 hover:bg-slate-50 rounded truncate"
            >
              {item.task_id.slice(0, 8)}... — {item.status}
            </NavLink>
          ))}
        </ScrollArea>
      </aside>
      <main className="flex-1 overflow-auto p-8">
        <Outlet />
      </main>
    </div>
  );
}
```

- [ ] **Step 4: Write RagConfigForm.tsx**

```tsx
import { useState, FormEvent } from 'react';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';

interface RagConfig {
  rag_base_url: string;
  rag_api_key: string;
}

interface Props {
  onSubmit: (config: RagConfig) => void;
}

export function RagConfigForm({ onSubmit }: Props) {
  const [url, setUrl] = useState('');
  const [key, setKey] = useState('');
  const [errors, setErrors] = useState<Record<string, string>>({});

  function handleSubmit(e: FormEvent) {
    e.preventDefault();
    const errs: Record<string, string> = {};
    if (!url.trim()) errs.url = 'Base URL is required';
    if (!key.trim()) errs.key = 'API key is required';
    if (Object.keys(errs).length) {
      setErrors(errs);
      return;
    }
    setErrors({});
    onSubmit({ rag_base_url: url.trim(), rag_api_key: key.trim() });
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>RAG Service Configuration</CardTitle>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <Label htmlFor="base-url">Base URL</Label>
            <Input
              id="base-url"
              placeholder="https://your-rag-service.com/v1"
              value={url}
              onChange={(e) => setUrl(e.target.value)}
            />
            {errors.url && <p className="text-red-500 text-sm mt-1">{errors.url}</p>}
          </div>
          <div>
            <Label htmlFor="api-key">API Key</Label>
            <Input
              id="api-key"
              type="password"
              placeholder="sk-..."
              value={key}
              onChange={(e) => setKey(e.target.value)}
            />
            {errors.key && <p className="text-red-500 text-sm mt-1">{errors.key}</p>}
          </div>
          <Button type="submit">Save Configuration</Button>
        </form>
      </CardContent>
    </Card>
  );
}
```

- [ ] **Step 5: Write FileUploader.tsx**

```tsx
import { useCallback, useState } from 'react';
import { Card, CardContent } from '@/components/ui/card';
import { Upload, FileText, X } from 'lucide-react';
import type { UploadedFile } from '../types';

interface Props {
  onUpload: (files: File[]) => Promise<void>;
  files?: UploadedFile[];
  disabled?: boolean;
}

export function FileUploader({ onUpload, files = [], disabled }: Props) {
  const [dragging, setDragging] = useState(false);

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setDragging(false);
      if (disabled) return;
      const dropped = Array.from(e.dataTransfer.files);
      onUpload(dropped);
    },
    [onUpload, disabled]
  );

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      onUpload(Array.from(e.target.files));
    }
  };

  return (
    <Card>
      <CardContent className="p-6">
        <div
          className={`border-2 border-dashed rounded-lg p-8 text-center transition-colors ${
            dragging ? 'border-blue-500 bg-blue-50' : 'border-slate-300'
          } ${disabled ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}`}
          onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
          onDragLeave={() => setDragging(false)}
          onDrop={handleDrop}
        >
          <Upload className="mx-auto w-8 h-8 text-slate-400 mb-2" />
          <p className="text-sm text-slate-600">
            Drag & drop knowledge base files here, or{' '}
            <label className="text-blue-600 hover:underline cursor-pointer">
              browse
              <input
                type="file"
                multiple
                accept=".txt,.md,.pdf,.json,.csv,.rst,.html"
                className="hidden"
                onChange={handleChange}
                disabled={disabled}
              />
            </label>
          </p>
          <p className="text-xs text-slate-400 mt-1">
            Supported: .txt, .md, .pdf, .json, .csv
          </p>
        </div>

        {files.length > 0 && (
          <div className="mt-4 space-y-2">
            {files.map((f) => (
              <div key={f.id} className="flex items-center gap-2 text-sm text-slate-700">
                <FileText className="w-4 h-4 text-slate-400" />
                <span className="flex-1 truncate">{f.filename}</span>
                <span className="text-xs text-slate-400">{(f.file_size / 1024).toFixed(1)} KB</span>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
```

- [ ] **Step 6: Write ConfigPage.tsx**

```tsx
import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { RagConfigForm } from '../components/RagConfigForm';
import { FileUploader } from '../components/FileUploader';
import { Button } from '@/components/ui/button';
import { api } from '../api/client';
import { useStartEvaluation } from '../hooks/useApi';
import type { UploadedFile } from '../types';
import { Loader2 } from 'lucide-react';

export function ConfigPage() {
  const navigate = useNavigate();
  const [ragConfig, setRagConfig] = useState<{ rag_base_url: string; rag_api_key: string } | null>(null);
  const [files, setFiles] = useState<UploadedFile[]>([]);
  const [taskId, setTaskId] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false);
  const startEval = useStartEvaluation();

  async function handleUpload(newFiles: File[]) {
    setUploading(true);
    try {
      const resp = await api.upload(newFiles);
      setFiles(resp.files);
      setTaskId(resp.task_id);
    } catch (err) {
      alert(`Upload failed: ${err}`);
    } finally {
      setUploading(false);
    }
  }

  async function handleStart() {
    if (!ragConfig || !taskId) return;
    try {
      await startEval.mutateAsync({
        rag_base_url: ragConfig.rag_base_url,
        rag_api_key: ragConfig.rag_api_key,
        task_id: taskId,
      });
      navigate(`/task/${taskId}/progress`);
    } catch (err) {
      alert(`Failed to start evaluation: ${err}`);
    }
  }

  const canStart = ragConfig && files.length > 0 && taskId;

  return (
    <div className="max-w-2xl mx-auto space-y-6">
      <h2 className="text-2xl font-bold">RAG Evaluation</h2>

      <RagConfigForm onSubmit={setRagConfig} />

      <FileUploader onUpload={handleUpload} files={files} disabled={uploading} />

      <Button
        size="lg"
        className="w-full"
        disabled={!canStart || startEval.isPending}
        onClick={handleStart}
      >
        {startEval.isPending && <Loader2 className="w-4 h-4 mr-2 animate-spin" />}
        Start Evaluation
      </Button>
    </div>
  );
}
```

- [ ] **Step 7: Update App.tsx**

```tsx
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Layout } from './components/Layout';
import { ConfigPage } from './pages/ConfigPage';
import { GoldensPage } from './pages/GoldensPage';
import { ProgressPage } from './pages/ProgressPage';
import { ResultsPage } from './pages/ResultsPage';

const queryClient = new QueryClient({
  defaultOptions: { queries: { retry: 1, staleTime: 5000 } },
});

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          <Route element={<Layout />}>
            <Route path="/" element={<ConfigPage />} />
            <Route path="/task/:taskId/goldens" element={<GoldensPage />} />
            <Route path="/task/:taskId/progress" element={<ProgressPage />} />
            <Route path="/task/:taskId/results" element={<ResultsPage />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  );
}

export default App;
```

- [ ] **Step 8: Run component tests**

```bash
cd frontend && npx vitest run src/__tests__/RagConfigForm.test.tsx src/__tests__/FileUploader.test.tsx
```

Expected: PASS (2 test files)

- [ ] **Step 9: Commit**

```bash
git add frontend/src/
git commit -m "feat: add config page, RAG form, file uploader, and layout"
```

---

### Task 16: Frontend Goldens, Progress, and Results Pages

**Files:**
- Create: `frontend/src/pages/GoldensPage.tsx`
- Create: `frontend/src/pages/ProgressPage.tsx`
- Create: `frontend/src/pages/ResultsPage.tsx`
- Create: `frontend/src/components/GoldenCard.tsx`
- Create: `frontend/src/components/ConfirmButton.tsx`
- Create: `frontend/src/components/ProgressTracker.tsx`
- Create: `frontend/src/components/ScoreCard.tsx`
- Create: `frontend/src/components/MetricsRadarChart.tsx`
- Create: `frontend/src/components/DetailTable.tsx`

- [ ] **Step 1: Write GoldenCard.tsx**

```tsx
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';

interface Props {
  index: number;
  input: string;
  expectedOutput: string;
  context?: string | null;
}

export function GoldenCard({ index, input, expectedOutput, context }: Props) {
  let parsedContext: string[] = [];
  if (context) {
    try { parsedContext = JSON.parse(context); } catch { parsedContext = [context]; }
  }

  return (
    <Card>
      <CardContent className="p-4 space-y-3">
        <div className="flex items-center gap-2">
          <Badge variant="secondary">#{index + 1}</Badge>
          <span className="text-sm font-medium text-slate-900">Q: {input}</span>
        </div>
        <div>
          <span className="text-xs font-medium text-slate-500">Expected Answer:</span>
          <p className="text-sm text-slate-700 mt-0.5">{expectedOutput}</p>
        </div>
        {parsedContext.length > 0 && (
          <div>
            <span className="text-xs font-medium text-slate-500">Source Chunks:</span>
            <div className="mt-1 space-y-1">
              {parsedContext.slice(0, 3).map((c, i) => (
                <p key={i} className="text-xs text-slate-500 bg-slate-50 p-1.5 rounded line-clamp-1">
                  {c}
                </p>
              ))}
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
```

- [ ] **Step 2: Write ConfirmButton.tsx**

```tsx
import { Button } from '@/components/ui/button';
import { Loader2, CheckCircle } from 'lucide-react';

interface Props {
  onClick: () => void;
  loading: boolean;
  disabled: boolean;
  goldensCount: number;
}

export function ConfirmButton({ onClick, loading, disabled, goldensCount }: Props) {
  return (
    <Button
      size="lg"
      onClick={onClick}
      disabled={disabled || loading || goldensCount === 0}
      className="w-full"
    >
      {loading && <Loader2 className="w-4 h-4 mr-2 animate-spin" />}
      {!loading && <CheckCircle className="w-4 h-4 mr-2" />}
      Confirm {goldensCount} Goldens & Run Evaluation
    </Button>
  );
}
```

- [ ] **Step 3: Write ProgressTracker.tsx**

```tsx
import { Progress } from '@/components/ui/progress';
import { Badge } from '@/components/ui/badge';
import { CheckCircle2, Loader2, Circle, XCircle } from 'lucide-react';

const PHASES = [
  { key: 'UPLOADING', label: 'Uploading' },
  { key: 'GENERATING_GOLDENS', label: 'Generating Goldens' },
  { key: 'AWAITING_CONFIRM', label: 'Review Goldens' },
  { key: 'RUNNING_EVAL', label: 'Running Evaluation' },
  { key: 'COMPLETED', label: 'Completed' },
];

interface Props {
  phase: string;
  progress: number;
  status: string;
}

export function ProgressTracker({ phase, progress, status }: Props) {
  const currentIdx = PHASES.findIndex((p) => p.key === phase);

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-4">
        <Progress value={progress * 100} className="flex-1" />
        <span className="text-sm text-slate-500">{Math.round(progress * 100)}%</span>
      </div>

      <div className="space-y-3">
        {PHASES.map((p, i) => {
          let Icon = Circle;
          let color = 'text-slate-300';
          if (status === 'FAILED' && i === currentIdx) {
            Icon = XCircle;
            color = 'text-red-500';
          } else if (i < currentIdx || status === 'COMPLETED') {
            Icon = CheckCircle2;
            color = 'text-green-500';
          } else if (i === currentIdx) {
            Icon = Loader2;
            color = 'text-blue-500 animate-spin';
          }
          return (
            <div key={p.key} className="flex items-center gap-3">
              <Icon className={`w-5 h-5 ${color}`} />
              <span className={`text-sm ${i <= currentIdx ? 'text-slate-900 font-medium' : 'text-slate-400'}`}>
                {p.label}
              </span>
              {i === currentIdx && <Badge variant="secondary">Current</Badge>}
            </div>
          );
        })}
      </div>
    </div>
  );
}
```

- [ ] **Step 4: Write ScoreCard.tsx**

```tsx
import { Card, CardContent } from '@/components/ui/card';

interface Props {
  name: string;
  score: number;
}

function scoreColor(s: number): string {
  if (s >= 0.8) return 'text-green-600';
  if (s >= 0.6) return 'text-yellow-600';
  return 'text-red-600';
}

export function ScoreCard({ name, score }: Props) {
  return (
    <Card>
      <CardContent className="p-4 text-center">
        <p className="text-sm text-slate-500 mb-1">{name}</p>
        <p className={`text-3xl font-bold ${scoreColor(score)}`}>
          {(score * 100).toFixed(1)}%
        </p>
      </CardContent>
    </Card>
  );
}
```

- [ ] **Step 5: Write MetricsRadarChart.tsx**

```tsx
import { RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, Radar, ResponsiveContainer } from 'recharts';

interface Props {
  scores: { name: string; score: number }[];
}

export function MetricsRadarChart({ scores }: Props) {
  const data = scores.map((s) => ({ metric: s.name, value: s.score * 100 }));

  return (
    <div className="w-full h-80">
      <ResponsiveContainer>
        <RadarChart data={data}>
          <PolarGrid />
          <PolarAngleAxis dataKey="metric" tick={{ fontSize: 11 }} />
          <PolarRadiusAxis angle={90} domain={[0, 100]} />
          <Radar name="Score" dataKey="value" stroke="#3b82f6" fill="#3b82f6" fillOpacity={0.3} />
        </RadarChart>
      </ResponsiveContainer>
    </div>
  );
}
```

- [ ] **Step 6: Write DetailTable.tsx**

```tsx
import { useState } from 'react';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Badge } from '@/components/ui/badge';
import type { EvalResultItem } from '../types';
import { ChevronDown, ChevronRight } from 'lucide-react';

interface Props {
  details: EvalResultItem[];
}

export function DetailTable({ details }: Props) {
  const [expanded, setExpanded] = useState<Set<number>>(new Set());

  function toggle(id: number) {
    setExpanded((prev) => {
      const next = new Set(prev);
      next.has(id) ? next.delete(id) : next.add(id);
      return next;
    });
  }

  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead className="w-8" />
          <TableHead>Input</TableHead>
          <TableHead>Expected Output</TableHead>
          <TableHead className="text-right">Passed</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {details.map((d) => (
          <>
            <TableRow key={d.id} className="cursor-pointer hover:bg-slate-50" onClick={() => toggle(d.id)}>
              <TableCell>
                {expanded.has(d.id) ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
              </TableCell>
              <TableCell className="max-w-40 truncate">{d.input}</TableCell>
              <TableCell className="max-w-40 truncate">{d.expected_output}</TableCell>
              <TableCell className="text-right">
                <Badge variant={d.passed ? 'default' : 'destructive'}>
                  {d.passed ? 'Pass' : 'Fail'}
                </Badge>
              </TableCell>
            </TableRow>
            {expanded.has(d.id) && (
              <TableRow key={`${d.id}-expanded`}>
                <TableCell colSpan={4} className="bg-slate-50 p-4">
                  <div className="space-y-2">
                    <p><strong>Actual Output:</strong> {d.actual_output}</p>
                    <div className="flex gap-2 flex-wrap">
                      {d.metrics.map((m) => (
                        <Badge key={m.name} variant="outline">
                          {m.name}: {(m.score * 100).toFixed(0)}%
                        </Badge>
                      ))}
                    </div>
                  </div>
                </TableCell>
              </TableRow>
            )}
          </>
        ))}
      </TableBody>
    </Table>
  );
}
```

- [ ] **Step 7: Write GoldensPage.tsx**

```tsx
import { useParams, useNavigate } from 'react-router-dom';
import { useGoldens, useConfirmGoldens } from '../hooks/useApi';
import { GoldenCard } from '../components/GoldenCard';
import { ConfirmButton } from '../components/ConfirmButton';
import { ScrollArea } from '@/components/ui/scroll-area';
import { AlertCircle } from 'lucide-react';

export function GoldensPage() {
  const { taskId } = useParams<{ taskId: string }>();
  const navigate = useNavigate();
  const { data: goldens, isLoading } = useGoldens(taskId ?? null);
  const confirm = useConfirmGoldens();

  async function handleConfirm() {
    if (!taskId) return;
    await confirm.mutateAsync(taskId);
    navigate(`/task/${taskId}/progress`);
  }

  if (isLoading) return <p className="text-center text-slate-500 py-8">Loading goldens...</p>;

  return (
    <div className="max-w-2xl mx-auto space-y-6">
      <div className="flex items-center gap-3">
        <AlertCircle className="w-5 h-5 text-blue-600" />
        <div>
          <h2 className="text-xl font-bold">Review Generated Goldens</h2>
          <p className="text-sm text-slate-500">
            {goldens?.length ?? 0} question-answer pairs generated from your documents.
            Review them before running the full evaluation.
          </p>
        </div>
      </div>

      <ScrollArea className="h-[50vh]">
        <div className="space-y-3">
          {goldens?.map((g, i) => (
            <GoldenCard key={g.id} index={i} {...g} expectedOutput={g.expected_output} />
          ))}
        </div>
      </ScrollArea>

      <ConfirmButton
        onClick={handleConfirm}
        loading={confirm.isPending}
        disabled={!goldens || goldens.length === 0}
        goldensCount={goldens?.length ?? 0}
      />
    </div>
  );
}
```

- [ ] **Step 8: Write ProgressPage.tsx**

```tsx
import { useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useTaskPolling } from '../hooks/useApi';
import { ProgressTracker } from '../components/ProgressTracker';

export function ProgressPage() {
  const { taskId } = useParams<{ taskId: string }>();
  const navigate = useNavigate();
  const { data: status } = useTaskPolling(taskId ?? null, true);

  useEffect(() => {
    if (!status) return;
    if (status.status === 'AWAITING_CONFIRM') {
      navigate(`/task/${taskId}/goldens`);
    } else if (status.status === 'COMPLETED') {
      navigate(`/task/${taskId}/results`);
    }
  }, [status, taskId, navigate]);

  if (!status) return <p className="text-center text-slate-500 py-8">Loading...</p>;

  return (
    <div className="max-w-xl mx-auto space-y-6">
      <h2 className="text-xl font-bold">Evaluation Progress</h2>
      <ProgressTracker phase={status.phase} progress={status.progress} status={status.status} />
      {status.error_message && (
        <p className="text-red-600 text-sm bg-red-50 p-3 rounded">{status.error_message}</p>
      )}
    </div>
  );
}
```

- [ ] **Step 9: Write ResultsPage.tsx**

```tsx
import { useParams } from 'react-router-dom';
import { useResults } from '../hooks/useApi';
import { ScoreCard } from '../components/ScoreCard';
import { MetricsRadarChart } from '../components/MetricsRadarChart';
import { DetailTable } from '../components/DetailTable';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';

export function ResultsPage() {
  const { taskId } = useParams<{ taskId: string }>();
  const { data: results, isLoading } = useResults(taskId ?? null);

  if (isLoading || !results) {
    return <p className="text-center text-slate-500 py-8">Loading results...</p>;
  }

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      <h2 className="text-2xl font-bold">Evaluation Results</h2>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        {results.overall_scores.map((s) => (
          <ScoreCard key={s.name} name={s.name} score={s.score} />
        ))}
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <Card>
          <CardHeader><CardTitle className="text-base">Metrics Overview</CardTitle></CardHeader>
          <CardContent>
            <MetricsRadarChart scores={results.overall_scores} />
          </CardContent>
        </Card>
        <Card>
          <CardHeader><CardTitle className="text-base">Summary</CardTitle></CardHeader>
          <CardContent className="space-y-2 text-sm">
            <p>Total Test Cases: <strong>{results.details.length}</strong></p>
            <p>Passed: <strong>{results.details.filter((d) => d.passed).length}</strong></p>
            <p>Failed: <strong>{results.details.filter((d) => !d.passed).length}</strong></p>
          </CardContent>
        </Card>
      </div>

      <Tabs defaultValue="details">
        <TabsList>
          <TabsTrigger value="details">Per-Question Breakdown</TabsTrigger>
        </TabsList>
        <TabsContent value="details">
          <DetailTable details={results.details} />
        </TabsContent>
      </Tabs>
    </div>
  );
}
```

- [ ] **Step 10: Verify TypeScript compiles**

```bash
cd frontend && npx tsc --noEmit
```

Expected: No errors.

- [ ] **Step 11: Commit**

```bash
git add frontend/src/pages/ frontend/src/components/
git commit -m "feat: add Goldens, Progress, and Results pages with components"
```

---

### Task 17: Frontend Component Tests

**Files:**
- Create: `frontend/src/__tests__/GoldenCard.test.tsx`
- Create: `frontend/src/__tests__/ConfirmButton.test.tsx`
- Create: `frontend/src/__tests__/ScoreCard.test.tsx`
- Create: `frontend/src/__tests__/ProgressTracker.test.tsx`

- [ ] **Step 1: Write GoldenCard.test.tsx**

```tsx
import { describe, it, expect } from 'vitest';
import { screen } from '@testing-library/react';
import { renderWithProviders } from './test-utils';
import { GoldenCard } from '../components/GoldenCard';

describe('GoldenCard', () => {
  it('renders input and expected output', () => {
    renderWithProviders(
      <GoldenCard index={0} input="What is X?" expectedOutput="X is a thing." />
    );
    expect(screen.getByText(/What is X\?/)).toBeInTheDocument();
    expect(screen.getByText('X is a thing.')).toBeInTheDocument();
  });

  it('shows context when provided', () => {
    renderWithProviders(
      <GoldenCard index={0} input="Q" expectedOutput="A" context='["chunk 1", "chunk 2"]' />
    );
    expect(screen.getByText('chunk 1')).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Write ConfirmButton.test.tsx**

```tsx
import { describe, it, expect, vi } from 'vitest';
import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { renderWithProviders } from './test-utils';
import { ConfirmButton } from '../components/ConfirmButton';

describe('ConfirmButton', () => {
  it('calls onClick when clicked', async () => {
    const onClick = vi.fn();
    renderWithProviders(
      <ConfirmButton onClick={onClick} loading={false} disabled={false} goldensCount={5} />
    );
    await userEvent.click(screen.getByRole('button'));
    expect(onClick).toHaveBeenCalledOnce();
  });

  it('is disabled when goldensCount is 0', () => {
    renderWithProviders(
      <ConfirmButton onClick={vi.fn()} loading={false} disabled={false} goldensCount={0} />
    );
    expect(screen.getByRole('button')).toBeDisabled();
  });

  it('shows loading state', () => {
    renderWithProviders(
      <ConfirmButton onClick={vi.fn()} loading={true} disabled={false} goldensCount={3} />
    );
    expect(screen.getByRole('button')).toBeDisabled();
  });
});
```

- [ ] **Step 3: Write ScoreCard.test.tsx**

```tsx
import { describe, it, expect } from 'vitest';
import { screen } from '@testing-library/react';
import { renderWithProviders } from './test-utils';
import { ScoreCard } from '../components/ScoreCard';

describe('ScoreCard', () => {
  it('renders metric name and score', () => {
    renderWithProviders(<ScoreCard name="Faithfulness" score={0.92} />);
    expect(screen.getByText('Faithfulness')).toBeInTheDocument();
    expect(screen.getByText('92.0%')).toBeInTheDocument();
  });

  it('uses green for high scores', () => {
    renderWithProviders(<ScoreCard name="Test" score={0.85} />);
    expect(screen.getByText('85.0%')).toHaveClass('text-green-600');
  });

  it('uses red for low scores', () => {
    renderWithProviders(<ScoreCard name="Test" score={0.45} />);
    expect(screen.getByText('45.0%')).toHaveClass('text-red-600');
  });
});
```

- [ ] **Step 4: Write ProgressTracker.test.tsx**

```tsx
import { describe, it, expect } from 'vitest';
import { screen } from '@testing-library/react';
import { renderWithProviders } from './test-utils';
import { ProgressTracker } from '../components/ProgressTracker';

describe('ProgressTracker', () => {
  it('shows all phases', () => {
    renderWithProviders(
      <ProgressTracker phase="GENERATING_GOLDENS" progress={0.3} status="GENERATING_GOLDENS" />
    );
    expect(screen.getByText('Generating Goldens')).toBeInTheDocument();
    expect(screen.getByText('Running Evaluation')).toBeInTheDocument();
  });

  it('shows progress percentage', () => {
    renderWithProviders(
      <ProgressTracker phase="RUNNING_EVAL" progress={0.75} status="RUNNING_EVAL" />
    );
    expect(screen.getByText('75%')).toBeInTheDocument();
  });
});
```

- [ ] **Step 5: Run all component tests**

```bash
cd frontend && npx vitest run
```

Expected: All tests PASS (6 component test files)

- [ ] **Step 6: Commit**

```bash
git add frontend/src/__tests__/
git commit -m "test: add frontend component tests"
```

---

### Task 18: Frontend User Flow Tests

**Files:**
- Create: `frontend/src/__tests__/user-flows.test.tsx`
- Create: `frontend/src/mocks/handlers.ts`
- Create: `frontend/src/mocks/fixtures.ts`

- [ ] **Step 1: Write mocks/fixtures.ts**

```typescript
import type { TaskStatus, GoldenItem, TaskResult, HistoryItem, UploadResponse } from '../types';

export const MOCK_TASK_ID = 'abc123def456abc123def456abc123de';

export const mockUploadResponse: UploadResponse = {
  task_id: MOCK_TASK_ID,
  files: [{ id: 1, filename: 'test.txt', file_size: 1024 }],
};

export const mockTaskStatusGenerating: TaskStatus = {
  task_id: MOCK_TASK_ID,
  status: 'GENERATING_GOLDENS',
  phase: 'GENERATING_GOLDENS',
  progress: 0.5,
  error_message: null,
  created_at: '2026-07-08T00:00:00Z',
  completed_at: null,
};

export const mockTaskStatusAwaiting: TaskStatus = {
  task_id: MOCK_TASK_ID,
  status: 'AWAITING_CONFIRM',
  phase: 'AWAITING_CONFIRM',
  progress: 1.0,
  error_message: null,
  created_at: '2026-07-08T00:00:00Z',
  completed_at: null,
};

export const mockTaskStatusCompleted: TaskStatus = {
  task_id: MOCK_TASK_ID,
  status: 'COMPLETED',
  phase: 'COMPLETED',
  progress: 1.0,
  error_message: null,
  created_at: '2026-07-08T00:00:00Z',
  completed_at: '2026-07-08T00:05:00Z',
};

export const mockGoldens: GoldenItem[] = [
  { id: 1, input: 'What is WidgetX?', expected_output: 'WidgetX is a task management app.', context: '["WidgetX is a revolutionary..."]' },
  { id: 2, input: 'How many pricing tiers?', expected_output: 'Three tiers: Free, Pro, Enterprise.', context: '["WidgetX offers three tiers..."]' },
];

export const mockResults: TaskResult = {
  task_id: MOCK_TASK_ID,
  status: 'COMPLETED',
  overall_scores: [
    { name: 'FaithfulnessMetric', score: 0.92, passed: true },
    { name: 'AnswerRelevancyMetric', score: 0.85, passed: true },
    { name: 'ContextualRelevancyMetric', score: 0.78, passed: true },
  ],
  details: [
    {
      id: 1,
      golden_id: 1,
      input: 'What is WidgetX?',
      expected_output: 'WidgetX is a task management app.',
      actual_output: 'WidgetX is a task management application.',
      retrieval_context: '["WidgetX is a revolutionary..."]',
      metrics: [{ name: 'FaithfulnessMetric', score: 0.92, passed: true }],
      passed: true,
    },
  ],
};

export const mockHistory: HistoryItem[] = [
  {
    task_id: MOCK_TASK_ID,
    status: 'COMPLETED',
    rag_base_url: 'https://rag.example.com/v1',
    created_at: '2026-07-08T00:00:00Z',
    completed_at: '2026-07-08T00:05:00Z',
  },
];
```

- [ ] **Step 2: Write mocks/handlers.ts**

```typescript
import { http, HttpResponse } from 'msw';
import {
  MOCK_TASK_ID,
  mockUploadResponse,
  mockTaskStatusCompleted,
  mockGoldens,
  mockResults,
  mockHistory,
} from './fixtures';

const BASE = 'http://localhost:8000/api';

export const handlers = [
  http.post(`${BASE}/upload`, () =>
    HttpResponse.json(mockUploadResponse)
  ),

  http.post(`${BASE}/evaluate`, () =>
    HttpResponse.json({ task_id: MOCK_TASK_ID })
  ),

  http.get(`${BASE}/task/:taskId`, () =>
    HttpResponse.json(mockTaskStatusCompleted)
  ),

  http.get(`${BASE}/goldens/:taskId`, () =>
    HttpResponse.json(mockGoldens)
  ),

  http.post(`${BASE}/goldens/:taskId/confirm`, () =>
    HttpResponse.json({ status: 'confirmed' })
  ),

  http.get(`${BASE}/results/:taskId`, () =>
    HttpResponse.json(mockResults)
  ),

  http.get(`${BASE}/history`, () =>
    HttpResponse.json(mockHistory)
  ),
];
```

- [ ] **Step 3: Write user-flows.test.tsx**

```tsx
import { describe, it, expect, beforeAll, afterAll, afterEach } from 'vitest';
import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { setupServer } from 'msw/node';
import { renderWithProviders } from './test-utils';
import { handlers } from '../mocks/handlers';
import App from '../App';
import { MOCK_TASK_ID } from '../mocks/fixtures';

const server = setupServer(...handlers);

beforeAll(() => server.listen({ onUnhandledRequest: 'bypass' }));
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

describe('User Flows', () => {
  it('Config page → upload → navigate to progress', async () => {
    renderWithProviders(<App />);
    const user = userEvent.setup();

    // Fill in RAG config
    await user.type(screen.getByLabelText(/base url/i), 'https://rag.test.com/v1');
    await user.type(screen.getByLabelText(/api key/i), 'sk-test');

    // Save config
    await user.click(screen.getByRole('button', { name: /save/i }));

    // Upload a file (via the hidden input)
    const input = document.querySelector('input[type="file"]') as HTMLInputElement;
    const file = new File(['test content'], 'doc.txt', { type: 'text/plain' });
    await user.upload(input, file);

    // Start evaluation button should be enabled
    const startBtn = screen.getByRole('button', { name: /start evaluation/i });
    expect(startBtn).not.toBeDisabled();
  });

  it('Results page shows metric scores', async () => {
    window.history.pushState({}, '', `/task/${MOCK_TASK_ID}/results`);
    renderWithProviders(<App />);

    await waitFor(() => {
      expect(screen.getByText('FaithfulnessMetric')).toBeInTheDocument();
    });
    expect(screen.getByText('92.0%')).toBeInTheDocument();
  });

  it('History sidebar shows past tasks', async () => {
    renderWithProviders(<App />);

    await waitFor(() => {
      expect(screen.getByText('COMPLETED')).toBeInTheDocument();
    });
  });
});
```

- [ ] **Step 4: Run user flow tests**

```bash
cd frontend && npx vitest run src/__tests__/user-flows.test.tsx
```

Expected: PASS (3 tests)

- [ ] **Step 5: Run all frontend tests**

```bash
cd frontend && npx vitest run
```

Expected: All tests PASS

- [ ] **Step 6: Commit**

```bash
git add frontend/src/__tests__/user-flows.test.tsx frontend/src/mocks/
git commit -m "test: add frontend user flow tests with MSW"
```

---

### Task 19: Final Integration Verification

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Run all backend tests**

```bash
cd D:\deepeval-main\rag-llm-test
pytest tests/ -v --cov=app --cov-report=term-missing
```

Expected: All unit + API tests PASS. Coverage ≥ 80%.

- [ ] **Step 2: Run all frontend tests**

```bash
cd frontend && npx vitest run --coverage
```

Expected: All component + flow tests PASS.

- [ ] **Step 3: Write README.md**

````markdown
# RAG Evaluation Platform

B/S-architecture RAG evaluation platform powered by [deepeval](https://github.com/confident-ai/deepeval).

## Quick Start

### Backend
```bash
pip install -r requirements.txt
export DEEPSEEK_API_KEY=your_key
uvicorn app.main:app --reload --port 8000
```

### Frontend
```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173.

## Architecture
- **Backend**: FastAPI + deepeval + SQLite
- **Frontend**: React + TypeScript + shadcn/ui + TanStack Query

## Testing
```bash
# Backend
pytest tests/ -v --cov=app

# Frontend
cd frontend && npx vitest run
```

## Known Issues
- Uses deepeval fork from PR [#2736](https://github.com/confident-ai/deepeval/pull/2736) for `deepseek-v4-flash` support and silent failure fix.
- `deepseek-chat` deprecated 2026-07-24. This project uses `deepseek-v4-flash`.
````

- [ ] **Step 4: Commit**

```bash
git add README.md
git commit -m "docs: add README with setup instructions"
```
