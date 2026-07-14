"""Tests for CustomOpenAIModel — no real API key required."""

import pytest
from unittest.mock import patch, MagicMock
import httpx


class TestCustomOpenAIModel:
    def test_get_model_name(self):
        from app.custom_model import CustomOpenAIModel
        model = CustomOpenAIModel(
            model_name="gpt-4o", api_key="sk-test",
            base_url="https://api.openai.com/v1",
        )
        assert model.get_model_name() == "gpt-4o"

    def test_load_model_returns_httpx_client(self):
        from app.custom_model import CustomOpenAIModel
        model = CustomOpenAIModel(
            model_name="test-model", api_key="sk-test",
            base_url="https://api.test.com",
        )
        client = model.load_model()
        assert isinstance(client, httpx.Client)
        assert client.headers["Authorization"] == "Bearer sk-test"

    def test_generate_parses_openai_response(self):
        from app.custom_model import CustomOpenAIModel
        model = CustomOpenAIModel(
            model_name="test-model", api_key="sk-test",
            base_url="https://api.test.com",
        )
        fake_response = MagicMock()
        fake_response.status_code = 200
        fake_response.json.return_value = {
            "choices": [{"message": {"content": "Hello from test model"}}],
        }
        with patch.object(httpx.Client, "post", return_value=fake_response):
            result, cost = model.generate("What is 1+1?")
            assert result == "Hello from test model"

    def test_generate_retries_on_429(self):
        from app.custom_model import CustomOpenAIModel
        model = CustomOpenAIModel(
            model_name="test-model", api_key="sk-test",
            base_url="https://api.test.com",
            max_retries=3,
        )
        fail = MagicMock()
        fail.status_code = 429
        success = MagicMock()
        success.status_code = 200
        success.json.return_value = {
            "choices": [{"message": {"content": "Success after retry"}}],
        }
        with patch.object(httpx.Client, "post", side_effect=[fail, fail, success]) as mock_post:
            result, cost = model.generate("prompt")
            assert result == "Success after retry"
            assert mock_post.call_count == 3

    def test_generate_raises_on_non_200(self):
        from app.custom_model import CustomOpenAIModel
        model = CustomOpenAIModel(
            model_name="test-model", api_key="sk-test",
            base_url="https://api.test.com",
        )
        fake = MagicMock()
        fake.status_code = 401
        fake.text = "Unauthorized"
        with patch.object(httpx.Client, "post", return_value=fake):
            with pytest.raises(RuntimeError, match="401"):
                model.generate("prompt")

    def test_generate_raises_on_timeout(self):
        from app.custom_model import CustomOpenAIModel
        model = CustomOpenAIModel(
            model_name="test-model", api_key="sk-test",
            base_url="https://api.test.com",
            max_retries=1,
        )
        with patch.object(httpx.Client, "post", side_effect=httpx.TimeoutException("timed out")):
            with pytest.raises(RuntimeError, match="timed out"):
                model.generate("prompt")

    def test_generate_builds_correct_request_body(self):
        from app.custom_model import CustomOpenAIModel
        model = CustomOpenAIModel(
            model_name="test-model", api_key="sk-test",
            base_url="https://api.test.com",
            temperature=0.5,
        )
        fake = MagicMock()
        fake.status_code = 200
        fake.json.return_value = {
            "choices": [{"message": {"content": "OK"}}],
        }
        with patch.object(httpx.Client, "post", return_value=fake) as mock_post:
            model.generate("What is life?")
            args, kwargs = mock_post.call_args
            body = kwargs.get("json") or args[1]
            assert body["model"] == "test-model"
            assert body["messages"][0]["content"] == "What is life?"
            assert body["temperature"] == 0.5
            url = kwargs.get("url") or args[0]
            assert url.endswith("/chat/completions")

    def test_custom_base_url_is_used(self):
        from app.custom_model import CustomOpenAIModel
        model = CustomOpenAIModel(
            model_name="llama3", api_key="sk-test",
            base_url="http://localhost:11434/v1",
        )
        fake = MagicMock()
        fake.status_code = 200
        fake.json.return_value = {
            "choices": [{"message": {"content": "OK"}}],
        }
        with patch.object(httpx.Client, "post", return_value=fake) as mock_post:
            model.generate("hi")
            called_url = mock_post.call_args[0][0]
            assert called_url == "http://localhost:11434/v1/chat/completions"

    def test_is_deepeval_base_llm_instance(self):
        from app.custom_model import CustomOpenAIModel
        from deepeval.models import DeepEvalBaseLLM
        model = CustomOpenAIModel(
            model_name="test", api_key="k", base_url="http://x.com",
        )
        assert isinstance(model, DeepEvalBaseLLM)
