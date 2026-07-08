"""Integration test: run full evaluation pipeline with mock RAG API."""

import json
import pytest


class TestPipelineEvaluate:
    def test_evaluate_with_mock_rag(self, temp_data_dir):
        """Run evaluation with mock RAG responses."""
        import os
        if not os.getenv("DEEPSEEK_API_KEY"):
            pytest.skip("DEEPSEEK_API_KEY not set")

        from app.pipeline import build_evaluation_model, build_test_case, collect_metric_scores
        from app.db import init_db, add_golden, save_eval_result, get_eval_results

        from deepeval.metrics import (
            AnswerRelevancyMetric,
            FaithfulnessMetric,
        )

        task_id = "integration-test-001"
        init_db(":memory:")

        gid1 = add_golden(
            task_id, "What is WidgetX?", "WidgetX is a task management app.", '["chunk1"]'
        )

        model = build_evaluation_model()
        metrics = [
            AnswerRelevancyMetric(model=model),
            FaithfulnessMetric(model=model),
        ]

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

        save_eval_result(
            task_id, gid1,
            actual_output="WidgetX is a task management application.",
            retrieval_context=json.dumps(["WidgetX is a revolutionary task management application."]),
            metrics=scores,
            passed=passed,
        )

        db_results = get_eval_results(task_id)
        assert len(db_results) == 1
