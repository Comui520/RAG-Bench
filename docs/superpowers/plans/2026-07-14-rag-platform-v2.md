# RAG Evaluation Platform v2 — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add user-configurable model selection (LLM + embedding + RAG), SSE real-time progress, duplicate-submission prevention, and frontend UX polish to the v1 platform.

**Architecture:** Backend adds `ModelConfig` Pydantic schema, `GET /api/models` proxy endpoint, SSE stream endpoint, and an `asyncio.Lock` gate on evaluate. Pipeline gains a `progress_callback` that feeds events into the SSE stream. Frontend adds `ModelSelector` component, switches `ProgressPage` from polling to `EventSource`, installs `sonner` for toast notifications, and improves button/error/upload feedback throughout.

**Tech Stack:** Python 3.11+, FastAPI, deepeval 4.0.7, SSE (text/event-stream), sonner, React 18, TypeScript, TanStack Query

---

## File Structure

```
rag-llm-test/
├── app/
│   ├── models.py            # [MODIFY] Add ModelConfig, expand EvaluateRequest
│   ├── routes.py            # [MODIFY] Add /api/models, /api/task/{id}/stream, lock on evaluate
│   ├── pipeline.py          # [MODIFY] Dynamic model building, progress_callback
│   ├── config.py            # [MODIFY] Remove eval/embed defaults, keep infra only
│   ├── embedder.py          # [MODIFY] build_embedder accepts ModelConfig
│   └── task_manager.py      # [MODIFY] Add SSE event queue per task
├── tests/
│   ├── test_api_models.py   # [CREATE]
│   ├── test_api_stream.py   # [CREATE]
│   ├── test_api_evaluate_v2.py  # [CREATE]
│   └── test_pipeline_v2.py  # [CREATE]
├── frontend/src/
│   ├── components/
│   │   ├── ModelSelector.tsx    # [CREATE]
│   │   ├── RagConfigForm.tsx    # [MODIFY]
│   │   ├── FileUploader.tsx     # [MODIFY]
│   │   ├── ProgressTracker.tsx  # [MODIFY]
│   │   └── ConfirmButton.tsx    # [MODIFY]
│   ├── pages/
│   │   ├── ConfigPage.tsx       # [MODIFY]
│   │   ├── ProgressPage.tsx     # [MODIFY]
│   │   ├── GoldensPage.tsx      # [MODIFY]
│   │   └── ResultsPage.tsx      # [MODIFY]
│   ├── hooks/
│   │   └── useApi.ts            # [MODIFY] add useSSE, useModels hooks
│   ├── api/
│   │   └── client.ts            # [MODIFY] add fetchModels, timeout, abort
│   ├── App.tsx                  # [MODIFY] add Toaster
│   └── __tests__/
│       ├── ModelSelector.test.tsx    # [CREATE]
│       ├── RagConfigForm-v2.test.tsx # [CREATE]
│       ├── ProgressPage-v2.test.tsx  # [CREATE]
│       └── FileUploader-v2.test.tsx  # [CREATE]
└── package.json (frontend)   # [MODIFY] add sonner
```

---

### Task 1: ModelConfig Schema + EvaluateRequest Update

**Files:**
- Modify: `app/models.py`

- [ ] **Step 1: Add ModelConfig and update EvaluateRequest**

```python
"""Pydantic request/response models for the API."""

from typing import List, Optional
from pydantic import BaseModel, Field


class ModelConfig(BaseModel):
    """Configuration for an LLM or embedding model."""
    provider: str = Field(default="custom", description="deepseek|openai|anthropic|siliconflow|custom")
    model_name: str = Field(..., min_length=1, description="Model identifier")
    api_key: str = Field(..., min_length=1, description="API key")
    base_url: str = Field(..., min_length=1, description="API base URL")


class EvaluateRequest(BaseModel):
    # RAG service under test
    rag_base_url: str = Field(..., min_length=1, description="RAG service base URL")
    rag_api_key: str = Field(..., min_length=1, description="RAG service API key")
    rag_model: str = Field(default="deepseek-chat", description="Model name for RAG queries")
    # Evaluation model (Synthesizer + metrics)
    eval_model: Optional[ModelConfig] = Field(default=None, description="LLM for evaluation")
    # Embedding model (chunking)
    embed_model: Optional[ModelConfig] = Field(default=None, description="Embedding model")
    # Existing task
    task_id: Optional[str] = Field(default=None, description="Existing task ID from upload")


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


class ModelsResponse(BaseModel):
    """Response from GET /api/models proxy."""
    data: List[dict]
```

- [ ] **Step 2: Verify import**

```bash
python -c "from app.models import ModelConfig, EvaluateRequest, ModelsResponse; print('OK')"
```

Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add app/models.py
git commit -m "feat: add ModelConfig schema and expand EvaluateRequest for v2"
```

---

### Task 2: GET /api/models Proxy Endpoint

**Files:**
- Create: `tests/test_api_models.py`
- Modify: `app/routes.py`

- [ ] **Step 1: Write the failing test — tests/test_api_models.py**

```python
"""API tests for models proxy endpoint."""

import pytest
from unittest.mock import patch, MagicMock


class TestModelsEndpoint:
    def test_returns_model_list(self, client):
        """Mock a successful /models response from an external API."""
        with patch("httpx.Client.get") as mock_get:
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = {"data": [{"id": "model-a"}, {"id": "model-b"}]}
            mock_get.return_value = mock_resp

            resp = client.get(
                "/api/models",
                params={"base_url": "https://api.example.com", "api_key": "sk-test"},
            )
            assert resp.status_code == 200
            data = resp.json()
            assert len(data["data"]) == 2
            assert data["data"][0]["id"] == "model-a"

    def test_returns_502_when_upstream_fails(self, client):
        """When the external API is unreachable, return 502."""
        with patch("httpx.Client.get") as mock_get:
            mock_get.side_effect = Exception("Connection refused")

            resp = client.get(
                "/api/models",
                params={"base_url": "https://bad.example.com", "api_key": "sk-test"},
            )
            assert resp.status_code == 502
            assert "Connection refused" in resp.json()["detail"]

    def test_missing_params_returns_422(self, client):
        """base_url and api_key are required."""
        resp = client.get("/api/models")
        assert resp.status_code == 422
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/test_api_models.py -v
```

Expected: FAIL — 404 Not Found (route not defined)

- [ ] **Step 3: Implement the endpoint in app/routes.py**

Add import at top of routes.py:

```python
import httpx
```

Add endpoint before `router = APIRouter(prefix="/api")` or in the router:

```python
@router.get("/models")
async def list_models(base_url: str, api_key: str):
    """Proxy to fetch available models from an OpenAI-compatible API."""
    url = base_url.rstrip("/") + "/models"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(url, headers=headers)
            if resp.status_code != 200:
                raise HTTPException(
                    status_code=502,
                    detail=f"Upstream returned {resp.status_code}: {resp.text[:300]}",
                )
            return resp.json()
    except httpx.RequestError as e:
        raise HTTPException(status_code=502, detail=str(e))
