"""Core deepeval evaluation pipeline."""

import asyncio
import json
import os
from typing import List, Dict, Any, Optional, Tuple

from deepeval.test_case import LLMTestCase
from deepeval.synthesizer import Synthesizer
from deepeval.synthesizer.config import ContextConstructionConfig
from deepeval.metrics import (
    ContextualRelevancyMetric,
    ContextualRecallMetric,
    ContextualPrecisionMetric,
    AnswerRelevancyMetric,
    FaithfulnessMetric,
)
from deepeval.evaluate import evaluate

from app.custom_model import CustomOpenAIModel

from app.config import (
    CHUNK_SIZE,
    CHUNK_OVERLAP,
    MAX_GOLDENS_PER_CONTEXT,
    TASK_TIMEOUT_SECONDS,
)
from app.embedder import build_embedder
from app.db import (
    create_task,
    update_task_status,
    add_golden,
    get_goldens,
    save_eval_result,
)
from app.storage import get_document_paths
from app.rag_client import RAGClient, RAGClientError
from app.task_manager import task_manager, TaskPhase


def build_evaluation_model(config):
    """Build a deepeval-compatible LLM from a ModelConfig.

    统一使用 CustomOpenAIModel，按 config.api_format 选择协议适配层：
      openai_chat → OpenAI Chat Completions（response_format=json_object 降级）
      openai_json → OpenAI Responses API（text.format.type=json_object）
      anthropic   → Anthropic Messages API（提示词 + 容错解析）
    DeepSeek 官方 API 兼容 OpenAI 协议，同样走 openai_chat。
    修复前 DeepSeek 走原生 DeepSeekModel（native 路径）、其他 provider 走
    CustomOpenAIModel（返回元组导致 Synthesizer 静默 0 条）；现在 CustomOpenAIModel
    返回单值，所有 provider 的 Synthesizer + 指标路径完全一致（#2885 适配）。
    """
    return CustomOpenAIModel(
        model_name=config.model_name,
        api_key=config.api_key,
        base_url=config.base_url,
        api_format=getattr(config, "api_format", "openai_chat"),
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
    """Extract metric scores from an evaluate() result.

    deepeval 4.0.7 的 evaluate() 返回 EvaluationResult（Pydantic 模型），
    .test_results 是 List[TestResult]（dataclass，字段 name/success/metrics_data）。
    """
    scores = {}
    all_passed = True
    test_results = getattr(result, "test_results", None) or []
    for tr in test_results:
        for md in (tr.metrics_data or []):
            scores[md.name] = md.score
            if not md.success:
                all_passed = False
    return scores, all_passed


async def run_evaluation_pipeline(task_id: str, eval_config, embed_config, rag_model: str = "deepseek-chat"):
    """Async evaluation pipeline: goldens -> confirm -> evaluate -> results."""
    state = task_manager.get_state(task_id)
    if state is None:
        return

    rag_base_url = state["rag_base_url"]
    rag_api_key = state["rag_api_key"]

    async def _push(event, data):
        await task_manager.push_event(task_id, event, data)

    try:
        # Phase 1: Generate goldens
        task_manager.update_phase(task_id, TaskPhase.GENERATING_GOLDENS, progress=0.1)
        update_task_status(task_id, "GENERATING_GOLDENS")
        await _push("progress", {"phase": "GENERATING_GOLDENS", "progress": 0.1, "message": "Initializing models..."})

        model = build_evaluation_model(eval_config)
        embedder = build_embedder(embed_config)

        doc_paths = get_document_paths(task_id)
        if not doc_paths:
            raise ValueError("No documents found for this task.")

        synthesizer = Synthesizer(async_mode=False, model=model)

        # Adaptive chunk size: scale down for short documents
        doc_total_chars = 0
        for dp in doc_paths:
            with open(dp, "r", encoding="utf-8", errors="ignore") as f:
                doc_total_chars += len(f.read())
        adaptive_chunk = max(100, min(CHUNK_SIZE, max(50, doc_total_chars // 3)))
        adaptive_overlap = max(10, min(CHUNK_OVERLAP, adaptive_chunk // 4))

        context_config = ContextConstructionConfig(
            embedder=embedder,
            critic_model=model,
            chunk_size=adaptive_chunk,
            chunk_overlap=adaptive_overlap,
        )

        task_manager.update_phase(task_id, TaskPhase.GENERATING_GOLDENS, progress=0.2)
        await _push("progress", {"phase": "GENERATING_GOLDENS", "progress": 0.2, "message": "Building context from documents..."})

        goldens = synthesizer.generate_goldens_from_docs(
            document_paths=doc_paths,
            context_construction_config=context_config,
            max_goldens_per_context=MAX_GOLDENS_PER_CONTEXT,
        )

        task_manager.update_phase(task_id, TaskPhase.GENERATING_GOLDENS, progress=0.8)
        await _push("progress", {"phase": "GENERATING_GOLDENS", "progress": 0.8, "message": f"Generated {len(goldens)} goldens"})

        if not goldens:
            raise ValueError("No goldens were generated.")

        for golden in goldens:
            context_json = json.dumps(golden.context) if golden.context else None
            add_golden(task_id, golden.input, golden.expected_output, context_json)

        # Pause for user confirmation
        task_manager.update_phase(task_id, TaskPhase.AWAITING_CONFIRM, progress=1.0)
        await _push("progress", {"phase": "AWAITING_CONFIRM", "progress": 1.0, "message": "Waiting for your confirmation..."})

        confirm_event = task_manager.set_confirmation_event(task_id)
        try:
            await asyncio.wait_for(confirm_event.wait(), timeout=TASK_TIMEOUT_SECONDS)
        except asyncio.TimeoutError:
            task_manager.mark_failed(task_id, "Timed out waiting for user confirmation.")
            update_task_status(task_id, "FAILED", error_message="Timed out waiting for user confirmation.")
            await _push("error", {"status": "FAILED", "error": "Timed out waiting for user confirmation."})
            return

        # Phase 2: Run evaluation
        task_manager.update_phase(task_id, TaskPhase.RUNNING_EVAL, progress=0.0)
        update_task_status(task_id, "RUNNING_EVAL")
        await _push("progress", {"phase": "RUNNING_EVAL", "progress": 0.0, "message": "Starting evaluation..."})

        goldens_list = get_goldens(task_id)
        total = len(goldens_list)

        rag_client = RAGClient(base_url=rag_base_url, api_key=rag_api_key)
        rag_warning_sent = False

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
            try:
                rag_response = rag_client.query(golden["input"], model=rag_model)
                actual_output = rag_response.answer
                retrieval_context = rag_response.contexts
                if rag_response.warning and not rag_warning_sent:
                    rag_warning_sent = True
                    await _push("warning", {
                        "phase": "RUNNING_EVAL",
                        "message": rag_response.warning,
                    })
            except RAGClientError as e:
                save_eval_result(
                    task_id, golden["id"],
                    actual_output=f"ERROR: {e}",
                    retrieval_context="[]",
                    metrics={m.__class__.__name__: 0.0 for m in all_metrics},
                    passed=False,
                )
                progress = (idx + 1) / total
                task_manager.update_phase(task_id, TaskPhase.RUNNING_EVAL, progress=progress)
                await _push("progress", {
                    "phase": "RUNNING_EVAL", "progress": progress,
                    "message": f"Evaluation {idx + 1}/{total}: RAG API error",
                    "current_golden": idx + 1, "total_goldens": total,
                })
                continue

            test_case = build_test_case(
                input_text=golden["input"],
                actual_output=actual_output,
                retrieval_context=retrieval_context,
                expected_output=golden["expected_output"],
            )

            await _push("progress", {
                "phase": "RUNNING_EVAL", "progress": (idx + 0.3) / total,
                "message": f"Evaluation {idx + 1}/{total}: Running metrics...",
                "current_golden": idx + 1, "total_goldens": total,
            })

            eval_result = evaluate([test_case], all_metrics)
            scores, passed = collect_metric_scores(eval_result)

            save_eval_result(
                task_id, golden["id"],
                actual_output=actual_output,
                retrieval_context=json.dumps(retrieval_context),
                metrics=scores,
                passed=passed,
            )

            progress = (idx + 1) / total
            task_manager.update_phase(task_id, TaskPhase.RUNNING_EVAL, progress=progress)
            await _push("progress", {
                "phase": "RUNNING_EVAL", "progress": progress,
                "message": f"Evaluation {idx + 1}/{total} complete",
                "current_golden": idx + 1, "total_goldens": total,
            })

        rag_client.close()

        task_manager.mark_completed(task_id)
        update_task_status(task_id, "COMPLETED")
        await _push("complete", {"status": "COMPLETED"})

    except Exception as e:
        task_manager.mark_failed(task_id, str(e))
        update_task_status(task_id, "FAILED", error_message=str(e))
        await _push("error", {"status": "FAILED", "error": str(e)})
