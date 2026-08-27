"""Generic OpenAI-compatible custom model for deepeval.

Implements DeepEvalBaseLLM so any OpenAI-compatible API
(OpenAI, DeepSeek, SiliconFlow, vLLM, Ollama, etc.) can be used
as the evaluation model in Synthesizer and metrics.

适配 deepeval 自定义模型缺陷（confident-ai/deepeval#2884 / #2885）：
  - generate()/a_generate() 返回【单值】（有 schema 返回 schema 实例，否则返回 str），
    与 deepeval 对非 native 模型的全部调用点（Synthesizer 的 _generate_schema /
    _generate / ContextGenerator.evaluate_chunk，以及各指标的
    generate_with_schema_and_extract）兼容。修复前返回 (content, cost) 元组，
    导致非 DeepSeek provider 的 Synthesizer 静默产出 0 条 golden。
  - JSON 解析容错：模型输出带 markdown 围栏 / 尾逗号时仍可解析（trim_and_load_json）。
  - 端点不支持 response_format（400/422 BadRequestError）时自动降级重试一次。
  - calculate_cost() 未知定价返回 0.0 而非 None（#2884 的 total_cost += None 根因）。
"""

import os
from typing import Any, Dict, Optional, Union

from pydantic import BaseModel
from deepeval.models import DeepEvalBaseLLM
from deepeval.models.llms.utils import trim_and_load_json


