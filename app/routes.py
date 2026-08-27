"""FastAPI route handlers."""

import os
import json as json_mod
import asyncio as _asyncio
from typing import List, Optional

import httpx
import asyncio
from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.db import (
    init_db,
    create_task,
    get_task,
    update_task_status,
    add_document,
    get_documents,
    get_goldens,
    update_golden as update_golden_db,
    delete_golden as delete_golden_db,
    add_golden as add_golden_db,
    get_eval_results,
    get_all_tasks,
)
from app.storage import save_uploaded_file, ensure_task_dir
from app.models import (
    EvaluateRequest,
    ModelConfig,
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


@router.get("/models")
async def list_models(base_url: str, api_key: str):
    """Proxy to fetch available models from an OpenAI-compatible API."""
    url = base_url.rstrip("/") + "/models"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    try:
        async with httpx.AsyncClient(timeout=10) as http_client:
            resp = await http_client.get(url, headers=headers)
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))

    if resp.status_code != 200:
        raise HTTPException(
            status_code=502,
            detail=f"Upstream returned {resp.status_code}: {resp.text[:300]}",
        )
    return resp.json()


@router.post("/upload")
async def upload_files(files: List[UploadFile] = File(...)):
    if not files:
        raise HTTPException(status_code=422, detail="No files provided")

    task_id = task_manager.start_task(
        rag_base_url="",
        rag_api_key="",
    )
    # Persist task to DB so FK constraints are satisfied
    create_task("", "", task_id=task_id)
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
async def start_evaluation(req: EvaluateRequest):
    task_id = req.task_id

    if task_id:
        state = task_manager.get_state(task_id)
        if state is None:
            raise HTTPException(status_code=404, detail="Task not found")

        # Prevent duplicate submissions: task is already in the pipeline
        if state["status"] != "UPLOADING":
            raise HTTPException(
                status_code=409,
                detail=f"Task is already running (current: {state['status']})",
            )

        state["rag_base_url"] = req.rag_base_url
        state["rag_api_key"] = req.rag_api_key
        # Sync status to DB; ignore if DB is already in terminal state
        try:
            update_task_status(task_id, state["status"])
        except ValueError:
            pass
    else:
        task_id = task_manager.start_task(req.rag_base_url, req.rag_api_key)
        create_task(req.rag_base_url, req.rag_api_key, task_id=task_id)

    # Use defaults if model configs not provided
    eval_config = req.eval_model or ModelConfig.model_construct(
        provider="deepseek", api_format="openai_chat", model_name="deepseek-chat",
        api_key=os.getenv("DEEPSEEK_API_KEY", ""),
        base_url="https://api.deepseek.com",
    )
    embed_config = req.embed_model or ModelConfig.model_construct(
        provider="siliconflow", api_format="openai_chat", model_name="BAAI/bge-m3",
        api_key=os.getenv("EMBEDDING_API_KEY", ""),
        base_url="https://api.siliconflow.cn/v1",
    )

    async def _run():
        try:
            await run_evaluation_pipeline(task_id, eval_config, embed_config, req.rag_model)
        except Exception as e:
            import logging
            logging.getLogger("uvicorn.error").error(f"Pipeline failed: {e}")
    asyncio.create_task(_run())

    return {"task_id": task_id}


@router.get("/task/{task_id}")
async def get_task_status(task_id: str):
    state = task_manager.get_state(task_id)
    if state is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return TaskStatus(**state).model_dump()


@router.get("/task/{task_id}/stream")
async def stream_task_progress(task_id: str):
    """SSE endpoint: streams real-time task progress events."""
    state = task_manager.get_state(task_id)
    if state is None:
        raise HTTPException(status_code=404, detail="Task not found")

    queue = task_manager.get_queue(task_id)

    async def event_generator():
        current = task_manager.get_state(task_id)
        if current:
            yield f"event: progress\ndata: {json_mod.dumps(current)}\n\n"

        try:
            while True:
                event = await _asyncio.wait_for(queue.get(), timeout=30)
                event_type = event.get("event", "progress")
                yield f"event: {event_type}\ndata: {json_mod.dumps(event['data'])}\n\n"
                if event_type in ("complete", "error"):
                    break
        except _asyncio.TimeoutError:
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


class GoldenUpdate(BaseModel):
    """测试样本编辑请求体。"""
    input: Optional[str] = None
    expected_output: Optional[str] = None
    context: Optional[str] = None


class GoldenCreate(BaseModel):
    """手动添加测试样本请求体。"""
    input: str
    expected_output: str
    context: Optional[str] = None


@router.put("/goldens/{golden_id}")
async def update_golden(golden_id: int, req: GoldenUpdate):
    """编辑测试样本（问题 / 期望答案 / 来源片段）。"""
    if not update_golden_db(golden_id, req.input, req.expected_output, req.context):
        raise HTTPException(status_code=404, detail="Golden not found")
    return {"status": "updated"}


@router.delete("/goldens/{golden_id}")
async def delete_golden(golden_id: int):
    """删除测试样本（关联评估结果级联删除）。"""
    if not delete_golden_db(golden_id):
        raise HTTPException(status_code=404, detail="Golden not found")
    return {"status": "deleted"}


@router.post("/goldens/{task_id}")
async def add_manual_golden(task_id: str, req: GoldenCreate):
    """手动添加测试样本。"""
    state = task_manager.get_state(task_id)
    if state is None:
        raise HTTPException(status_code=404, detail="Task not found")
    golden_id = add_golden_db(task_id, req.input, req.expected_output, req.context)
    return {"id": golden_id}


@router.get("/results/{task_id}")
async def get_results(task_id: str):
    state = task_manager.get_state(task_id)
    if state is None or state["status"] not in ("COMPLETED", "FAILED"):
        raise HTTPException(status_code=404, detail="Results not available")

    results = get_eval_results(task_id)
    details = []
    all_metric_names = set()

    for r in results:
        metrics_json = json_mod.loads(r["metrics_json"]) if isinstance(r["metrics_json"], str) else r["metrics_json"]
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
