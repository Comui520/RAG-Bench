"""Integration test: generate goldens from a real document via Synthesizer."""

import pytest


@pytest.mark.integration
class TestPipelineGoldensGeneration:
    def test_generate_goldens_from_fixture_doc(self, temp_data_dir):
        """Generate goldens from a real .txt document using actual deepeval Synthesizer."""
        import os
        from app.pipeline import build_evaluation_model, build_embedder
        from app.storage import save_uploaded_file
        from app.db import init_db, add_golden, get_goldens
        from app.task_manager import task_manager
        from app.config import CHUNK_SIZE, CHUNK_OVERLAP, MAX_GOLDENS_PER_CONTEXT
        from app.models import ModelConfig

        if not os.getenv("DEEPSEEK_API_KEY") or not os.getenv("EMBEDDING_API_KEY"):
            pytest.skip("DEEPSEEK_API_KEY / EMBEDDING_API_KEY not set")

        task_id = task_manager.start_task(
            rag_base_url="https://test.example.com",
            rag_api_key="sk-test",
        )
        # goldens 表依赖 tasks 外键，先建表
        from app.db import init_db
        init_db(":memory:")
        from app.db import create_task
        create_task("https://test.example.com", "sk-test", task_id=task_id)

        fixture_path = os.path.join(
            os.path.dirname(__file__), "fixtures", "test_doc.txt"
        )
        with open(fixture_path, "rb") as f:
            content = f.read()
        file_path = save_uploaded_file(task_id, "test_doc.txt", content)

        from deepeval.synthesizer import Synthesizer
        from deepeval.synthesizer.config import ContextConstructionConfig

        eval_cfg = ModelConfig(
            provider="deepseek", model_name="deepseek-chat",
            api_key=os.getenv("DEEPSEEK_API_KEY"),
            base_url="https://api.deepseek.com",
        )
        model = build_evaluation_model(eval_cfg)
        embed_cfg = ModelConfig(
            provider="siliconflow",
            model_name=os.getenv("EMBEDDING_MODEL", "BAAI/bge-m3"),
            api_key=os.getenv("EMBEDDING_API_KEY"),
            base_url=os.getenv("EMBEDDING_BASE_URL", "https://api.siliconflow.cn/v1"),
        )
        embedder = build_embedder(embed_cfg)

        synthesizer = Synthesizer(async_mode=False, model=model)
        context_config = ContextConstructionConfig(
            embedder=embedder,
            critic_model=model,
            chunk_size=CHUNK_SIZE,
            chunk_overlap=CHUNK_OVERLAP,
        )

        from app.storage import get_document_paths
        doc_paths = get_document_paths(task_id)

        goldens = synthesizer.generate_goldens_from_docs(
            document_paths=doc_paths,
            context_construction_config=context_config,
            max_goldens_per_context=MAX_GOLDENS_PER_CONTEXT,
        )

        assert len(goldens) > 0, "Synthesizer should produce at least 1 golden"

        import json
        for golden in goldens:
            golden_id = add_golden(
                task_id,
                golden.input,
                golden.expected_output,
                json.dumps(golden.context) if golden.context else None,
            )
            assert golden_id > 0

        saved = get_goldens(task_id)
        assert len(saved) == len(goldens)
        assert saved[0]["input"]
        assert saved[0]["expected_output"]
