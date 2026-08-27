"""离线验证：CustomOpenAIModel（单值契约）与真实 deepeval Synthesizer + 5 个 RAG 指标。

覆盖 deepeval#2885 现场：修复前 CustomOpenAIModel 返回元组导致 Synthesizer
静默产出 0 条 golden；修复后单值返回，Synthesizer 与全部指标的非 native 路径
均可工作。全程 mock httpx（chat 层），embedder 用内存假实现，不访问网络。
"""

import asyncio
import json
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.custom_model import CustomOpenAIModel  # noqa: E402

# 超集 payload：覆盖 Synthesizer（ContextScore/SyntheticDataList/InputFeedback/
# RewrittenInput/Response）与 5 个指标（Verdicts/Statements/Truths/Claims/
# *ScoreReason）的全部必填字段。
_SUPERSET = {
    "clarity": 0.8,
    "depth": 0.7,
    "structure": 0.9,
    "relevance": 0.6,
    "data": [{"input": "What is retrieval augmented generation?"}],
    "input": "What is retrieval augmented generation?",
    "score": 0.9,
    "feedback": "good synthetic input",
    "rewritten_input": "Explain RAG with a concrete example.",
    "response": "RAG combines retrieval with generation to ground answers in documents.",
    "verdicts": [
        {"verdict": "yes", "reason": "statement is supported", "statement": "RAG is a technique."}
    ],
    "reason": "metric score reason",
    "statements": ["RAG combines retrieval and generation."],
    "truths": ["RAG combines retrieval and generation."],
    "claims": ["RAG combines retrieval and generation."],
}

_EMBED_VEC = [0.01 * i for i in range(1, 9)]


def _make_model():
    return CustomOpenAIModel(
        model_name="mock-llm",
        api_key="k",
        base_url="http://127.0.0.1:9999/v1",
    )


@pytest.fixture
def mock_chat():
    """mock openai SDK chat 层：sync + async 均返回超集 payload。"""
    def _fake_response():
        comp = MagicMock()
        comp.choices[0].message.content = json.dumps(_SUPERSET, ensure_ascii=False)
        return comp

    with patch("openai.resources.chat.completions.completions.Completions.create", return_value=_fake_response()) as sync_post, \
         patch("openai.resources.chat.completions.completions.AsyncCompletions.create", new_callable=AsyncMock, return_value=_fake_response()) as async_post:
        yield sync_post, async_post


# ── 1. Synthesizer 私有路径（#2885 现场）────────────────────

def test_synthesizer_generate_schema_path(mock_chat):
    from deepeval.synthesizer import Synthesizer
    from deepeval.synthesizer.schema import SyntheticDataList

    model = _make_model()
    syn = Synthesizer(model=model, async_mode=False)
    res = syn._generate_schema("make inputs", SyntheticDataList, model)
    assert isinstance(res, SyntheticDataList)
    assert res.data and res.data[0].input


def test_synthesizer_generate_returns_str(mock_chat):
    from deepeval.synthesizer import Synthesizer

    model = _make_model()
    syn = Synthesizer(model=model, async_mode=False)
    out = syn._generate("evolve this input")
    assert isinstance(out, str) and "RAG" in out


def test_context_generator_evaluate_chunk(mock_chat):
    from deepeval.synthesizer.chunking.context_generator import ContextGenerator
    from app.custom_model import CustomOpenAIModel
    from deepeval.models import DeepEvalBaseEmbeddingModel
    from typing import List

    class FakeEmbedder(DeepEvalBaseEmbeddingModel):
        def load_model(self): return None
        def embed_text(self, text): return _EMBED_VEC
        def embed_texts(self, texts): return [_EMBED_VEC] * len(texts)
        async def a_embed_text(self, text): return _EMBED_VEC
        async def a_embed_texts(self, texts): return [_EMBED_VEC] * len(texts)
        def get_model_name(self): return "fake-embedder"

    model = _make_model()
    cg = ContextGenerator(
        embedder=FakeEmbedder(model="fake"),
        document_paths=["dummy.txt"],
        model=model,
    )
    assert cg.using_native_model is False
    score = cg.evaluate_chunk("some chunk text")
    assert score == pytest.approx((0.8 + 0.7 + 0.9 + 0.6) / 4)


# ── 2. 完整 Synthesizer 管线（修复前静默 0 条）────────────────

def test_full_generate_goldens_from_docs(mock_chat, tmp_path):
    from deepeval.synthesizer import Synthesizer
    from deepeval.synthesizer.config import ContextConstructionConfig
    from deepeval.models import DeepEvalBaseEmbeddingModel
    from typing import List

    class FakeEmbedder(DeepEvalBaseEmbeddingModel):
        def load_model(self): return None
        def embed_text(self, text): return _EMBED_VEC
        def embed_texts(self, texts): return [_EMBED_VEC] * len(texts)
        async def a_embed_text(self, text): return _EMBED_VEC
        async def a_embed_texts(self, texts): return [_EMBED_VEC] * len(texts)
        def get_model_name(self): return "fake-embedder"

    doc = tmp_path / "rag_doc.txt"
    para = "Retrieval augmented generation combines a retriever with a generator. " * 600
    doc.write_text(para, encoding="utf-8")

    model = _make_model()
    syn = Synthesizer(model=model, async_mode=False)
    cfg = ContextConstructionConfig(
        embedder=FakeEmbedder(model="fake"),
        critic_model=model,
    )
    goldens = syn.generate_goldens_from_docs(
        document_paths=[str(doc)],
        context_construction_config=cfg,
        max_goldens_per_context=1,
        include_expected_output=True,
    )
    assert len(goldens) > 0, "Synthesizer 应产出 goldens（修复前此处静默返回空）"
    assert goldens[0].input


# ── 3. 5 个 RAG 指标离线跑通 ───────────────────────────────

def test_all_five_rag_metrics_offline(mock_chat):
    from deepeval.test_case import LLMTestCase
    from deepeval.metrics import (
        ContextualRelevancyMetric,
        ContextualRecallMetric,
        ContextualPrecisionMetric,
        AnswerRelevancyMetric,
        FaithfulnessMetric,
    )

    model = _make_model()
    tc = LLMTestCase(
        input="What is RAG?",
        actual_output="RAG combines retrieval with generation.",
        expected_output="RAG is retrieval augmented generation.",
        retrieval_context=["RAG combines retrieval and generation."],
    )

    metrics = [
        ContextualRelevancyMetric(model=model),
        ContextualRecallMetric(model=model),
        ContextualPrecisionMetric(model=model),
        AnswerRelevancyMetric(model=model),
        FaithfulnessMetric(model=model),
    ]
    for m in metrics:
        assert m.using_native_model is False, type(m).__name__
        m.measure(tc)
        assert m.score is not None, type(m).__name__
        assert 0.0 <= m.score <= 1.0, (type(m).__name__, m.score)
        print(f"  {type(m).__name__}: score={m.score}")


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v", "-s"]))
