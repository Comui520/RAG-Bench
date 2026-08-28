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
- Any OpenAI-compatible LLM API key (DeepSeek, OpenAI, SiliconFlow, vLLM, Ollama…)
- Any OpenAI-compatible embedding API key (SiliconFlow BAAI/bge-m3, OpenAI, local Ollama…)

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

> **API base**: the frontend reads `VITE_API_BASE` (default `http://localhost:8000/api`).
> Create `frontend/.env.local` to override, e.g. `VITE_API_BASE=http://127.0.0.1:8000/api`.

### Mini RAG (for testing)

```bash
export DEEPSEEK_API_KEY=your_key
python mini_rag.py   # starts on port 8001
```

## Testing

```bash
# Backend (84 tests)
pytest tests/ -q --ignore=tests/test_pipeline_goldens.py --ignore=tests/test_pipeline_evaluate.py

# Backend integration (requires DEEPSEEK_API_KEY + EMBEDDING_API_KEY)
$env:DEEPSEEK_API_KEY=sk-...; $env:EMBEDDING_API_KEY=sk-...
$env:EMBEDDING_BASE_URL=https://api.siliconflow.cn/v1
$env:EMBEDDING_MODEL=BAAI/bge-m3
pytest tests/test_pipeline_goldens.py tests/test_pipeline_evaluate.py -v

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
| `GET` | `/api/history` | List past evaluation tasks (includes optional task name) |
| `DELETE` | `/api/tasks/{id}` | Delete a completed/failed task and its local data |

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

**All three model slots (RAG-under-test, evaluation LLM, embedding) are fully user-configurable** in the frontend: provider preset + API format + base URL + API key + model name.

### API Format Selection

The **evaluation LLM** (`CustomOpenAIModel`) supports three wire protocols, selectable in the `ModelSelector` dropdown. This matters because not every endpoint speaks OpenAI Chat Completions:

| `api_format` | Protocol | Endpoint | JSON output | Use for |
|--------------|----------|----------|-------------|---------|
| `openai_chat` (default) | OpenAI Chat Completions | `POST {base}/chat/completions` | `response_format=json_object` + fallback | DeepSeek, SiliconFlow, vLLM, llama.cpp, LM Studio, Ollama, any OpenAI-compatible proxy — **works with every local server** |
| `openai_json` | OpenAI Responses API | `POST {base}/responses` | `text.format.type=json_object` | Modern OpenAI API (`gpt-*`); *not* supported by most local OpenAI-compatible servers (see microsoft/amplifier#246) |
| `anthropic` | Anthropic Messages API | `POST {base}/messages` | prompt instruction + tolerant JSON parse + retry | Anthropic Claude, and proxies that expose `/v1/messages` |

The **embedding** model always speaks OpenAI-compatible `POST {base}/embeddings` (Anthropic / Responses have no embedding endpoints), so its selector hides the format dropdown.

| Provider | Evaluation LLM | Embedding | Notes |
|----------|---------------|-----------|-------|
| DeepSeek | `CustomOpenAIModel` (`openai_chat`) | — | api.deepseek.com |
| OpenAI | `CustomOpenAIModel` (`openai_json`) | any | |
| SiliconFlow | `CustomOpenAIModel` (`openai_chat`) | `OpenAICompatibleEmbeddingModel` | BAAI/bge-m3 recommended |
| vLLM / Ollama / 本地 | `CustomOpenAIModel` (`openai_chat`) | any OpenAI-compatible | point base_url at the local server |
| Anthropic | `CustomOpenAIModel` (`anthropic`) | — | `x-api-key` + `anthropic-version` headers |

## Known Issues

### deepeval `DeepEvalBaseLLM` Synthesizer Incompatibility (#2884 / #2885)

**Status:** Upstream bugs in deepeval, still OPEN ([full report](docs/deepeval-bug-report.md)):

- **#2885**: deepeval's non-native path assumes `generate()` returns a **single value** (`str` or schema instance), but model classes that return `(result, cost)` tuples break `Synthesizer._generate_schema` / `_generate` / `ContextGenerator.evaluate_chunk`, which silently swallow the error and yield **0 goldens**.
- **#2884**: models with unknown pricing make `calculate_cost()` return `None`, so native path `total_cost += None` raises `TypeError` that is also silently swallowed.

**Fix in this repo (no site-packages patching):**
`app/custom_model.py` `CustomOpenAIModel`:
- `generate()` / `a_generate()` **always return a single value** — schema instance when `schema` is passed, otherwise `str`. Never a tuple.
- `calculate_cost()` returns `0.0` instead of `None` when pricing is unknown.
- Uses `response_format={"type":"json_object"}` with automatic fallback on `BadRequestError` (DeepSeek requires the word "json" in the prompt), plus a second fallback that appends a JSON instruction suffix, so Synthesizer prompts (which ask for JSON) work even when the model would otherwise return plain text.
- Declares `supports_json_mode()=True` / `supports_structured_outputs()=False`.

All providers (DeepSeek included — its API is OpenAI-compatible) go through the **same** `CustomOpenAIModel`, so behavior is consistent everywhere.

### `deepseek-v4-flash` Cost Calculation

deepeval v4.0.7 registers `deepseek-v4-flash`/`v4-pro` pricing, but `calculate_cost()` can still return `None` on some paths. Our `CustomOpenAIModel.calculate_cost()` never returns `None`, so this is fully covered.

### Windows Path Escaping

File paths in `app/storage.py` use POSIX-style forward slashes to avoid Windows backslash escape issues (`\t` → tab, `\f` → form feed) when passed to deepeval's `TextLoader`.

## Project Structure

```
rag-llm-test/
├── app/
│   ├── main.py              # FastAPI entry point
│   ├── config.py             # Infrastructure config (chunk size, timeouts, paths)
│   ├── models.py             # Pydantic request/response schemas (ModelConfig + api_format)
│   ├── db.py                 # SQLite CRUD operations
│   ├── storage.py            # File storage (./data/{task_id}/)
│   ├── embedder.py           # OpenAI-compatible embedding adapter (any /embeddings endpoint)
│   ├── custom_model.py       # CustomOpenAIModel: openai_chat / openai_json / anthropic adapters
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
│   ├── test_custom_model.py  # CustomOpenAIModel tests (no API key)
│   ├── test_custom_model_responses.py  # OpenAI Responses API adapter tests
│   ├── test_custom_model_anthropic.py  # Anthropic Messages API adapter tests
│   ├── test_custom_model_synthesizer.py  # Synthesizer + 5 metrics offline
│   ├── test_api_*.py         # API integration tests (6 files)
│   ├── test_pipeline_error.py    # Pipeline error handling
│   ├── test_pipeline_goldens.py  # Goldens generation integration (real API)
│   └── test_pipeline_evaluate.py # Evaluation integration (real API)
├── frontend/
│   └── src/
│       ├── pages/            # ConfigPage, GoldensPage, ProgressPage, ResultsPage
│       ├── components/       # ModelSelector, FileUploader, ProgressTracker, etc.
│       ├── api/client.ts     # Fetch wrappers with timeout/abort (VITE_API_BASE)
│       ├── hooks/useApi.ts   # TanStack Query + SSE hooks
│       ├── types/index.ts    # Shared TypeScript types
│       ├── mocks/            # MSW handlers + fixtures
│       └── __tests__/        # 10 test files, 22 tests
├── mini_rag.py               # Test RAG service (port 8001)
├── scripts/
│   ├── smoke_real_eval.py    # Real-API smoke (DeepSeek + SiliconFlow)
│   └── smoke_formats_e2e.py  # Offline 3-protocol E2E (local mock server)
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
