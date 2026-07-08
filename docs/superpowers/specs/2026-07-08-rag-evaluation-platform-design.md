# RAG Evaluation Platform — Design Spec

> Date: 2026-07-08
> Status: approved
> Based on: deepeval (Confident AI), FastAPI, React

## Overview

A B/S-architecture RAG evaluation platform. Users upload their knowledge base documents, configure their RAG API endpoint (OpenAI-compatible), and the platform generates goldens (ground truth Q&A pairs) via deepeval's Synthesizer, constructs an evaluation dataset, runs a battery of metrics, and displays results in a dashboard. Built on deepeval's Python SDK with a FastAPI backend and React/TypeScript frontend.

## Architecture

```
┌──────────────────────────────────────────────────┐
│  Frontend (React + TypeScript + shadcn/ui)        │
│  ┌──────────┐ ┌───────────┐ ┌────────────────┐  │
│  │ Config   │ │ Golden    │ │ Results        │  │
│  │ Panel    │ │ Browser   │ │ Dashboard      │  │
│  └──────────┘ └───────────┘ └────────────────┘  │
│                     │ REST API                     │
├─────────────────────┼────────────────────────────┤
│  Backend (FastAPI)   │                             │
│  ┌───────────────────┴──────────────────────────┐ │
│  │ /api/upload   /api/evaluate  /api/results    │ │
│  └───────────────────┬──────────────────────────┘ │
│  ┌───────────────────┴──────────────────────────┐ │
│  │ Synthesizer → Dataset → Metrics → evaluate() │ │
│  │         (deepeval core pipeline)              │ │
│  └───────────────────┬──────────────────────────┘ │
│  ┌───────────────────┴──────────────────────────┐ │
│  │ SQLite (goldens, eval results, task history)  │ │
│  └──────────────────────────────────────────────┘ │
│  ┌───────────────────┴──────────────────────────┐ │
│  │ Disk: ./data/{task_id}/documents/ (raw files) │ │
│  └──────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────┘
```

- Frontend communicates via REST API only
- Backend encapsulates deepeval's Synthesizer, EvaluationDataset, evaluate() APIs
- Evaluation tasks run asynchronously; frontend polls task status
- Large document files stored on disk; metadata in SQLite

## Technology Stack

| Layer | Choice | Rationale |
|-------|--------|-----------|
| Backend framework | FastAPI (Python) | Async support, native to deepeval ecosystem |
| Frontend framework | React + TypeScript | Strong ecosystem, team familiarity |
| UI component library | shadcn/ui | Clean design, works well with React/Tailwind |
| Database | SQLite | Zero-config, sufficient for single-instance use |
| Evaluation engine | deepeval (Python SDK) | Synthesizer, metrics, evaluate() pipeline |
| RAG interface protocol | OpenAI-compatible chat completions | Most universal, users just provide base_url + api_key |
| Evaluation model (initial, hardcoded) | DeepSeek V4 Flash (`deepseek-v4-flash`) | Per PR #2736; `deepseek-chat` deprecated 2026-07-24 |
| Embedding model (initial, hardcoded) | SiliconFlow BAAI/bge-m3 | Matches reference project pattern |

## API Design

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/upload` | Upload knowledge base files; returns file list |
| `POST` | `/api/evaluate` | Start evaluation task (params: rag_base_url, rag_api_key, file ids); returns task_id |
| `GET` | `/api/task/{task_id}` | Get task status + current phase + progress percentage |
| `GET` | `/api/goldens/{task_id}` | Get generated goldens list (for user review) |
| `POST` | `/api/goldens/{task_id}/confirm` | User confirms goldens, pipeline continues to full evaluation |
| `GET` | `/api/results/{task_id}` | Get evaluation results (metric scores + per-item breakdown) |
| `GET` | `/api/history` | Get list of past evaluation tasks |

### Task State Machine

```
UPLOADING → GENERATING_GOLDENS → AWAITING_CONFIRM → RUNNING_EVAL → COMPLETED
                 ↘                    (user confirms)                ↙
                 FAILED  ←  (any stage on error)