class CustomOpenAIModel(DeepEvalBaseLLM):
    """A deepeval-compatible LLM backed by any OpenAI-compatible API.

    generate()/a_generate() 返回单值（str 或 schema 实例），绝不返回元组。
    """

    def __init__(
        self,
        model_name: str,
        api_key: str,
        base_url: str,
        temperature: float = 0.0,
        timeout: float = 120.0,
        max_retries: int = 3,
        cost_per_input_token: Optional[float] = None,
        cost_per_output_token: Optional[float] = None,
        **kwargs,
    ):
        self.name = model_name
        self.api_key = api_key
        self.base_url = (base_url or "").rstrip("/")
        self.temperature = temperature
        self.timeout = timeout
        self.max_retries = max_retries
        self.cost_per_input_token = cost_per_input_token
        self.cost_per_output_token = cost_per_output_token
        self.extra_kwargs = kwargs
        self._client = None
        self._async_client = None
        super().__init__(model=model_name)

    # ── DeepEvalBaseLLM interface ──

    def get_model_name(self) -> str:
        return self.name

    def load_model(self, async_mode: bool = False):
        """Return the OpenAI SDK client (sync or async), lazy-created."""
        from openai import AsyncOpenAI, OpenAI

        cls = AsyncOpenAI if async_mode else OpenAI

        if async_mode:
            if self._async_client is None:
                self._async_client = cls(
                    api_key=self.api_key,
                    base_url=self.base_url,
                    timeout=self.timeout,
                    max_retries=self.max_retries,
                )
            return self._async_client
        else:
            if self._client is None:
                self._client = cls(
                    api_key=self.api_key,
                    base_url=self.base_url,
                    timeout=self.timeout,
                    max_retries=self.max_retries,
                )
            return self._client

    def generate(self, prompt: str, schema=None) -> Union[str, BaseModel]:
        """Send prompt to the OpenAI-compatible API, return single value.

        schema 非 None 时：优先 response_format=json_object；若端点拒绝（400/422，
        常见于 DeepSeek：prompt 未含 'json' 字样）则降级为普通生成，再做容错 JSON
        解析；解析失败/字段缺失时再降级一次为「追加 JSON 指令后缀」的生成，保证
        Synthesizer._generate 这类既要求 JSON 又要求单字符串的场景可用。
        """
        client = self.load_model(async_mode=False)
        return self._call_api(client, prompt, schema)

    async def a_generate(self, prompt: str, schema=None) -> Union[str, BaseModel]:
        """Async version of generate（同样含 JSON 降级逻辑）。"""
        client = self.load_model(async_mode=True)
        return await self._call_api_async(client, prompt, schema)

    # ── Capabilities（供 deepeval 查询，避免降级路径）──

    def supports_json_mode(self) -> Union[bool, None]:
        return True

    def supports_structured_outputs(self) -> Union[bool, None]:
        return False

    def supports_temperature(self) -> Union[bool, None]:
        return True

    # ── Cost（#2884 关键：永远不返回 None）────────────────

    def calculate_cost(self, input_tokens: int, output_tokens: int) -> float:
        if (
            self.cost_per_input_token is not None
            and self.cost_per_output_token is not None
        ):
            return (
                input_tokens * self.cost_per_input_token
                + output_tokens * self.cost_per_output_token
            )
        return 0.0

    # ── Internal ──

    def _call_api(self, client, prompt: str, schema=None):
        from openai import BadRequestError

        messages = [{"role": "user", "content": prompt}]
        kwargs: Dict[str, Any] = dict(
            model=self.name,
            messages=messages,
            temperature=self.temperature,
            **self.extra_kwargs,
        )
        try:
            if schema is not None:
                try:
                    completion = client.chat.completions.create(
                        **kwargs, response_format={"type": "json_object"}
                    )
                except BadRequestError:
                    # 端点不支持 json_object（或 prompt 未含 'json' 字样）→ 降级为无 response_format
                    completion = client.chat.completions.create(**kwargs)
                content = completion.choices[0].message.content or ""
                try:
                    json_output = trim_and_load_json(content)
                    if hasattr(schema, "model_validate"):
                        return schema.model_validate(json_output)
                    return json_output
                except Exception:
                    # 模型输出了非 JSON（如 evolution 类 prompt 直接返回改写文本）→
                    # 追加 JSON 指令后缀再试一次，仍失败才抛出
                    retry_kwargs = dict(kwargs)
                    retry_kwargs["messages"] = [
                        {"role": "user", "content": prompt + '\nOutput the result as a JSON object with a single key "response".'}
                    ]
                    completion = client.chat.completions.create(**retry_kwargs)
                    content = completion.choices[0].message.content or ""
                    json_output = trim_and_load_json(content)
                    if hasattr(schema, "model_validate"):
                        return schema.model_validate(json_output)
                    return json_output
            completion = client.chat.completions.create(**kwargs)
            return completion.choices[0].message.content or ""
        except Exception:
            raise

    async def _call_api_async(self, client, prompt: str, schema=None):
        from openai import BadRequestError

        messages = [{"role": "user", "content": prompt}]
        kwargs: Dict[str, Any] = dict(
            model=self.name,
            messages=messages,
            temperature=self.temperature,
            **self.extra_kwargs,
        )
        try:
            if schema is not None:
                try:
                    completion = await client.chat.completions.create(
                        **kwargs, response_format={"type": "json_object"}
                    )
                except BadRequestError:
                    completion = await client.chat.completions.create(**kwargs)
                content = completion.choices[0].message.content or ""
                try:
                    json_output = trim_and_load_json(content)
                    if hasattr(schema, "model_validate"):
                        return schema.model_validate(json_output)
                    return json_output
                except Exception:
                    # 同同步版：追加 JSON 指令后缀再试一次
                    retry_kwargs = dict(kwargs)
                    retry_kwargs["messages"] = [
                        {"role": "user", "content": prompt + '\nOutput the result as a JSON object with a single key "response".'}
                    ]
                    completion = await client.chat.completions.create(**retry_kwargs)
                    content = completion.choices[0].message.content or ""
                    json_output = trim_and_load_json(content)
                    if hasattr(schema, "model_validate"):
                        return schema.model_validate(json_output)
                    return json_output
            completion = await client.chat.completions.create(**kwargs)
            return completion.choices[0].message.content or ""
        except Exception:
            raise

    # ── Connection test（供前端"测试连接"使用）──────────────

    def test_connection(self, timeout: float = 15.0) -> Dict[str, Any]:
        """探测端点连通性：优先 /models，失败则最小 chat 请求。"""
        import httpx

        host = self.base_url or "https://api.openai.com/v1"
        probe_urls = [f"{host}/models", f"{host}/chat/completions"]
        headers = {}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        last_error: Optional[str] = None
        for url in probe_urls:
            try:
                r = httpx.get(
                    url,
                    headers=headers,
                    timeout=timeout,
                    params={"limit": 1} if url.endswith("/models") else None,
                )
                if r.status_code < 400:
                    return {
                        "ok": True,
                        "status_code": r.status_code,
                        "endpoint": url,
                        "message": f"连通正常（HTTP {r.status_code}）",
                    }
                if r.status_code in (401, 403):
                    return {
                        "ok": True,
                        "status_code": r.status_code,
                        "endpoint": url,
                        "message": f"端点可达，但鉴权失败（HTTP {r.status_code}）",
                    }
                last_error = f"HTTP {r.status_code}: {r.text[:200]}"
            except Exception as e:
                last_error = f"{type(e).__name__}: {e}"
        return {"ok": False, "endpoint": host, "message": last_error}

    # ── Cleanup ──

    def close(self):
        if self._client:
            try:
                self._client.close()
            except Exception:
                pass
            self._client = None
        self._async_client = None

    def __del__(self):
        try:
            self.close()
        except Exception:
            pass
