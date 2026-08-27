"""OpenAI Responses API (openai_json) adapter tests — offline via SDK client patch."""
import json
import pytest
from unittest.mock import MagicMock, patch

from app.custom_model import CustomOpenAIModel


def _make_model(**kw):
    return CustomOpenAIModel(
        model_name=kw.pop("model_name", "responses-model"),
        api_key=kw.pop("api_key", "sk-test"),
        base_url=kw.pop("base_url", "https://api.test.com"),
        api_format=kw.pop("api_format", "openai_json"),
        **kw,
    )


@pytest.fixture
def model():
    return _make_model()


def _responses_completion(text: str):
    comp = MagicMock()
    comp.output_text = text
    return comp


class TestResponsesModel:
    def test_uses_responses_endpoint(self, model):
        with patch("openai.resources.responses.responses.Responses.create", return_value=_responses_completion("Hello")) as create:
            out = model.generate("Hi")
            assert out == "Hello"
            assert create.call_args.kwargs["model"] == "responses-model"
            assert create.call_args.kwargs["input"] == "Hi"
            assert "text" not in create.call_args.kwargs  # 无 schema 不加 text.format

    def test_schema_sets_json_object(self, model):
        from pydantic import BaseModel

        class V(BaseModel):
            x: int

        with patch("openai.resources.responses.responses.Responses.create", return_value=_responses_completion('{"x": 1}')) as create:
            result = model.generate("p", schema=V)
            assert result.x == 1
            assert create.call_args.kwargs["text"] == {"format": {"type": "json_object"}}

    def test_get_model_name(self):
        assert _make_model().get_model_name() == "responses-model"
