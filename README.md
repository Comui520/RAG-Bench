# RAG Evaluation Platform

A browser-based RAG evaluation platform powered by [deepeval](https://github.com/confident-ai/deepeval). It guides users through four steps: configure models and upload documents, review generated test samples, run five RAG metrics, and inspect or export the results.

## Features

- Four-step guided workflow with Chinese user-facing copy
- User-configurable RAG endpoint, evaluation LLM, embedding model, base URLs, models, and API keys
- Evaluation LLM adapters for OpenAI Chat Completions, OpenAI Responses, and Anthropic Messages
- Automatic test-sample generation from uploaded documents
- Editable, removable, and manually creatable test samples
- RAG response context extraction from `message.contexts`, `message.citations`, or top-level `contexts` / `context`
- Real-time progress through SSE
- Named tasks, paginated history cards, task deletion, and CSV / JSON result export
- Local browser configuration memory for repeated evaluations

> Configuration memory uses browser `localStorage` and includes API keys when saved. Use the platform only in a trusted local browser profile, and clear the saved configuration before sharing the computer.

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | FastAPI + SQLite + httpx |
| Evaluation Engine | deepeval (official, v4.0.7) |
| Frontend | React 19 + TypeScript + Tailwind CSS + TanStack Query + Recharts |
| Notifications | sonner (toast) |

## Quick Start

### Prerequisites

- Python 3.11+ with conda (recommended)
- Node.js 18+
- Evaluation LLM endpoint using OpenAI Chat Completions, OpenAI Responses, or Anthropic Messages
- OpenAI-compatible embedding API key (SiliconFlow BAAI/bge-m3, OpenAI, local Ollama, etc.)

### Backend

```powershell
conda create -n rag-eval python=3.11 -y
conda activate rag-eval
pip install -r requirements.txt
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

### Frontend

```powershell
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`.

> **API base**: the frontend reads `VITE_API_BASE` (default `http://localhost:8000/api`).
> Create `frontend/.env.local` to override, e.g. `VITE_API_BASE=http://127.0.0.1:8000/api`.

### Mini RAG (optional demo service)

```powershell
$env:DEEPSEEK_API_KEY = "your-key"
python mini_rag.py  # starts on port 8001
```

Configure the tested RAG service as:

```text
Base URL: http://127.0.0.1:8001
API Key:  sk-local
Model:    deepseek-v4-flash
```

The mini RAG ignores the incoming placeholder key, but it must contain ASCII characters because it is sent in an HTTP `Authorization` header.

## Testing

```powershell
# Backend offline suite (106 passed in the latest verified run)
python -m pytest tests\ -q --ignore=tests\test_pipeline_goldens.py --ignore=tests\test_pipeline_evaluate.py

# Backend real-API integration (requires both keys)
$env:DEEPSEEK_API_KEY = "sk-..."
$env:EMBEDDING_API_KEY = "sk-..."
$env:EMBEDDING_BASE_URL = "https://api.siliconflow.cn/v1"
$env:EMBEDDING_MODEL = "BAAI/bge-m3"
python -m pytest tests\test_pipeline_goldens.py tests\test_pipeline_evaluate.py -v

# Frontend (25 passed in the latest verified run)
cd frontend
npm test
npm run build
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
| `GET` | `/api/goldens/{id}` | List generated test samples |
| `POST` | `/api/goldens/{task_id}` | Manually add a test sample |
| `PUT` | `/api/goldens/{golden_id}` | Edit a test sample |
| `DELETE` | `/api/goldens/{golden_id}` | Delete a test sample |
| `POST` | `/api/goldens/{id}/confirm` | Confirm test samples and proceed to evaluation |
| `GET` | `/api/results/{id}` | Get evaluation results |
| `GET` | `/api/history` | List past evaluation tasks (includes optional task name) |
| `DELETE` | `/api/tasks/{id}` | Delete a completed/failed task and its local data |

### Tested RAG Response Contract

The tested RAG endpoint is called through OpenAI-style `POST {base_url}/chat/completions`. The answer is read from `choices[0].message.content`. Retrieval evidence is discovered from the first supported field:

1. `choices[0].message.contexts`
2. `choices[0].message.citations` (`text` or `content` per citation)
3. top-level `contexts`
4. top-level `context`

Retrieval metrics require these evidence chunks. If none are found, the platform emits a warning because Contextual Relevancy, Recall, and Precision cannot be evaluated correctly.

### Evaluation Pipeline

1. Name the evaluation, configure the RAG API and models, and upload knowledge-base documents
2. deepeval Synthesizer generates test samples (question/expected-answer pairs)
3. Review, edit, remove, or manually add test samples
4. Confirm the samples and run five metrics against the tested RAG service
5. Inspect per-sample results, export CSV / JSON, or return later through paginated history

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
│       ├── pages/            # Config, sample review, progress, results, paginated history
│       ├── components/       # ModelSelector, StepIndicator, ExpandableText, charts, etc.
│       ├── api/client.ts     # Fetch wrappers with timeout/abort (VITE_API_BASE)
│       ├── hooks/useApi.ts   # TanStack Query + SSE hooks
│       ├── utils/storage.ts  # Local browser configuration memory
│       ├── types/index.ts    # Shared TypeScript types
│       ├── mocks/            # MSW handlers + fixtures
│       └── __tests__/        # 12 test files, 25 tests
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