```

- After `GENERATING_GOLDENS`, task auto-pauses at `AWAITING_CONFIRM`
- User can browse goldens, then confirm to proceed or abort
- Once confirmed, task enters `RUNNING_EVAL` (irreversible)

## Database Schema

Tables in SQLite:

```sql
-- Evaluation tasks
tasks (
    id            TEXT PRIMARY KEY,  -- UUID
    rag_base_url  TEXT NOT NULL,
    rag_api_key   TEXT NOT NULL,     -- obfuscated storage
    status        TEXT NOT NULL,     -- enum per state machine
    error_message TEXT,
    created_at    DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    completed_at  DATETIME
)

-- Files uploaded per task (metadata only; content on disk)
task_documents (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id   TEXT REFERENCES tasks(id),
    filename  TEXT NOT NULL,
    file_path TEXT NOT NULL,         -- relative path under ./data/{task_id}/documents/
    file_size INTEGER
)

-- Generated goldens
goldens (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id         TEXT REFERENCES tasks(id),
    input           TEXT NOT NULL,   -- the question
    expected_output TEXT NOT NULL,   -- the expected answer
    context         TEXT             -- corresponding doc snippets (JSON array)
)

-- Per-golden evaluation results
eval_results (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id           TEXT REFERENCES tasks(id),
    golden_id         INTEGER REFERENCES goldens(id),
    actual_output     TEXT NOT NULL,
    retrieval_context TEXT,
    metrics_json      TEXT NOT NULL,  -- all metric scores as JSON
    passed            BOOLEAN,
    evaluated_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
)
```

### File Storage Layout

```
./data/
  {task_id}/
    documents/           ← raw user uploads
      manual.pdf
      faq.md
    .dataset.json        ← deepeval generated dataset file
```

Documents stored on disk to avoid bloating SQLite. Metadata (filename, path, size) kept in `task_documents` for querying.

## Evaluation Pipeline

Core async pipeline (FastAPI background task):

```
1. Load documents from ./data/{task_id}/documents/
2. Synthesizer.generate_goldens_from_docs()
   - ContextConstructionConfig (embedder + critic_model)
   - max_goldens_per_context = 3 (configurable)
3. Save goldens → SQLite; status → AWAITING_CONFIRM
4. [Wait for user confirmation via POST /api/goldens/{task_id}/confirm]
5. For each golden:
   a. Call user's RAG API (OpenAI-compatible) with golden.input
   b. Extract actual_output + retrieval_context from response
   c. Build LLMTestCase(input, actual_output, retrieval_context, expected_output)
6. Build EvaluationDataset from goldens
7. Run evaluate() with two metric groups:
   - Retriever: ContextualRelevancyMetric, ContextualRecallMetric, ContextualPrecisionMetric
   - Generator: AnswerRelevancyMetric, FaithfulnessMetric
8. Save results → eval_results; status → COMPLETED
```

### Calling User's RAG API

For each test input, send an OpenAI-compatible chat completion request:
```
POST {rag_base_url}/chat/completions
Headers: Authorization: Bearer {rag_api_key}
Body: { model: "...", messages: [{role: "user", content: golden.input}] }
```

The RAG service is expected to return both the answer and (optionally) the retrieved contexts in the response. If contexts are not returned separately, the evaluation will still run but context-dependent metrics (ContextualPrecision, ContextualRecall) will have degraded signal.

## Frontend Design

### Page Structure

4 core pages:

| Page | Route | Purpose |
|------|-------|---------|
| Config | `/` | RAG config form + file upload + start button |
| Goldens | `/task/:id/goldens` | Browse generated goldens, confirm to proceed |
| Progress | `/task/:id/progress` | Live progress bar + phase indicator |
| Results | `/task/:id/results` | Metric score cards, chart, detail breakdown |

### User Flow

```
Config → Start → Progress → Goldens Browser → Confirm → Progress → Results Dashboard
```

### Component Tree

```
App
├── Layout (top nav + sidebar history list)
├── ConfigPage
│   ├── RagConfigForm (base_url, api_key inputs)
│   ├── FileUploader (drag-and-drop zone)
│   └── StartButton
├── GoldensPage
│   ├── GoldenCard[] (scrollable list, each showing input + expected_output)
│   └── ConfirmButton
├── ProgressPage
│   └── ProgressTracker (phase stepper indicator)
└── ResultsPage
    ├── ScoreCardRow (overall: Faithfulness, Relevancy, Precision, Recall)
    ├── MetricsRadarChart (radar/bar chart for metric comparison)
    └── DetailTable (per-golden expandable rows with metric breakdown)
