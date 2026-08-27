"""End-to-end smoke: 真实 DeepSeek LLM + SiliconFlow 嵌入，验证 deepeval 5 指标。"""
import os
import sys

sys.path.insert(0, "D:/rag-llm-test")

from app.pipeline import build_evaluation_model, build_test_case, collect_metric_scores
from app.models import ModelConfig
from deepeval.test_case import LLMTestCase
from deepeval.metrics import (
    ContextualRelevancyMetric,
    ContextualRecallMetric,
    ContextualPrecisionMetric,
    AnswerRelevancyMetric,
    FaithfulnessMetric,
)

eval_cfg = ModelConfig(
    provider="deepseek",
    model_name="deepseek-chat",
    api_key=os.environ["DEEPSEEK_API_KEY"],
    base_url="https://api.deepseek.com",
)
model = build_evaluation_model(eval_cfg)

tc = build_test_case(
    input_text="What is WidgetX?",
    actual_output="WidgetX is a task management application.",
    retrieval_context=["WidgetX is a revolutionary task management application."],
    expected_output="WidgetX is a task management app.",
)

metrics = [
    ContextualRelevancyMetric(model=model),
    ContextualRecallMetric(model=model),
    ContextualPrecisionMetric(model=model),
    AnswerRelevancyMetric(model=model),
    FaithfulnessMetric(model=model),
]

from deepeval.evaluate import evaluate
result = evaluate([tc], metrics)
scores, passed = collect_metric_scores(result)
print("scores:", scores)
print("passed:", passed)
for k, v in scores.items():
    assert 0.0 <= v <= 1.0, (k, v)
print("SMOKE OK")
model.close()