```

- [ ] **Step 4: Run test to verify it passes**

```bash
pytest tests/test_api_models.py -v
```

Expected: 3/3 PASS

- [ ] **Step 5: Commit**

```bash
git add tests/test_api_models.py app/routes.py
git commit -m "feat: add GET /api/models proxy endpoint"
```

---

### Task 3: SSE Stream Endpoint

**Files:**
- Create: `tests/test_api_stream.py`
- Modify: `app/routes.py`
- Modify: `app/task_manager.py`

- [ ] **Step 1: Add SSE event queue to task_manager.py**

Add at bottom of `app/task_manager.py` (before the singleton):

```python
import asyncio

# In TaskManager.__init__, add:
        self._queues: Dict[str, asyncio.Queue] = {}

# In TaskManager, add these methods:
    def get_queue(self, task_id: str) -> asyncio.Queue:
        if task_id not in self._queues:
            self._queues[task_id] = asyncio.Queue()
        return self._queues[task_id]

    async def push_event(self, task_id: str, event: str, data: dict) -> None:
        queue = self.get_queue(task_id)
        await queue.put({"event": event, "data": data})

    def cleanup_queue(self, task_id: str) -> None:
        self._queues.pop(task_id, None)
```

- [ ] **Step 2: Write the failing test — tests/test_api_stream.py**

```python
"""API tests for SSE stream endpoint."""

import json
import pytest
import httpx


class TestStreamEndpoint:
    @pytest.mark.asyncio
    async def test_stream_returns_events(self, client, test_task_id):
        """SSE endpoint should stream progress events."""
        from app.task_manager import task_manager

        # Push a test event
        await task_manager.push_event(
            test_task_id, "progress",
            {"phase": "TEST", "progress": 0.5, "message": "testing"}
        )

        # Read SSE stream
        async with httpx.AsyncClient(app=client.app, base_url="http://test") as ac:
            async with ac.stream("GET", f"/api/task/{test_task_id}/stream") as response:
                assert response.status_code == 200
                # Read first event
                lines = []
                async for line in response.aiter_lines():
                    lines.append(line)
                    if line == "":
                        break  # Empty line = end of event

                event_text = "\n".join(lines)
                assert "event: progress" in event_text
                assert "phase" in event_text

    def test_stream_nonexistent_task_returns_404(self, client):
        resp = client.get("/api/task/nonexistent/stream")
        assert resp.status_code == 404
```

- [ ] **Step 3: Run test to verify it fails**

```bash
pytest tests/test_api_stream.py -v
```

Expected: FAIL — 404 (route not defined)

- [ ] **Step 4: Implement SSE endpoint in app/routes.py**

Add import:

```python
from fastapi.responses import StreamingResponse
import json as json_mod
```

Add endpoint:

```python
@router.get("/task/{task_id}/stream")
async def stream_task_progress(task_id: str):
    """SSE endpoint: streams real-time task progress events."""
    state = task_manager.get_state(task_id)
    if state is None:
        raise HTTPException(status_code=404, detail="Task not found")

    queue = task_manager.get_queue(task_id)

    async def event_generator():
        # Send current state immediately
        current = task_manager.get_state(task_id)
        if current:
            yield f"event: progress\ndata: {json_mod.dumps(current)}\n\n"

        # Stream ongoing events
        try:
            while True:
                event = await asyncio.wait_for(queue.get(), timeout=30)
                event_type = event.get("event", "progress")
                yield f"event: {event_type}\ndata: {json_mod.dumps(event['data'])}\n\n"

                # Terminal event: close stream
                if event_type in ("complete", "error"):
                    break
        except asyncio.TimeoutError:
            yield f"event: error\ndata: {{\"error\": \"Stream timeout\"}}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
```

- [ ] **Step 5: Run tests to verify**

```bash
pytest tests/test_api_stream.py -v
```

Expected: 2/2 PASS

- [ ] **Step 6: Commit**

```bash
git add tests/test_api_stream.py app/routes.py app/task_manager.py
git commit -m "feat: add SSE stream endpoint for real-time progress"
```

---

### Task 4: Pipeline v2 — Dynamic Models + Progress Callback

**Files:**
- Modify: `app/pipeline.py`
- Modify: `app/config.py`
- Modify: `app/embedder.py`
- Create: `tests/test_pipeline_v2.py`

- [ ] **Step 1: Simplify config.py — remove eval/embed defaults**

```python
"""Infrastructure configuration for the evaluation platform."""

import os

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

Remove: `EVAL_MODEL_NAME`, `EVAL_MODEL_API_KEY`, `EVAL_MODEL_BASE_URL`, `EMBEDDING_MODEL_NAME`, `EMBEDDING_API_KEY`, `EMBEDDING_BASE_URL`, `RAG_MODEL_NAME`.

- [ ] **Step 2: Update embedder.py — dynamic build_embedder**

Replace `build_embedder()` with:

```python
def build_embedder(config: "ModelConfig"):
    """Build a SiliconFlowEmbeddingModel from a ModelConfig."""
    return SiliconFlowEmbeddingModel(
        api_key=config.api_key,
        model_name=config.model_name,
        base_url=config.base_url,
    )
```

- [ ] **Step 3: Update pipeline.py — dynamic model building**

Replace `build_evaluation_model()` with:

```python
def build_evaluation_model(config: "ModelConfig"):
    """Build a DeepSeekModel (or OpenAI-compatible) from a ModelConfig."""
    return DeepSeekModel(
        api_key=config.api_key,
        model=config.model_name,
        base_url=config.base_url,
    )
```

Update `run_evaluation_pipeline` signature:

```python
async def run_evaluation_pipeline(
    task_id: str,
    eval_config: "ModelConfig",
    embed_config: "ModelConfig",
    rag_model: str = "deepseek-chat",
):
```

Inside the function, replace:
- `model = build_evaluation_model()` → `model = build_evaluation_model(eval_config)`
- `embedder = build_embedder()` → `embedder = build_embedder(embed_config)`
- `rag_client.query(golden["input"], model=RAG_MODEL_NAME)` → `rag_client.query(golden["input"], model=rag_model)`

Add progress callback after each step:

