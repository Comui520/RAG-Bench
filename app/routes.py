"""FastAPI route handlers."""

import json
from typing import List

import asyncio
from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks

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
async def start_evaluation(req: EvaluateRequest, background_tasks: BackgroundTasks):
    task_id = req.task_id

    if task_id:
        state = task_manager.get_state(task_id)
        if state is None:
            raise HTTPException(status_code=404, detail="Task not found")
        state["rag_base_url"] = req.rag_base_url
        state["rag_api_key"] = req.rag_api_key
        # Update existing DB task with RAG config
        update_task_status(task_id, state["status"])
    else:
        task_id = task_manager.start_task(req.rag_base_url, req.rag_api_key)
        create_task(req.rag_base_url, req.rag_api_key, task_id=task_id)

    async def _run():
        try:
            await run_evaluation_pipeline(task_id)
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