```

### State Management

- React Context + useReducer for global app state (current task, navigation)
- React Query (TanStack Query) for server state: API calls, caching, polling
- Polling interval: 2 seconds for task progress; stop on terminal states

## Known Dependency Issue — Synthesizer Silent Failure

> Source: [PR #2736](https://github.com/confident-ai/deepeval/pull/2736) by Comui520 (unmerged as of 2026-07-08)

**Bug**: When using `deepseek-chat` (or any model with unknown pricing) as the Synthesizer model:
1. `calculate_cost()` returns `None` for unregistered models
2. `ContextGenerator.evaluate_chunk()` does `self.total_cost += cost` → `TypeError`
3. The error is caught by a broad `except Exception` in `generate_contexts()`
4. **Result**: Synthesizer silently returns empty goldens with no error surfaced

**Fix applied in this project**: Install deepeval from the patched fork:
```bash
pip install git+https://github.com/Comui520/deepeval.git@fix/deepseek-v4-support
```

The fork:
- Guards `None` cost at all arithmetic boundaries in `evaluate_chunk`, `_generate_schema`, `_generate`, etc.
- Raises `DeepEvalError` when all documents fail or zero contexts are produced
- Registers `deepseek-v4-flash` and `deepseek-v4-pro` model definitions

**Model migration**: Per [DeepSeek API docs](https://api-docs.deepseek.com/), `deepseek-chat` will be deprecated on 2026-07-24. This project uses `deepseek-v4-flash` from the start.

**Fallback plan**: If the PR is merged before project completion, switch to the upstream version. If the PR is rejected, maintain the monkey-patches as a local `deepeval_patches.py` module that applies at startup.

## Error Handling

- **Upload failures**: Return HTTP 4xx with descriptive message (file too large, unsupported format)
- **Synthesizer failures**: Catch deepeval exceptions, set task status to FAILED, store error_message
- **RAG API unreachable**: Mark individual test cases as errored in eval_results with null metrics; don't fail entire pipeline
- **Timeout**: Set a per-task timeout (default 10 minutes). Exceeded → FAILED with timeout message
- **Empty goldens**: If Synthesizer generates 0 goldens (e.g., docs too short), report FAILED with guidance

## Scope & Future Work

### v1 (this spec)
- [x] Hardcoded evaluation model + embedding model
- [x] One-click evaluation with golden browsing gate
- [x] Single-turn RAG evaluation only
- [x] SQLite persistence
- [x] Basic results dashboard
- [x] Backend tests: unit + API integration + pipeline integration (pytest + mocks)
- [x] Frontend tests: component tests + key user flows (Vitest + MSW)

### v2 (future)
- [ ] Configurable LLM/embedding API settings via frontend
- [ ] Step-by-step manual control (edit goldens, adjust metrics)
- [ ] Multi-turn / chatbot evaluation support
- [ ] PDF document parsing support
- [ ] Confident AI integration for hosted dashboards
- [ ] User authentication
- [ ] Result export (CSV, PDF)

## Testing Design

Strategy: **Backend comprehensive + Frontend critical paths** (hybrid).
Pytest for backend, Vitest + React Testing Library for frontend, no E2E in v1.

### Backend Tests (`tests/`)

#### Layer 1: Unit Tests

| Module | Test file | What it covers |
|--------|-----------|----------------|
| `db.py` | `tests/test_db.py` | CRUD for tasks, documents, goldens, results. State machine transition validity (e.g., cannot go from COMPLETED back to RUNNING). Rollback on errors. |
| `storage.py` | `tests/test_storage.py` | File save/read/delete under `./data/{task_id}/`. Deduplicate filenames. Reject oversized files. Clean empty dirs on task delete. |
| `rag_client.py` | `tests/test_rag_client.py` | Send OpenAI-format request; parse response correctly; timeout handling; malformed response handling. Uses `responses` or `httpx` mock to simulate a remote RAG API. |
| `pipeline.py` | `tests/test_pipeline.py` | Orchestration logic: step ordering, golden save, state transitions, error → FAILED propagation. Mocked deepeval Synthesizer and RAG client so tests don't hit real APIs. |

#### Layer 2: API Integration Tests

| Target | Test file | What it covers |
|--------|-----------|----------------|
| Upload endpoint | `tests/test_api_upload.py` | `POST /api/upload` — valid file → 200 + file list; no file → 422; unsupported extension → 400. Uses FastAPI `TestClient` + temp directory. |
| Evaluate endpoint | `tests/test_api_evaluate.py` | `POST /api/evaluate` — valid params → 200 + task_id; missing fields → 422; returns 404 for nonexistent files. |
| Task status | `tests/test_api_task.py` | `GET /api/task/{id}` — returns correct status, progress; 404 for bad id. |
| Goldens endpoints | `tests/test_api_goldens.py` | `GET /api/goldens/{id}` — returns golden list; 404 for unknown task. `POST /api/goldens/{id}/confirm` — advances state; rejects if not in AWAITING_CONFIRM. |
| Results endpoint | `tests/test_api_results.py` | `GET /api/results/{id}` — returns scores + breakdown; 404 for incomplete task. |
| History endpoint | `tests/test_api_history.py` | `GET /api/history` — returns list sorted by date; empty array when no tasks. |

#### Layer 3: Pipeline Integration Tests (core deepeval path)

| Test file | What it covers |
|-----------|----------------|
| `tests/test_pipeline_goldens.py` | Feed a real small txt document through the Synthesizer → assert goldens generated, saved to DB, status = AWAITING_CONFIRM. Uses real deepeval but a test fixture document. |
| `tests/test_pipeline_evaluate.py` | With pre-seeded goldens and a mock RAG API, run the full metric evaluation → assert results saved with valid score ranges (0-1). Verifies LLMTestCase construction is correct. |
| `tests/test_pipeline_error.py` | Empty document → FAILED with descriptive message. RAG API timeout → partial results saved, individual errors recorded. |

#### Test Infrastructure

- **Fixtures**: `conftest.py` provides temp SQLite database (in-memory), temp `./data/` directory, pre-seeded tasks/goldens, and a mock OpenAI-compatible server via `responses` library.
- **Mock RAG server**: A fixture that creates an httpx-based mock returning realistic `{"choices":[{"message":{"content":"...", "contexts":["..."]}}]}` for pipeline tests. Exposed as `mock_rag_server`.
- **Test document**: A small fixture `.txt` file (~200 words about a fictional topic) committed to `tests/fixtures/` so pipeline tests are reproducible without external files.
- **Isolation**: Each test uses its own in-memory SQLite and temp directory. No cross-test contamination.

#### Running Backend Tests

```bash
pytest tests/ -v --cov=app --cov-report=term-missing
```

Target: ≥80% line coverage on `app/` backend code.

### Frontend Tests (`frontend/src/__tests__/`)

#### Component Tests (Vitest + React Testing Library)

| Component | What it tests |
|-----------|---------------|
| `RagConfigForm` | Renders inputs, validates required fields, calls onSubmit with form data |
| `FileUploader` | Renders drop zone, handles file selection, shows file list, calls onUpload callback |
| `GoldenCard` | Renders input + expected_output, expand/collapse detail |
| `ConfirmButton` | Disabled state when no goldens, fires onConfirm, shows loading spinner |
| `ScoreCard` | Renders metric name + score with correct color (green > 0.8, yellow > 0.6, red < 0.6) |
| `ProgressTracker` | Renders correct phase, shows active/inactive/completed states |

#### User Flow Tests

| Flow | What it tests |
|------|---------------|
| Config → Progress | User fills form, uploads file, clicks start → navigates to progress page, polling begins |
| Goldens → Confirm | Goldens page loads list, user clicks confirm → API called, navigates to progress |
| Results | Results page loads scores + detail table, expand row shows per-metric breakdown |
| History | Sidebar renders past tasks, click navigates to results |

#### Test Infrastructure

- **MSW (Mock Service Worker)**: Intercepts all fetch calls to backend API, returns fixture data. Shared handlers in `frontend/src/mocks/handlers.ts`.
- **Fixtures**: Reusable mock API responses — task statuses, golden lists, result payloads — in `frontend/src/mocks/fixtures.ts`.
- **Custom render**: `test-utils.tsx` wraps components with QueryClientProvider, MemoryRouter, and MSW server.

#### Running Frontend Tests

```bash
cd frontend && npx vitest run --coverage
```

### What v1 Does NOT Test (explicit non-goals)

- End-to-end Playwright tests (backend + frontend together in a real browser) — deferred to v2
- Performance/load tests — deferred
- deepeval internal correctness (that's deepeval's responsibility)
- Visual regression / screenshot tests
- Real LLM API calls in CI (all model-dependent tests use mocks)