```python
async def _push(event, data):
    await task_manager.push_event(task_id, event, data)

# After model building:
await _push("progress", {"phase": "GENERATING_GOLDENS", "progress": 0.1, "message": "初始化模型..."})

# After Synthesizer created:
await _push("progress", {"phase": "GENERATING_GOLDENS", "progress": 0.2, "message": "正在构建上下文..."})

# After goldens generated:
await _push("progress", {"phase": "GENERATING_GOLDENS", "progress": 0.8, "message": f"生成了 {len(goldens)} 条 goldens"})

# During evaluation loop, after each golden:
await _push("progress", {
    "phase": "RUNNING_EVAL",
    "progress": (idx + 1) / total,
    "message": f"评测 {idx + 1}/{total}...",
    "current_golden": idx + 1,
    "total_goldens": total,
})

# Before metric evaluation:
await _push("progress", {
    "phase": "RUNNING_EVAL",
    "progress": (idx + 0.5) / total,
    "message": f"评测 {idx + 1}/{total}: 运行指标...",
    "current_golden": idx + 1,
    "total_goldens": total,
})

# On complete:
await _push("complete", {"status": "COMPLETED"})

# On error (in except block):
await _push("error", {"status": "FAILED", "error": str(e)})
```

Remove import of `RAG_MODEL_NAME` and eval/embed config constants.

- [ ] **Step 4: Write the failing test — tests/test_pipeline_v2.py**

```python
"""Tests for v2 pipeline with dynamic model config."""

import pytest
from unittest.mock import patch, MagicMock
from app.models import ModelConfig


class TestBuildEvaluationModelV2:
    def test_builds_with_custom_config(self):
        from app.pipeline import build_evaluation_model
        config = ModelConfig(
            provider="openai",
            model_name="gpt-4o",
            api_key="sk-custom",
            base_url="https://api.openai.com/v1",
        )
        with patch("app.pipeline.DeepSeekModel") as MockModel:
            build_evaluation_model(config)
            MockModel.assert_called_once_with(
                api_key="sk-custom",
                model="gpt-4o",
                base_url="https://api.openai.com/v1",
            )


class TestBuildEmbedderV2:
    def test_builds_with_custom_config(self):
        from app.pipeline import build_embedder
        config = ModelConfig(
            provider="siliconflow",
            model_name="BAAI/bge-m3",
            api_key="sk-embed",
            base_url="https://api.siliconflow.cn/v1",
        )
        embedder = build_embedder(config)
        assert embedder._model_name == "BAAI/bge-m3"
        assert embedder._base_url == "https://api.siliconflow.cn/v1"


class TestPipelineProgressCallback:
    @pytest.mark.asyncio
    async def test_pushes_progress_events(self, temp_data_dir):
        """Pipeline should push events during execution."""
        from app.task_manager import task_manager
        from app.models import ModelConfig

        task_id = task_manager.start_task("http://test.com", "sk-test")
        from app.db import init_db, create_task
        init_db(":memory:")
        create_task("http://test.com", "sk-test", task_id=task_id)

        # Just verify the pipeline starts and pushes events for empty docs
        from app.pipeline import run_evaluation_pipeline
        import asyncio

        eval_config = ModelConfig(
            provider="deepseek", model_name="deepseek-chat",
            api_key="sk-test", base_url="https://api.deepseek.com",
        )
        embed_config = ModelConfig(
            provider="siliconflow", model_name="BAAI/bge-m3",
            api_key="sk-test", base_url="https://api.siliconflow.cn/v1",
        )

        # Run pipeline (will fail on empty docs but should push events)
        await run_evaluation_pipeline(task_id, eval_config, embed_config)

        state = task_manager.get_state(task_id)
        assert state["status"] == "FAILED"
        assert state["error_message"] is not None
```

- [ ] **Step 5: Run tests**

```bash
pytest tests/test_pipeline_v2.py -v
```

Expected: 3/3 PASS

- [ ] **Step 6: Update existing tests that reference removed config**

Run all backend tests and fix any that reference removed config constants:

```bash
pytest tests/ -v --ignore=tests/test_pipeline_goldens.py --ignore=tests/test_pipeline_evaluate.py
```

Fix `tests/test_pipeline.py` — update `test_returns_siliconflow_embedder` to pass a `ModelConfig`:

```python
class TestBuildEmbedder:
    def test_returns_siliconflow_embedder(self):
        from app.models import ModelConfig
        config = ModelConfig(
            provider="siliconflow", model_name="BAAI/bge-m3",
            api_key="sk-test", base_url="https://api.siliconflow.cn/v1",
        )
        embedder = build_embedder(config)
        from app.embedder import SiliconFlowEmbeddingModel
        assert isinstance(embedder, SiliconFlowEmbeddingModel)
```

- [ ] **Step 7: Commit**

```bash
git add app/config.py app/embedder.py app/pipeline.py tests/test_pipeline_v2.py tests/test_pipeline.py
git commit -m "feat: dynamic model config — pipeline and embedder accept ModelConfig"
```

---

### Task 5: Evaluate Endpoint v2 — ModelConfig + Duplicate Prevention

**Files:**
- Create: `tests/test_api_evaluate_v2.py`
- Modify: `app/routes.py`

- [ ] **Step 1: Write the failing test — tests/test_api_evaluate_v2.py**

