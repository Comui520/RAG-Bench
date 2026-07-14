# RAG Evaluation Platform

B/S-architecture RAG evaluation platform powered by [deepeval](https://github.com/confident-ai/deepeval). Upload knowledge base documents, configure your RAG API endpoint, and the platform generates evaluation goldens, runs a battery of metrics, and displays results in a dashboard.

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | FastAPI + SQLite + httpx |
| Evaluation Engine | deepeval (official, v4.0.7) |
| Frontend | React 18 + TypeScript + Tailwind CSS + TanStack Query + Recharts |
| Notifications | sonner (toast) |

## Quick Start

### Prerequisites

- Python 3.11+ with conda (recommended)
- Node.js 18+
- DeepSeek API key (for evaluation model)
- SiliconFlow API key (for embedding model, or use any OpenAI-compatible embedding API)

### Backend

```bash
conda create -n rag-eval python=3.11 -y
conda activate rag-eval
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`.

### Mini RAG (for testing)

```bash
export DEEPSEEK_API_KEY=your_key
python mini_rag.py   # starts on port 8001
```

## Testing

```bash
# Backend (75 tests)
pytest tests/ -v --ignore=tests/test_pipeline_goldens.py --ignore=tests/test_pipeline_evaluate.py

# Backend integration (requires DEEPSEEK_API_KEY)
DEEPSEEK_API_KEY=your_key pytest tests/test_pipeline_goldens.py tests/test_pipeline_evaluate.py -v

# Frontend (22 tests)
cd frontend && npm test
```

## Architecture

```
Frontend (React + TS)  ←→  Backend (FastAPI)  ←→  deepeval (Synthesizer + Metrics)
       │                          │
  REST + SSE                  SQLite + Disk
```

### API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/upload` | Upload knowledge base files |
| `POST` | `/api/evaluate` | Start evaluation with model configs |
| `GET` | `/api/task/{id}` | Get task status |
| `GET` | `/api/task/{id}/stream` | SSE real-time progress |
| `GET` | `/api/models` | Proxy to fetch available models |
| `GET` | `/api/goldens/{id}` | List generated goldens |
| `POST` | `/api/goldens/{id}/confirm` | Confirm goldens, proceed to evaluation |
| `GET` | `/api/results/{id}` | Get evaluation results |
| `GET` | `/api/history` | List past evaluation tasks |

### Evaluation Pipeline

1. Upload knowledge base documents
2. Configure RAG API, evaluation model, and embedding model
3. deepeval Synthesizer generates goldens (Q&A pairs)
4. Review and confirm goldens
5. Pipeline queries RAG API for each golden, runs 5 metrics
6. Results dashboard with per-question breakdown

### Metrics

- **Retriever**: ContextualRelevancy, ContextualRecall, ContextualPrecision
- **Generator**: AnswerRelevancy, Faithfulness

## Supported Model Providers

| Provider | Evaluation | Embedding | Notes |
|----------|-----------|-----------|-------|
| DeepSeek | Native `DeepSeekModel` | — | Full Synthesizer compatibility |
| OpenAI | `CustomOpenAIModel` | — | Any OpenAI-compatible API |
| SiliconFlow | `CustomOpenAIModel` | `SiliconFlowEmbeddingModel` | BAAI/bge-m3 recommended |
| Anthropic | Not supported | — | Non-OpenAI-compatible protocol |
| Custom | `CustomOpenAIModel` | Any OpenAI-compatible | vLLM, Ollama, etc. |

## Known Issues

### deepeval `DeepEvalBaseLLM` Synthesizer Incompatibility

**Status:** Upstream bug in deepeval v4.0.7. [Full bug report](docs/deepeval-bug-report.md).

Custom `DeepEvalBaseLLM` subclasses cannot be used as `critic_model` in `ContextConstructionConfig` — the Synthesizer returns 0 goldens despite valid model implementations. The internal chunk evaluation code expects return value formats from native model classes (e.g., `DeepSeekModel`) that are not documented in the abstract interface.

**Workaround:** The platform uses `DeepSeekModel` for the DeepSeek provider and `CustomOpenAIModel` for other providers. See `app/pipeline.py:build_evaluation_model()`.

### `deepseek-v4-flash` Cost Calculation

**Status:** Fixed in deepeval v4.0.7 — model is registered and works with `DeepSeekModel`. However `calculate_cost()` still returns `None` for some edge cases. Using `deepseek-chat` is a reliable fallback.

### Windows Path Escaping

File paths in `app/storage.py` use POSIX-style forward slashes to avoid Windows backslash escape issues (`\t` → tab, `\f` → form feed) when passed to deepeval's `TextLoader`.

## Project Structure

```
rag-llm-test/
├── app/
│   ├── main.py              # FastAPI entry point
│   ├── config.py             # Infrastructure config (chunk size, timeouts, paths)
│   ├── models.py             # Pydantic request/response schemas
│   ├── db.py                 # SQLite CRUD operations
│   ├── storage.py            # File storage (./data/{task_id}/)
│   ├── embedder.py           # SiliconFlow / OpenAI-compatible embedding adapter
│   ├── custom_model.py       # CustomOpenAIModel (DeepEvalBaseLLM subclass)
│   ├── rag_client.py         # OpenAI-compatible RAG API client
│   ├── task_manager.py       # In-memory task state + SSE event queues
│   ├── pipeline.py           # Core evaluation pipeline
│   └── routes.py             # All API route handlers
├── tests/
│   ├── conftest.py           # Shared fixtures
│   ├── fixtures/             # Test documents
│   ├── test_db.py            # Database CRUD tests
│   ├── test_storage.py       # File storage tests
│   ├── test_rag_client.py    # RAG client tests
│   ├── test_task_manager.py  # Task state machine tests
│   ├── test_pipeline.py      # Pipeline unit tests
│   ├── test_pipeline_v2.py   # Pipeline v2 (dynamic models) tests
│   ├── test_custom_model.py  # CustomOpenAIModel tests (9 tests, no API key)
│   ├── test_api_*.py         # API integration tests (6 files)
│   ├── test_pipeline_error.py    # Pipeline error handling
│   ├── test_pipeline_goldens.py  # Goldens generation integration
│   └── test_pipeline_evaluate.py # Evaluation integration
├── frontend/
│   └── src/
│       ├── pages/            # ConfigPage, GoldensPage, ProgressPage, ResultsPage
│       ├── components/       # ModelSelector, FileUploader, ProgressTracker, etc.
│       ├── api/client.ts     # Fetch wrappers with timeout/abort
│       ├── hooks/useApi.ts   # TanStack Query + SSE hooks
│       ├── types/index.ts    # Shared TypeScript types
│       ├── mocks/            # MSW handlers + fixtures
│       └── __tests__/        # 10 test files, 22 tests
├── mini_rag.py               # Test RAG service (port 8001)
├── requirements.txt
├── pyproject.toml
└── docs/
    ├── deepeval-bug-report.md    # Detailed upstream bug report
    ├── USER_GUIDE.md             # End-user tutorial
    └── superpowers/              # Design specs and implementation plans
```

## Commit Conventions

| Prefix | Example | When |
|--------|---------|------|
| `feat:` | `feat: add ModelSelector component` | New feature |
| `fix:` | `fix: use forward slashes in file paths` | Bug fix |
| `test:` | `test: add CustomOpenAIModel unit tests` | Tests |
| `docs:` | `docs: add v2 design spec` | Documentation |
| `chore:` | `chore: project scaffolding` | Tooling, deps |
| `refactor:` | `refactor: simplify config` | Code restructuring |
