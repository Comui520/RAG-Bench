"""Tests for v2 pipeline with dynamic model config."""

import pytest
from unittest.mock import patch, MagicMock
from app.models import ModelConfig


class TestBuildEvaluationModelV2:
    def test_builds_with_custom_config_for_openai(self):
        from app.pipeline import build_evaluation_model
        config = ModelConfig(
            provider="openai", model_name="gpt-4o",
            api_key="sk-custom", base_url="https://api.openai.com/v1",
        )
        with patch("app.pipeline.CustomOpenAIModel") as MockModel:
            build_evaluation_model(config)
            MockModel.assert_called_once_with(
                model_name="gpt-4o",
                api_key="sk-custom",
                base_url="https://api.openai.com/v1",
            )

    def test_builds_with_deepseek_for_deepseek_provider(self):
        """DeepSeek 官方 API 同样走 CustomOpenAIModel（OpenAI 兼容协议）。

        修复前 DeepSeek 特判走原生 DeepSeekModel（native 路径），其他 provider 走
        CustomOpenAIModel（元组返回导致 Synthesizer 静默 0 条）。现在统一使用
        CustomOpenAIModel，所有 provider 行为一致（#2885 适配）。
        """
        from app.pipeline import build_evaluation_model
        config = ModelConfig(
            provider="deepseek", model_name="deepseek-chat",
            api_key="sk-ds", base_url="https://api.deepseek.com",
        )
        with patch("app.pipeline.CustomOpenAIModel") as MockModel:
            build_evaluation_model(config)
            MockModel.assert_called_once_with(
                model_name="deepseek-chat",
                api_key="sk-ds",
                base_url="https://api.deepseek.com",
            )


class TestBuildEmbedderV2:
    def test_builds_with_custom_config(self):
        from app.pipeline import build_embedder
        config = ModelConfig(
            provider="siliconflow", model_name="BAAI/bge-m3",
            api_key="sk-embed", base_url="https://api.siliconflow.cn/v1",
        )
        embedder = build_embedder(config)
        assert embedder._model_name == "BAAI/bge-m3"
        assert embedder._base_url == "https://api.siliconflow.cn/v1"


class TestPipelineProgressCallback:
    @pytest.mark.asyncio
    async def test_pushes_progress_events(self, temp_data_dir):
        from app.task_manager import task_manager
        from app.models import ModelConfig

        task_id = task_manager.start_task("http://test.com", "sk-test")
        from app.db import init_db, create_task
        init_db(":memory:")
        create_task("http://test.com", "sk-test", task_id=task_id)

        from app.pipeline import run_evaluation_pipeline

        eval_config = ModelConfig(
            provider="deepseek", model_name="deepseek-chat",
            api_key="sk-test", base_url="https://api.deepseek.com",
        )
        embed_config = ModelConfig(
            provider="siliconflow", model_name="BAAI/bge-m3",
            api_key="sk-test", base_url="https://api.siliconflow.cn/v1",
        )

        await run_evaluation_pipeline(task_id, eval_config, embed_config)

        state = task_manager.get_state(task_id)
        assert state["status"] == "FAILED"
        assert state["error_message"] is not None