```python
"""API tests for evaluate endpoint v2."""

import pytest


class TestEvaluateV2:
    def test_evaluate_with_model_configs(self, client, test_task_id):
        """POST /api/evaluate with full ModelConfig should start evaluation."""
        resp = client.post(
            "/api/evaluate",
            json={
                "rag_base_url": "https://rag.example.com/v1",
                "rag_api_key": "sk-test-key",
                "rag_model": "deepseek-chat",
                "eval_model": {
                    "provider": "deepseek",
                    "model_name": "deepseek-chat",
                    "api_key": "sk-eval",
                    "base_url": "https://api.deepseek.com",
                },
                "embed_model": {
                    "provider": "siliconflow",
                    "model_name": "BAAI/bge-m3",
                    "api_key": "sk-embed",
                    "base_url": "https://api.siliconflow.cn/v1",
                },
                "task_id": test_task_id,
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["task_id"] == test_task_id

    def test_evaluate_duplicate_returns_409(self, client, test_task_id):
        """Starting evaluation on an already-running task should return 409."""
        # First request: start evaluation
        client.post(
            "/api/evaluate",
            json={
                "rag_base_url": "https://rag.example.com/v1",
                "rag_api_key": "sk-test-key",
                "rag_model": "deepseek-chat",
                "eval_model": {
                    "provider": "deepseek", "model_name": "deepseek-chat",
                    "api_key": "sk-eval", "base_url": "https://api.deepseek.com",
                },
                "embed_model": {
                    "provider": "siliconflow", "model_name": "BAAI/bge-m3",
                    "api_key": "sk-embed", "base_url": "https://api.siliconflow.cn/v1",
                },
                "task_id": test_task_id,
            },
        )
        # Manually set task to RUNNING_EVAL to simulate active evaluation
        from app.task_manager import task_manager, TaskPhase
        task_manager.update_phase(test_task_id, TaskPhase.RUNNING_EVAL, progress=0.5)

        # Second request with same task_id should be rejected
        resp = client.post(
            "/api/evaluate",
            json={
                "rag_base_url": "https://rag.example.com/v1",
                "rag_api_key": "sk-test-key",
                "rag_model": "deepseek-chat",
                "eval_model": {
                    "provider": "deepseek", "model_name": "deepseek-chat",
                    "api_key": "sk-eval", "base_url": "https://api.deepseek.com",
                },
                "embed_model": {
                    "provider": "siliconflow", "model_name": "BAAI/bge-m3",
                    "api_key": "sk-embed", "base_url": "https://api.siliconflow.cn/v1",
                },
                "task_id": test_task_id,
            },
        )
        assert resp.status_code == 409
        assert "正在运行" in resp.json()["detail"]

    def test_evaluate_missing_model_config_returns_422(self, client, test_task_id):
        """eval_model and embed_model should be required."""
        resp = client.post(
            "/api/evaluate",
            json={
                "rag_base_url": "https://rag.example.com/v1",
                "rag_api_key": "sk-test-key",
                "task_id": test_task_id,
            },
        )
        assert resp.status_code == 422
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/test_api_evaluate_v2.py -v
```

Expected: Some tests FAIL — missing validation, no lock

- [ ] **Step 3: Update evaluate endpoint in app/routes.py**

```python
# Per-task locks to prevent duplicate submissions
_evaluate_locks: dict = {}

@router.post("/evaluate")
async def start_evaluation(req: EvaluateRequest, background_tasks: BackgroundTasks):
    task_id = req.task_id

    if task_id:
        state = task_manager.get_state(task_id)
        if state is None:
            raise HTTPException(status_code=404, detail="Task not found")

        # Prevent duplicate submissions
        if state["status"] in ("GENERATING_GOLDENS", "RUNNING_EVAL"):
            raise HTTPException(
                status_code=409,
                detail=f"任务正在运行中 (当前: {state['status']})，请等待完成",
            )

        state["rag_base_url"] = req.rag_base_url
        state["rag_api_key"] = req.rag_api_key
        update_task_status(task_id, state["status"])
    else:
        task_id = task_manager.start_task(req.rag_base_url, req.rag_api_key)
        create_task(req.rag_base_url, req.rag_api_key, task_id=task_id)

    # Use default model configs if not provided
    eval_config = req.eval_model or ModelConfig(
        provider="deepseek", model_name="deepseek-chat",
        api_key=os.getenv("DEEPSEEK_API_KEY", ""),
        base_url="https://api.deepseek.com",
    )
    embed_config = req.embed_model or ModelConfig(
        provider="siliconflow", model_name="BAAI/bge-m3",
        api_key=os.getenv("EMBEDDING_API_KEY", ""),
        base_url="https://api.siliconflow.cn/v1",
    )

    async def _run():
        try:
            await run_evaluation_pipeline(
                task_id, eval_config, embed_config, req.rag_model,
            )
        except Exception as e:
            import logging
            logging.getLogger("uvicorn.error").error(f"Pipeline failed: {e}")
    asyncio.create_task(_run())

    return {"task_id": task_id}
```

Add `import os` at top of routes.py.

- [ ] **Step 4: Run tests to verify**

```bash
pytest tests/test_api_evaluate_v2.py -v
```

Expected: 3/3 PASS

- [ ] **Step 5: Commit**

```bash
git add tests/test_api_evaluate_v2.py app/routes.py
git commit -m "feat: evaluate endpoint v2 — ModelConfig support + duplicate prevention"
```

---

### Task 6: Frontend — ModelSelector Component

**Files:**
- Create: `frontend/src/components/ModelSelector.tsx`
- Create: `frontend/src/__tests__/ModelSelector.test.tsx`

- [ ] **Step 1: Install sonner**

```bash
cd frontend && npm install sonner
```

- [ ] **Step 2: Create frontend/src/components/ModelSelector.tsx**

