"""Unit tests for the evaluation pipeline orchestration."""

import json
import pytest
from unittest.mock import patch, MagicMock, PropertyMock
from app.pipeline import (
    build_evaluation_model,
    build_embedder,
    build_test_case,
    collect_metric_scores,
)


class TestBuildEmbedder:
    def test_returns_siliconflow_embedder(self):
        embedder = build_embedder()
        from app.embedder import SiliconFlowEmbeddingModel
        assert isinstance(embedder, SiliconFlowEmbeddingModel)


class TestBuildTestCase:
    def test_builds_test_case_correctly(self):
        test_case = build_test_case(
            input_text="What is X?",
            actual_output="X is a thing.",
            retrieval_context=["doc about X"],
            expected_output="X is a thing.",
        )
        assert test_case.input == "What is X?"
        assert test_case.actual_output == "X is a thing."
        assert test_case.retrieval_context == ["doc about X"]
        assert test_case.expected_output == "X is a thing."


class TestCollectMetricScores:
    def test_collects_all_metric_types(self):
        fake_result = MagicMock()
        m1 = MagicMock(score=0.85, success=True)
        m1.name = "ContextualRelevancyMetric"
        m2 = MagicMock(score=0.72, success=False)
        m2.name = "ContextualRecallMetric"
        m3 = MagicMock(score=0.91, success=True)
        m3.name = "FaithfulnessMetric"
        fake_result.metrics_data = [m1, m2, m3]
        fake_result.success = False

        scores, passed = collect_metric_scores(fake_result)
        assert len(scores) == 3
        assert scores["ContextualRelevancyMetric"] == 0.85
        assert scores["FaithfulnessMetric"] == 0.91
        assert passed is False
