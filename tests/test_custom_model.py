"""Rewrite tests for CustomOpenAIModel — OpenAI SDK client + 单值契约。"""
import pytest
from unittest.mock import patch, MagicMock
import httpx


def _make_model(**kw):
    from app.custom_model import CustomOpenAIModel
    return CustomOpenAIModel(
        model_name=kw.pop("model_name", "test-model"),
        api_key=kw.pop("api_key", "sk-test"),
        base_url=kw.pop("base_url", "https://api.test.com"),
        **kw,
    )


@pytest.fixture
def model():
    return _make_model()


@pytest.fixture
def chat(model):
    """patch 该 model 自身 client 的 chat.completions.create。"""
    client = model.load_model()
    with patch.object(client.chat.completions, "create") as p:
        yield p


def _completion(content: str):
    comp = MagicMock()
    comp.choices[0].message.content = content
    return comp


class TestCustomOpenAIModel:
    def test_get_model_name(self):
        assert _make_model().get_model_name() == "test-model"

    def test_load_model_returns_openai_client(self):
        import openai
        m = _make_model()
        assert isinstance(m.load_model(), openai.OpenAI)
        assert m.load_model().api_key == "sk-test"

    def test_generate_returns_single_str(self, model, chat):
        """无 schema 时返回 str（而非元组）。"""
        chat.return_value = _completion("Hello from test model")
        result = model.generate("What is 1+1?")
        assert isinstance(result, str)
        assert result == "Hello from test model"

    def test_generate_with_schema_returns_instance(self, model, chat):
        """有 schema 时返回 schema 实例（非元组、非 dict）。"""
        from pydantic import BaseModel

        class Verdict(BaseModel):
            verdict: str
            score: float

        chat.return_value = _completion('{"verdict": "pass", "score": 0.9}')
        result = model.generate("eval", schema=Verdict)
        assert isinstance(result, Verdict)
        assert result.verdict == "pass"

    def test_generate_parses_json_with_markdown_fences(self, model, chat):
        """模型输出带 markdown 围栏时仍能解析（trim_and_load_json 容错）。"""
        from pydantic import BaseModel

        class Verdict(BaseModel):
            verdict: str

        chat.return_value = _completion('```json\n{"verdict": "pass"}\n```')
        result = model.generate("eval", schema=Verdict)
        assert result.verdict == "pass"

    def test_generate_raises_on_429(self):
        """429 由 openai SDK 内部重试，连续 429 最终冒泡（不会静默返回）。"""
        from openai import RateLimitError
        m = _make_model(max_retries=3)
        err = RateLimitError("429", response=MagicMock(status_code=429), body=None)
        with patch.object(m.load_model().chat.completions, "create", side_effect=err):
            with pytest.raises(RateLimitError):
                m.generate("prompt")

    def test_generate_raises_on_non_200(self, model, chat):
        """非 2xx 且非 429/5xx → 抛异常。"""
        from openai import AuthenticationError
        err = AuthenticationError("Unauthorized", response=MagicMock(status_code=401), body=None)
        chat.side_effect = err
        with pytest.raises(Exception):
            model.generate("prompt")

    def test_generate_raises_on_timeout(self, model, chat):
        """超时 → openai APIConnectionError 冒泡。"""
        chat.side_effect = httpx.TimeoutException("timed out")
        with pytest.raises(Exception):
            model.generate("prompt")

    def test_generate_builds_correct_request_body(self, model, chat):
        """请求体含 model/messages/temperature。"""
        m = _make_model(temperature=0.5)
        cl = m.load_model()
        with patch.object(cl.chat.completions, "create", return_value=_completion("OK")) as mock_create:
            m.generate("What is life?")
            kwargs = mock_create.call_args.kwargs
            assert kwargs["model"] == "test-model"
            assert kwargs["messages"][0]["content"] == "What is life?"
            assert kwargs["temperature"] == 0.5

    def test_schema_request_includes_json_mode(self, model, chat):
        from pydantic import BaseModel

        class V(BaseModel):
            x: int

        chat.return_value = _completion('{"x": 1}')
        model.generate("p", schema=V)
        kwargs = chat.call_args.kwargs
        assert kwargs.get("response_format") == {"type": "json_object"}

    def test_schema_fallback_when_json_mode_rejected(self):
        """端点拒绝 response_format（400 BadRequestError）时降级重试一次并成功。"""
        from pydantic import BaseModel
        from openai import BadRequestError

        class V(BaseModel):
            x: int

        m = _make_model(max_retries=2)
        cl = m.load_model()
        rejected = BadRequestError(
            "response_format not supported", response=MagicMock(status_code=400), body=None
        )
        with patch.object(cl.chat.completions, "create", side_effect=[rejected, _completion('{"x": 1}')]) as mock_create:
            result = m.generate("p", schema=V)
            assert result.x == 1
            bodies = [c.kwargs for c in mock_create.call_args_list]
            assert bodies[0].get("response_format") is not None
            assert bodies[1].get("response_format") is None

    def test_schema_plain_text_fallback_retries_with_json_suffix(self):
        """模型返回非 JSON 纯文本（evolution 类 prompt 场景）→ 追加 JSON 指令后缀重试。"""
        from pydantic import BaseModel

        class Response(BaseModel):
            response: str

        m = _make_model(max_retries=2)
        cl = m.load_model()
        plain = _completion("What is the meaning of life?")
        json_ok = _completion('{"response": "42"}')
        with patch.object(cl.chat.completions, "create", side_effect=[plain, json_ok]) as mock_create:
            result = m.generate("Evolve this question", schema=Response)
            assert result.response == "42"
            assert mock_create.call_count == 2
            # 第一次：带 response_format；第二次：无 response_format + 追加 JSON 指令
            first = mock_create.call_args_list[0].kwargs
            second = mock_create.call_args_list[1].kwargs
            assert first.get("response_format") == {"type": "json_object"}
            assert "response_format" not in second
            assert 'single key "response"' in second["messages"][0]["content"]

    def test_custom_base_url_is_used(self):
        from openai import OpenAI
        m = _make_model(base_url="http://localhost:11434/v1")
        cl = m.load_model()
        assert isinstance(cl, OpenAI)
        assert cl.base_url == "http://localhost:11434/v1/"  # SDK 会补尾部斜杠

    def test_is_deepeval_base_llm_instance(self):
        from deepeval.models import DeepEvalBaseLLM
        assert isinstance(_make_model(), DeepEvalBaseLLM)