```tsx
import { useState } from 'react';
import { Loader2, RefreshCw, Eye, EyeOff } from 'lucide-react';

interface ModelConfig {
  provider: string;
  model_name: string;
  api_key: string;
  base_url: string;
}

interface Props {
  label: string;
  value: ModelConfig;
  onChange: (config: ModelConfig) => void;
}

const PROVIDERS: Record<string, { base_url: string; models: string[] }> = {
  deepseek: {
    base_url: 'https://api.deepseek.com',
    models: ['deepseek-chat', 'deepseek-v4-flash', 'deepseek-v4-pro'],
  },
  openai: {
    base_url: 'https://api.openai.com/v1',
    models: ['gpt-4o', 'gpt-4o-mini', 'gpt-4.1'],
  },
  anthropic: {
    base_url: 'https://api.anthropic.com',
    models: ['claude-sonnet-4-6', 'claude-opus-4-8'],
  },
  siliconflow: {
    base_url: 'https://api.siliconflow.cn/v1',
    models: ['BAAI/bge-m3', 'Pro/BAAI/bge-m3', 'Qwen/Qwen2.5-7B-Instruct'],
  },
  custom: { base_url: '', models: [] },
};

export function ModelSelector({ label, value, onChange }: Props) {
  const [showKey, setShowKey] = useState(false);
  const [fetching, setFetching] = useState(false);
  const [models, setModels] = useState<string[]>([]);

  function update(fields: Partial<ModelConfig>) {
    onChange({ ...value, ...fields });
  }

  async function fetchModels() {
    if (!value.base_url || !value.api_key) return;
    setFetching(true);
    try {
      const res = await fetch(
        `http://localhost:8000/api/models?base_url=${encodeURIComponent(value.base_url)}&api_key=${encodeURIComponent(value.api_key)}`
      );
      if (!res.ok) throw new Error('Failed');
      const data = await res.json();
      const ids = (data.data || []).map((m: { id: string }) => m.id);
      setModels(ids);
    } catch {
      // Fall back to preset models
      setModels(PROVIDERS[value.provider]?.models || []);
    } finally {
      setFetching(false);
    }
  }

  function handleProviderChange(provider: string) {
    const preset = PROVIDERS[provider] || PROVIDERS.custom;
    update({ provider, base_url: preset.base_url });
    setModels(preset.models);
  }

  const allModels = models.length > 0 ? models : (PROVIDERS[value.provider]?.models || []);

  return (
    <div className="border rounded-lg bg-white p-4 space-y-3">
      <h4 className="text-sm font-semibold text-slate-700">{label}</h4>

      {/* Provider */}
      <div>
        <label className="block text-xs font-medium text-slate-500 mb-1">Provider</label>
        <select
          className="w-full border rounded-md px-3 py-2 text-sm"
          value={value.provider}
          onChange={(e) => handleProviderChange(e.target.value)}
        >
          <option value="deepseek">DeepSeek</option>
          <option value="openai">OpenAI</option>
          <option value="anthropic">Anthropic</option>
          <option value="siliconflow">SiliconFlow</option>
          <option value="custom">Custom</option>
        </select>
      </div>

      {/* Base URL */}
      <div>
        <label className="block text-xs font-medium text-slate-500 mb-1">Base URL</label>
        <input
          className="w-full border rounded-md px-3 py-2 text-sm"
          placeholder="https://api.example.com/v1"
          value={value.base_url}
          onChange={(e) => update({ base_url: e.target.value })}
        />
      </div>

      {/* API Key */}
      <div>
        <label className="block text-xs font-medium text-slate-500 mb-1">API Key</label>
        <div className="relative">
          <input
            type={showKey ? 'text' : 'password'}
            className="w-full border rounded-md px-3 py-2 text-sm pr-10"
            placeholder="sk-..."
            value={value.api_key}
            onChange={(e) => update({ api_key: e.target.value })}
          />
          <button
            type="button"
            className="absolute right-2 top-2 text-slate-400 hover:text-slate-600"
            onClick={() => setShowKey(!showKey)}
          >
            {showKey ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
          </button>
        </div>
      </div>

      {/* Model */}
      <div>
        <label className="block text-xs font-medium text-slate-500 mb-1">Model</label>
        <div className="flex gap-2">
          {allModels.length > 0 ? (
            <select
              className="flex-1 border rounded-md px-3 py-2 text-sm"
              value={value.model_name}
              onChange={(e) => update({ model_name: e.target.value })}
            >
              {allModels.map((m) => (
                <option key={m} value={m}>{m}</option>
              ))}
            </select>
          ) : (
            <input
              className="flex-1 border rounded-md px-3 py-2 text-sm"
              placeholder="model-name"
              value={value.model_name}
              onChange={(e) => update({ model_name: e.target.value })}
            />
          )}
          <button
            type="button"
            className="px-3 py-2 border rounded-md text-sm text-slate-600 hover:bg-slate-50 disabled:opacity-50 flex items-center gap-1"
            onClick={fetchModels}
            disabled={fetching || !value.base_url || !value.api_key}
          >
            {fetching ? <Loader2 className="w-3 h-3 animate-spin" /> : <RefreshCw className="w-3 h-3" />}
            获取
          </button>
        </div>
      </div>
    </div>
  );
}

export type { ModelConfig };
```

- [ ] **Step 3: Write component test — frontend/src/__tests__/ModelSelector.test.tsx**

```tsx
import { describe, it, expect, vi } from 'vitest';
import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { renderWithProviders } from './test-utils';
import { ModelSelector } from '../components/ModelSelector';

describe('ModelSelector', () => {
  const defaultConfig = {
    provider: 'deepseek',
    model_name: 'deepseek-chat',
    api_key: '',
    base_url: 'https://api.deepseek.com',
  };

  it('renders provider selector', () => {
    renderWithProviders(
      <ModelSelector label="Test Model" value={defaultConfig} onChange={vi.fn()} />
    );
    expect(screen.getByText('Test Model')).toBeInTheDocument();
    expect(screen.getByDisplayValue('deepseek-chat')).toBeInTheDocument();
  });

  it('auto-fills base_url when provider changes', async () => {
    const onChange = vi.fn();
    renderWithProviders(
      <ModelSelector label="Test" value={{ ...defaultConfig, provider: 'custom', base_url: '' }} onChange={onChange} />
    );
    const select = screen.getByRole('combobox');
    await userEvent.selectOptions(select, 'deepseek');
    expect(onChange).toHaveBeenCalledWith(
      expect.objectContaining({ provider: 'deepseek', base_url: 'https://api.deepseek.com' })
    );
  });

  it('has password visibility toggle', async () => {
    renderWithProviders(
      <ModelSelector label="Test" value={defaultConfig} onChange={vi.fn()} />
    );
    const input = screen.getByPlaceholderText('sk-...');
    expect(input).toHaveAttribute('type', 'password');
    const toggle = screen.getByRole('button', { name: '' });
    await userEvent.click(toggle);
    expect(input).toHaveAttribute('type', 'text');
  });
});
```

- [ ] **Step 4: Run component tests**

```bash
cd frontend && npx vitest run --root frontend src/__tests__/ModelSelector.test.tsx
```

Expected: 3/3 PASS

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/ModelSelector.tsx frontend/src/__tests__/ModelSelector.test.tsx frontend/package.json frontend/package-lock.json
git commit -m "feat: add ModelSelector component with provider presets"
```

---

### Task 7: Frontend API Client Updates

**Files:**
- Modify: `frontend/src/api/client.ts`
- Modify: `frontend/src/hooks/useApi.ts`

- [ ] **Step 1: Update client.ts — add fetchModels, timeout, abort**

```typescript
import type { UploadResponse, EvaluateRequest, EvaluateResponse, TaskStatus, GoldenItem, TaskResult, HistoryItem } from '../types';

const API_BASE = 'http://localhost:8000/api';
const DEFAULT_TIMEOUT = 30000;

async function request<T>(path: string, options?: RequestInit & { timeout?: number }): Promise<T> {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), options?.timeout || DEFAULT_TIMEOUT);

  try {
    const res = await fetch(`${API_BASE}${path}`, {
      headers: { 'Content-Type': 'application/json', ...options?.headers },
      signal: controller.signal,
      ...options,
    });
    if (!res.ok) {
      const detail = await res.json().catch(() => ({ detail: res.statusText }));
      throw new Error(detail.detail || `HTTP ${res.status}`);
    }
    return res.json();
  } finally {
    clearTimeout(timeout);
  }
}

export async function uploadFiles(files: FileList | File[]): Promise<UploadResponse> {
  const form = new FormData();
  Array.from(files).forEach((f) => form.append('files', f));
  const res = await fetch(`${API_BASE}/upload`, { method: 'POST', body: form });
  if (!res.ok) throw new Error((await res.json()).detail || 'Upload failed');
  return res.json();
}

export async function fetchModels(baseUrl: string, apiKey: string): Promise<{ data: { id: string }[] }> {
  const params = new URLSearchParams({ base_url: baseUrl, api_key: apiKey });
  return request(`/models?${params}`);
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

  fetchModels,
};
```

