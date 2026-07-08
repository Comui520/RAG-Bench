"""Core deepeval evaluation pipeline."""

import asyncio
import json
import os
from typing import List, Dict, Any, Optional, Tuple

from deepeval.models import DeepSeekModel
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
    RAG_MODEL_NAME,
)
from app.embedder import SiliconFlowEmbeddingModel
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


def build_evaluation_model():
    """Build a DeepSeekModel for evaluation. Takes API key from env/config."""
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
    """Async evaluation pipeline: goldens -> confirm -> evaluate -> results."""
    state = task_manager.get_state(task_id)
    if state is None:
        return

    rag_base_url = state["rag_base_url"]
    rag_api_key = state["rag_api_key"]

    try:
        # Phase 1: Generate goldens
        task_manager.update_phase(task_id, TaskPhase.GENERATING_GOLDENS, progress=0.1)
        update_task_status(task_id, "GENERATING_GOLDENS")

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

        # Pause for user confirmation
        task_manager.update_phase(task_id, TaskPhase.AWAITING_CONFIRM, progress=1.0)

        confirm_event = task_manager.set_confirmation_event(task_id)
        try:
            await asyncio.wait_for(confirm_event.wait(), timeout=TASK_TIMEOUT_SECONDS)
        except asyncio.TimeoutError:
            task_manager.mark_failed(task_id, "Timed out waiting for user confirmation.")
            update_task_status(task_id, "FAILED", error_message="Timed out waiting for user confirmation.")
            return

        # Phase 2: Run evaluation
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
            try:
                rag_response = rag_client.query(golden["input"], model=RAG_MODEL_NAME)
                actual_output = rag_response.answer
                retrieval_context = rag_response.contexts
            except RAGClientError as e:
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

        task_manager.mark_completed(task_id)
        update_task_status(task_id, "COMPLETED")

    except Exception as e:
        task_manager.mark_failed(task_id, str(e))
        update_task_status(task_id, "FAILED", error_message=str(e))
