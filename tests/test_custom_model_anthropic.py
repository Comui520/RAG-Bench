"""Anthropic Messages API (anthropic) adapter tests — offline via httpx client patch."""
import json
import pytest
from unittest.mock import MagicMock, patch

from app.custom_model import CustomOpenAIModel


def _make_model(**kw):
    return CustomOpenAIModel(
        model_name=kw.pop("model_name", "claude-model"),
        api_key=kw.pop("api_key", "sk-ant-test"),
        base_url=kw.pop("base_url", "https://api.anthropic.com/v1"),
        api_format=kw.pop("api_format", "anthropic"),
        **kw,
    )


@pytest.fixture
def model():
    return _make_model()


def _fake_response(text: str, status: int = 200):
    resp = MagicMock()
    resp.status_code = status
    resp.text = "err"
    resp.json.return_value = {
        "content": [{"type": "text", "text": text}],
        "model": "claude-model",
        "stop_reason": "end_turn",
    }
    return resp


class TestAnthropicModel:
    def test_uses_httpx_client_and_messages_url(self, model):
        resp = _fake_response("Hello from Claude")
        with patch.object(model.load_model(), "post", return_value=resp) as post:
            out = model.generate("Hi")
            assert out == "Hello from Claude"
            url = post.call_args.args[0]
            assert url.endswith("/messages")
            body = post.call_args.kwargs["json"]
            assert body["model"] == "claude-model"
            assert body["messages"] == [{"role": "user", "content": "Hi"}]
            assert body["max_tokens"] == 2048

    def test_uses_x_api_key_header(self, model):
        import httpx
        cl = model.load_model()
        assert isinstance(cl, httpx.Client)
        assert cl.headers["x-api-key"] == "sk-ant-test"
        assert cl.headers["anthropic-version"] == "2023-06-01"

    def test_schema_uses_prompt_json_and_parses(self, model):
        from pydantic import BaseModel

        class V(BaseModel):
            x: int

        resp = _fake_response('{"x": 42}')
        with patch.object(model.load_model(), "post", return_value=resp) as post:
            result = model.generate("p", schema=V)
            assert result.x == 42
            body = post.call_args.kwargs["json"]
            assert "JSON" in body["messages"][0]["content"]

    def test_schema_plain_text_fallback_retries_with_json_suffix(self, model):
        """模型先返回非 JSON 纯文本，追加 JSON 指令重试后成功。"""
        from pydantic import BaseModel

        class V(BaseModel):
            x: int

        first = _fake_response("Here is some plain text without JSON.")
        second = _fake_response('{"x": 7}')
        with patch.object(model.load_model(), "post", side_effect=[first, second]) as post:
            result = model.generate("p", schema=V)
            assert result.x == 7
            assert post.call_count == 2
            second_body = post.call_args_list[1].kwargs["json"]
            assert 'single key "response"' in second_body["messages"][0]["content"]

    def test_non_200_raises(self, model):
        resp = _fake_response("bad request", status=400)
        with patch.object(model.load_model(), "post", return_value=resp):
            with pytest.raises(RuntimeError):
                model.generate("Hi")

    def test_get_model_name(self):
        assert _make_model().get_model_name() == "claude-model"