- [ ] **Step 2: Update hooks/useApi.ts — add useSSE hook**

Add after existing hooks:

```typescript
import { useEffect, useState } from 'react';

export function useTaskSSE(taskId: string | null) {
  const [progress, setProgress] = useState<{
    phase: string;
    progress: number;
    message: string;
    error?: string;
  } | null>(null);
  const [status, setStatus] = useState<string | null>(null);

  useEffect(() => {
    if (!taskId) return;

    const es = new EventSource(`http://localhost:8000/api/task/${taskId}/stream`);

    es.addEventListener('progress', (e) => {
      const data = JSON.parse(e.data);
      setProgress(data);
      setStatus(data.phase);
    });

    es.addEventListener('complete', (e) => {
      const data = JSON.parse(e.data);
      setStatus(data.status);
      es.close();
    });

    es.addEventListener('error', (e) => {
      try {
        const data = JSON.parse((e as MessageEvent).data);
        setProgress((prev) => prev ? { ...prev, error: data.error } : null);
        setStatus('FAILED');
      } catch {
        // Connection error — EventSource auto-reconnects
      }
    });

    return () => es.close();
  }, [taskId]);

  return { progress, status };
}
```

- [ ] **Step 3: Verify TypeScript compiles**

```bash
cd frontend && npx tsc --noEmit
```

- [ ] **Step 4: Commit**

```bash
git add frontend/src/api/client.ts frontend/src/hooks/useApi.ts
git commit -m "feat: add fetchModels API, request timeout/abort, and SSE hook"
```

---

### Task 8: RagConfigForm v2 — Three Model Cards

**Files:**
- Modify: `frontend/src/components/RagConfigForm.tsx`
- Modify: `frontend/src/pages/ConfigPage.tsx`
- Create: `frontend/src/__tests__/RagConfigForm-v2.test.tsx`

- [ ] **Step 1: Rewrite RagConfigForm.tsx with three sections**

```tsx
import { useState, type FormEvent } from 'react';
import { ModelSelector, type ModelConfig } from './ModelSelector';

export interface FullConfig {
  rag_base_url: string;
  rag_api_key: string;
  rag_model: string;
  eval_model: ModelConfig;
  embed_model: ModelConfig;
}

interface Props {
  onSubmit: (config: FullConfig) => void;
}

const DEFAULT_EVAL: ModelConfig = {
  provider: 'deepseek',
  model_name: 'deepseek-chat',
  api_key: '',
  base_url: 'https://api.deepseek.com',
};

const DEFAULT_EMBED: ModelConfig = {
  provider: 'siliconflow',
  model_name: 'BAAI/bge-m3',
  api_key: '',
  base_url: 'https://api.siliconflow.cn/v1',
};

export function RagConfigForm({ onSubmit }: Props) {
  const [ragUrl, setRagUrl] = useState('');
  const [ragKey, setRagKey] = useState('');
  const [ragModel, setRagModel] = useState('deepseek-chat');
  const [evalModel, setEvalModel] = useState<ModelConfig>(DEFAULT_EVAL);
  const [embedModel, setEmbedModel] = useState<ModelConfig>(DEFAULT_EMBED);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [saved, setSaved] = useState(false);

  function handleSubmit(e: FormEvent) {
    e.preventDefault();
    const errs: Record<string, string> = {};
    if (!ragUrl.trim()) errs.ragUrl = 'RAG Base URL is required';
    if (!ragKey.trim()) errs.ragKey = 'RAG API Key is required';
    if (!evalModel.api_key) errs.evalKey = 'Evaluation API Key is required';
    if (!embedModel.api_key) errs.embedKey = 'Embedding API Key is required';
    if (Object.keys(errs).length) {
      setErrors(errs);
      return;
    }
    setErrors({});
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
    onSubmit({
      rag_base_url: ragUrl.trim(),
      rag_api_key: ragKey.trim(),
      rag_model: ragModel.trim() || 'deepseek-chat',
      eval_model: evalModel,
      embed_model: embedModel,
    });
  }

  return (
    <div className="space-y-4">
      {/* RAG Service Card */}
      <div className="border rounded-lg bg-white p-4 space-y-3">
        <h4 className="text-sm font-semibold text-slate-700">RAG Service</h4>
        <div>
          <label className="block text-xs font-medium text-slate-500 mb-1">Base URL</label>
          <input
            className="w-full border rounded-md px-3 py-2 text-sm"
            placeholder="https://your-rag-service.com/v1"
            value={ragUrl}
            onChange={(e) => setRagUrl(e.target.value)}
          />
          {errors.ragUrl && <p className="text-red-500 text-xs mt-1">{errors.ragUrl}</p>}
        </div>
        <div>
          <label className="block text-xs font-medium text-slate-500 mb-1">API Key</label>
          <input
            type="password"
            className="w-full border rounded-md px-3 py-2 text-sm"
            placeholder="sk-..."
            value={ragKey}
            onChange={(e) => setRagKey(e.target.value)}
          />
          {errors.ragKey && <p className="text-red-500 text-xs mt-1">{errors.ragKey}</p>}
        </div>
        <div>
          <label className="block text-xs font-medium text-slate-500 mb-1">Model Name</label>
          <input
            className="w-full border rounded-md px-3 py-2 text-sm"
            placeholder="deepseek-chat"
            value={ragModel}
            onChange={(e) => setRagModel(e.target.value)}
          />
        </div>
      </div>

      {/* Evaluation Model */}
      <ModelSelector label="Evaluation Model" value={evalModel} onChange={setEvalModel} />
      {errors.evalKey && <p className="text-red-500 text-xs">{errors.evalKey}</p>}

      {/* Embedding Model */}
      <ModelSelector label="Embedding Model" value={embedModel} onChange={setEmbedModel} />
      {errors.embedKey && <p className="text-red-500 text-xs">{errors.embedKey}</p>}

      {/* Submit */}
      <button
        type="submit"
        onClick={handleSubmit}
        className={`w-full py-3 rounded-md text-white font-medium text-sm transition-all active:scale-95 ${
          saved ? 'bg-green-600' : 'bg-slate-900 hover:bg-slate-800'
        }`}
      >
        {saved ? '✓ Configuration Saved' : 'Save Configuration'}
      </button>
    </div>
  );
}
```

- [ ] **Step 2: Update ConfigPage.tsx — pass full config**

Update the `handleStart` to pass the full config:

```tsx
async function handleStart() {
    if (!fullConfig || !taskId) return;
    try {
      await startEval.mutateAsync({
        rag_base_url: fullConfig.rag_base_url,
        rag_api_key: fullConfig.rag_api_key,
        rag_model: fullConfig.rag_model,
        eval_model: fullConfig.eval_model,
        embed_model: fullConfig.embed_model,
        task_id: taskId,
      });
      navigate(`/task/${taskId}/progress`);
    } catch (err: any) {
      toast.error(`Failed to start: ${err.message}`);
    }
  }
```

Change `ragConfig` state to `fullConfig` of type `FullConfig | null`.

- [ ] **Step 3: Write test — RagConfigForm-v2.test.tsx**

```tsx
import { describe, it, expect, vi } from 'vitest';
import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { renderWithProviders } from './test-utils';
import { RagConfigForm } from '../components/RagConfigForm';

describe('RagConfigForm v2', () => {
  it('renders three config sections', () => {
    renderWithProviders(<RagConfigForm onSubmit={vi.fn()} />);
    expect(screen.getByText('RAG Service')).toBeInTheDocument();
    expect(screen.getByText('Evaluation Model')).toBeInTheDocument();
    expect(screen.getByText('Embedding Model')).toBeInTheDocument();
  });

  it('shows validation errors for missing API keys', async () => {
    const onSubmit = vi.fn();
    renderWithProviders(<RagConfigForm onSubmit={onSubmit} />);
    await userEvent.click(screen.getByRole('button', { name: /save/i }));
    expect(onSubmit).not.toHaveBeenCalled();
    expect(screen.getByText(/RAG Base URL is required/i)).toBeInTheDocument();
  });

  it('calls onSubmit with full config when valid', async () => {
    const onSubmit = vi.fn();
    renderWithProviders(<RagConfigForm onSubmit={onSubmit} />);
    const user = userEvent.setup();

    // Fill RAG
    const ragUrlInput = screen.getAllByPlaceholderText(/https:\/\/your-rag/i)[0];
    await user.type(ragUrlInput, 'https://rag.test.com');
    // Fill RAG key
    const keyInputs = screen.getAllByPlaceholderText('sk-...');
    await user.type(keyInputs[0], 'sk-rag');
    // Fill eval key
    await user.type(keyInputs[1], 'sk-eval');
    // Fill embed key
    await user.type(keyInputs[2], 'sk-embed');

    await user.click(screen.getByRole('button', { name: /save/i }));
    expect(onSubmit).toHaveBeenCalledWith(
      expect.objectContaining({
        rag_base_url: 'https://rag.test.com',
        rag_api_key: 'sk-rag',
        eval_model: expect.objectContaining({ api_key: 'sk-eval' }),
        embed_model: expect.objectContaining({ api_key: 'sk-embed' }),
      })
    );
  });
});
```

- [ ] **Step 4: Run tests**

```bash
cd frontend && npx vitest run --root frontend src/__tests__/RagConfigForm-v2.test.tsx
```

Expected: 3/3 PASS

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/RagConfigForm.tsx frontend/src/pages/ConfigPage.tsx frontend/src/__tests__/RagConfigForm-v2.test.tsx
git commit -m "feat: RagConfigForm v2 — three model config cards with validation"
```

---

### Task 9: ProgressPage v2 — SSE Real-Time

**Files:**
- Modify: `frontend/src/pages/ProgressPage.tsx`
- Modify: `frontend/src/components/ProgressTracker.tsx`
- Create: `frontend/src/__tests__/ProgressPage-v2.test.tsx`

- [ ] **Step 1: Rewrite ProgressPage with SSE**

```tsx
import { useParams, useNavigate } from 'react-router-dom';
import { useTaskSSE } from '../hooks/useApi';
import { ProgressTracker } from '../components/ProgressTracker';
import { Loader2, AlertCircle, ArrowLeft, RotateCcw } from 'lucide-react';

export function ProgressPage() {
  const { taskId } = useParams<{ taskId: string }>();
  const navigate = useNavigate();
  const { progress, status } = useTaskSSE(taskId ?? null);

  // Handle terminal states
  if (status === 'COMPLETED') {
    setTimeout(() => navigate(`/task/${taskId}/results`), 2000);
  }

  if (!progress) {
    return (
      <div className="max-w-xl mx-auto py-12 text-center">
        <Loader2 className="w-8 h-8 animate-spin mx-auto text-blue-500" />
        <p className="text-slate-500 mt-4">Connecting to evaluation stream...</p>
      </div>
    );
  }

  if (status === 'FAILED' || progress.error) {
    return (
      <div className="max-w-xl mx-auto space-y-6">
        <h2 className="text-xl font-bold">Evaluation Failed</h2>
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 flex items-start gap-3">
          <AlertCircle className="w-5 h-5 text-red-500 mt-0.5" />
          <div>
            <p className="text-sm font-medium text-red-800">Error</p>
            <p className="text-sm text-red-600">{progress.error || 'Unknown error'}</p>
          </div>
        </div>
        <div className="flex gap-3">
          <button
            onClick={() => navigate('/')}
            className="flex items-center gap-2 px-4 py-2 border rounded-md text-sm hover:bg-slate-50"
          >
            <ArrowLeft className="w-4 h-4" /> Back to Config
          </button>
          <button
            onClick={() => window.location.reload()}
            className="flex items-center gap-2 px-4 py-2 bg-slate-900 text-white rounded-md text-sm hover:bg-slate-800"
          >
            <RotateCcw className="w-4 h-4" /> Retry
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-xl mx-auto space-y-6">
      <h2 className="text-xl font-bold">Evaluation Progress</h2>
      <ProgressTracker
        phase={progress.phase}
        progress={progress.progress}
        status={progress.phase}
        message={progress.message}
      />
    </div>
  );
}
```

- [ ] **Step 2: Update ProgressTracker to show message**

Add `message?: string` prop. Show it below the progress bar:

```tsx
{message && (
  <p className="text-sm text-slate-600 bg-slate-50 p-3 rounded-md flex items-center gap-2">
    <Loader2 className="w-4 h-4 animate-spin text-blue-500" />
    {message}
  </p>
)}
```

- [ ] **Step 3: Write test — ProgressPage-v2.test.tsx**

```tsx
import { describe, it, expect, vi } from 'vitest';
import { screen } from '@testing-library/react';
import { renderWithProviders } from './test-utils';
import { ProgressPage } from '../pages/ProgressPage';

// Mock EventSource
class MockEventSource {
  onmessage: ((e: any) => void) | null = null;
  addEventListener(_type: string, _handler: any) {}
  close() {}
}
(global as any).EventSource = MockEventSource;

describe('ProgressPage v2', () => {
  it('shows loading state initially', () => {
    renderWithProviders(<ProgressPage />);
    expect(screen.getByText(/connecting/i)).toBeInTheDocument();
  });
});
```

- [ ] **Step 4: Run tests**

```bash
cd frontend && npx vitest run --root frontend src/__tests__/ProgressPage-v2.test.tsx
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add frontend/src/pages/ProgressPage.tsx frontend/src/components/ProgressTracker.tsx frontend/src/__tests__/ProgressPage-v2.test.tsx
git commit -m "feat: ProgressPage v2 — SSE real-time progress with error/loading states"
```

---

### Task 10: UX Improvements — Toast, Button Feedback, Error Handling

**Files:**
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/pages/GoldensPage.tsx`
- Modify: `frontend/src/pages/ResultsPage.tsx`
- Modify: `frontend/src/components/ConfirmButton.tsx`

- [ ] **Step 1: Add Toaster to App.tsx**

Add import and `<Toaster />`:

```tsx
import { Toaster } from 'sonner'

// Inside QueryClientProvider, add before BrowserRouter:
<Toaster position="top-right" richColors />
```

- [ ] **Step 2: Update GoldensPage — toast + try/catch**

Replace `alert()` pattern with toast:

```tsx
import { toast } from 'sonner';

async function handleConfirm() {
    if (!taskId) return;
    try {
      await confirm.mutateAsync(taskId);
      navigate(`/task/${taskId}/progress`);
    } catch (err: any) {
      toast.error(`Confirmation failed: ${err.message}`);
    }
  }
```

Add loading state, error state, and empty state handling.

- [ ] **Step 3: Update ResultsPage — loading skeleton + empty state**

Add isLoading check with spinner, error state with retry:

```tsx
if (isLoading) {
    return (
      <div className="max-w-4xl mx-auto py-12 text-center">
        <Loader2 className="w-8 h-8 animate-spin mx-auto text-blue-500" />
        <p className="text-slate-500 mt-4">Loading results...</p>
      </div>
    );
  }

  if (!results) {
    return (
      <div className="max-w-4xl mx-auto py-12 text-center">
        <p className="text-slate-500">No results available.</p>
      </div>
    );
  }
```

- [ ] **Step 4: Update ConfirmButton — click animation**

Add `active:scale-95 transition-transform` to the button className.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/App.tsx frontend/src/pages/GoldensPage.tsx frontend/src/pages/ResultsPage.tsx frontend/src/components/ConfirmButton.tsx
git commit -m "feat: UX improvements — toast notifications, loading states, click feedback"
```

---

### Task 11: FileUploader v2 — Progress Bar + File Delete

**Files:**
- Modify: `frontend/src/components/FileUploader.tsx`
- Create: `frontend/src/__tests__/FileUploader-v2.test.tsx`

- [ ] **Step 1: Rewrite FileUploader with progress and delete**

Key additions:
- Upload progress tracking via XMLHttpRequest (track `upload.progress` event)
- Delete button (X) per file
- Drag hover scale animation (`hover:scale-[1.02]`)

```tsx
// In handleUpload, use XMLHttpRequest for progress:
function uploadWithProgress(file: File): Promise<void> {
    return new Promise((resolve, reject) => {
      const xhr = new XMLHttpRequest();
      const formData = new FormData();
      formData.append('files', file);

      xhr.upload.addEventListener('progress', (e) => {
        if (e.lengthComputable) {
          const pct = Math.round((e.loaded / e.total) * 100);
          setUploadProgress((prev) => ({ ...prev, [file.name]: pct }));
        }
      });

      xhr.addEventListener('load', () => {
        if (xhr.status >= 200 && xhr.status < 300) resolve();
        else reject(new Error(`Upload failed: ${xhr.status}`));
      });

      xhr.addEventListener('error', () => reject(new Error('Upload failed')));
      xhr.open('POST', 'http://localhost:8000/api/upload');
      xhr.send(formData);
    });
  }
```

Add `removeFile(id: number)` callback. Show progress bar per file:

```tsx
{uploadProgress[f.filename] !== undefined && uploadProgress[f.filename] < 100 && (
  <div className="w-full bg-slate-200 rounded-full h-1.5 mt-1">
    <div
      className="bg-blue-500 h-1.5 rounded-full transition-all duration-300"
      style={{ width: `${uploadProgress[f.filename]}%` }}
    />
  </div>
)}
```

- [ ] **Step 2: Write test — FileUploader-v2.test.tsx**

```tsx
import { describe, it, expect, vi } from 'vitest';
import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { renderWithProviders } from './test-utils';
import { FileUploader } from '../components/FileUploader';

describe('FileUploader v2', () => {
  it('shows delete button on uploaded files', () => {
    renderWithProviders(
      <FileUploader
        onUpload={vi.fn()}
        onRemove={vi.fn()}
        files={[{ id: 1, filename: 'doc.txt', file_size: 1024 }]}
      />
    );
    expect(screen.getByText('doc.txt')).toBeInTheDocument();
    // Should have a remove button
    const removeBtn = screen.getByRole('button', { name: /remove/i });
    expect(removeBtn).toBeInTheDocument();
  });
});
```

- [ ] **Step 3: Update types/index.ts (add ModelConfig)**

```typescript
export interface ModelConfig {
  provider: string;
  model_name: string;
  api_key: string;
  base_url: string;
}
```

And update `EvaluateRequest` to include `eval_model: ModelConfig; embed_model: ModelConfig; rag_model: string;`.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/FileUploader.tsx frontend/src/__tests__/FileUploader-v2.test.tsx frontend/src/types/index.ts
git commit -m "feat: FileUploader v2 — upload progress bar and file deletion"
```

---

### Task 12: Final Integration Verification

- [ ] **Step 1: Run all backend tests**

```bash
pytest tests/ -v --ignore=tests/test_pipeline_goldens.py --ignore=tests/test_pipeline_evaluate.py
```

Expected: All tests PASS

- [ ] **Step 3: Run all frontend tests**

```bash
cd frontend && npx vitest run --root frontend
```

Expected: All tests PASS

- [ ] **Step 4: TypeScript check + build**

```bash
cd frontend && npx tsc --noEmit && npm run build
```

Expected: No errors

- [ ] **Step 5: Commit**

```bash
git add frontend/src/types/index.ts
git commit -m "chore: update TypeScript types for v2 models"
```
