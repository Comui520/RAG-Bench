"""Generic custom LLM adapters for deepeval — OpenAI / Anthropic formats.

Implements DeepEvalBaseLLM so any provider API can be used as the evaluation
model in Synthesizer and metrics. All adapters return a SINGLE value
(schema instance or str) — never a tuple — which is what deepeval's
non-native model paths assume (confident-ai/deepeval#2885). Unknown pricing
returns 0.0 instead of None (confident-ai/deepeval#2884).

Supported api_format values:
  - "openai_chat"  OpenAI Chat Completions (`/chat/completions`), best-effort
                   response_format=json_object with fallbacks.
  - "openai_json"  OpenAI Responses API (`/responses`, the newer "response"
                   format). JSON output via `text.format.type="json_object"`
                   when schema is requested; plain text otherwise.
  - "anthropic"    Anthropic Messages API (`/v1/messages`). Anthropic has no
                   response_format; JSON is achieved via prompt instruction +
                   tolerant parsing (trim_and_load_json), with a second retry
                   that appends an explicit JSON instruction.
"""

import os
from typing import Any, Dict, Optional, Union

from pydantic import BaseModel
from deepeval.models import DeepEvalBaseLLM
from deepeval.models.llms.utils import trim_and_load_json

VALID_API_FORMATS = ("openai_chat", "openai_json", "anthropic")


def _resolve(api_format: str, default: str = "openai_chat") -> str:
    api_format = (api_format or default).lower().replace("-", "_")
    if api_format not in VALID_API_FORMATS:
        return default
    return api_format


def _build_headers(api_key: str, api_format: str) -> Dict[str, str]:
    if api_format == "anthropic":
        return {
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json",
        }
    return {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }


def _extract_text(data: dict, api_format: str) -> str:
    """Extract the plain text response from each API shape."""
    try:
        if api_format == "openai_chat":
            return data["choices"][0]["message"]["content"] or ""
        if api_format == "openai_json":
            # Responses API: output_text may contain plain text or JSON string
            return data.get("output_text") or ""
        if api_format == "anthropic":
            blocks = data.get("content", [])
            text = "".join(
                b.get("text", "") for b in blocks if b.get("type") == "text"
            )
            return text
    except (KeyError, IndexError, TypeError):
        pass
    raise RuntimeError(f"Unexpected API response format: {data}")


class CustomOpenAIModel(DeepEvalBaseLLM):
    """deepeval-compatible LLM backed by OpenAI-compatible / Anthropic APIs.

    generate()/a_generate() 返回单值（str 或 schema 实例），绝不返回元组。
    """

    def __init__(
        self,
        model_name: str,
        api_key: str,
        base_url: str,
        api_format: str = "openai_chat",
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
        self.api_format = _resolve(api_format)
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
        """Return the OpenAI SDK client (sync or async), lazy-created.

        OpenAI Responses API uses the same `OpenAI` client; Anthropic format
        uses plain httpx since the anthropic SDK may not be installed.
        """
        if self.api_format == "anthropic":
            import httpx

            if async_mode:
                if self._async_client is None:
                    self._async_client = httpx.AsyncClient(
                        timeout=self.timeout,
                        headers=_build_headers(self.api_key, self.api_format),
                    )
                return self._async_client
            if self._client is None:
                self._client = httpx.Client(
                    timeout=self.timeout,
                    headers=_build_headers(self.api_key, self.api_format),
                )
            return self._client

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
        """Send prompt, return single value."""
        client = self.load_model(async_mode=False)
        return self._call_api(client, prompt, schema)

    async def a_generate(self, prompt: str, schema=None) -> Union[str, BaseModel]:
        """Async version of generate."""
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

    # ── Internal ───────────────────────────────────────────

    def _call_api(self, client, prompt: str, schema=None):
        if self.api_format == "anthropic":
            return self._call_anthropic(client, prompt, schema)
        return self._call_openai(client, prompt, schema)

    async def _call_api_async(self, client, prompt: str, schema=None):
        if self.api_format == "anthropic":
            return await self._call_anthropic_async(client, prompt, schema)
        return await self._call_openai_async(client, prompt, schema)

    # ── OpenAI Chat / Responses ───────────────────────────

    def _call_openai(self, client, prompt: str, schema=None):
        from openai import BadRequestError

        def _create(use_schema: bool, retry_prompt: str = None):
            msg_prompt = retry_prompt if retry_prompt is not None else prompt
            if self.api_format == "openai_json":
                # OpenAI Responses API
                body: Dict[str, Any] = dict(
                    model=self.name,
                    input=msg_prompt,
                    **self.extra_kwargs,
                )
                if use_schema and schema is not None:
                    body["text"] = {"format": {"type": "json_object"}}
                return client.responses.create(**body)

            # openai_chat
            kwargs: Dict[str, Any] = dict(
                model=self.name,
                messages=[{"role": "user", "content": msg_prompt}],
                temperature=self.temperature,
                **self.extra_kwargs,
            )
            if use_schema and schema is not None:
                kwargs["response_format"] = {"type": "json_object"}
            return client.chat.completions.create(**kwargs)

        def _parse(completion, for_schema: bool):
            if self.api_format == "openai_json":
                content = completion.output_text or ""
            else:
                content = completion.choices[0].message.content or ""
            if not for_schema or schema is None:
                return content
            json_output = trim_and_load_json(content)
            if hasattr(schema, "model_validate"):
                return schema.model_validate(json_output)
            return json_output

        def _schema_call():
            """三层降级：json_object → 无 format → 追加 JSON 指令后缀重试。"""
            completion = None
            try:
                completion = _create(True)
            except BadRequestError:
                # 端点不支持 json_object（DeepSeek 要求 prompt 含 'json' 字样）→ 无 format
                completion = _create(False)
            try:
                return _parse(completion, True)
            except Exception:
                # 模型输出非 JSON（evolution 类 prompt 直接返回改写文本）→ 追加 JSON 后缀再试
                suffix = '\nOutput the result as a JSON object with a single key "response".'
                return _parse(_create(False, prompt + suffix), True)

        try:
            if schema is not None:
                return _schema_call()
            return _parse(_create(False), False)
        except Exception:
            raise

    async def _call_openai_async(self, client, prompt: str, schema=None):
        from openai import BadRequestError

        async def _create(use_schema: bool, retry_prompt: str = None):
            msg_prompt = retry_prompt if retry_prompt is not None else prompt
            if self.api_format == "openai_json":
                body: Dict[str, Any] = dict(
                    model=self.name,
                    input=msg_prompt,
                    **self.extra_kwargs,
                )
                if use_schema and schema is not None:
                    body["text"] = {"format": {"type": "json_object"}}
                return await client.responses.create(**body)

            kwargs: Dict[str, Any] = dict(
                model=self.name,
                messages=[{"role": "user", "content": msg_prompt}],
                temperature=self.temperature,
                **self.extra_kwargs,
            )
            if use_schema and schema is not None:
                kwargs["response_format"] = {"type": "json_object"}
            return await client.chat.completions.create(**kwargs)

        async def _parse(completion, for_schema: bool):
            if self.api_format == "openai_json":
                content = completion.output_text or ""
            else:
                content = completion.choices[0].message.content or ""
            if not for_schema or schema is None:
                return content
            json_output = trim_and_load_json(content)
            if hasattr(schema, "model_validate"):
                return schema.model_validate(json_output)
            return json_output

        async def _schema_call():
            completion = None
            try:
                completion = await _create(True)
            except BadRequestError:
                completion = await _create(False)
            try:
                return await _parse(completion, True)
            except Exception:
                suffix = '\nOutput the result as a JSON object with a single key "response".'
                return await _parse(await _create(False, prompt + suffix), True)

        try:
            if schema is not None:
                return await _schema_call()
            return await _parse(await _create(False), False)
        except Exception:
            raise

    # ── Anthropic Messages ────────────────────────────────

    def _call_anthropic(self, client, prompt: str, schema=None):
        url = f"{self.base_url}/messages"

        def _do(payload):
            resp = client.post(url, json=payload)
            if resp.status_code != 200:
                raise RuntimeError(
                    f"Anthropic API returned {resp.status_code}: {resp.text[:500]}"
                )
            return _extract_text(resp.json(), "anthropic")

        try:
            if schema is not None:
                # 提示词要求 JSON + 容错解析；解析失败追加 JSON 指令再试一次
                json_prompt = prompt + (
                    '\nOutput the result as a JSON object. Return ONLY valid JSON, no other text.'
                )
                content = _do({
                    "model": self.name, "max_tokens": 2048,
                    "messages": [{"role": "user", "content": json_prompt}],
                    **self.extra_kwargs,
                })
                try:
                    json_output = trim_and_load_json(content)
                    if hasattr(schema, "model_validate"):
                        return schema.model_validate(json_output)
                    return json_output
                except Exception:
                    # 追加显式 JSON 指令再试一次
                    retry_prompt = prompt + (
                        '\nOutput the result as a JSON object with a single key "response".'
                    )
                    content = _do({
                        "model": self.name, "max_tokens": 2048,
                        "messages": [{"role": "user", "content": retry_prompt}],
                        **self.extra_kwargs,
                    })
                    json_output = trim_and_load_json(content)
                    if hasattr(schema, "model_validate"):
                        return schema.model_validate(json_output)
                    return json_output
            return _do({
                "model": self.name, "max_tokens": 2048,
                "messages": [{"role": "user", "content": prompt}],
                **self.extra_kwargs,
            })
        except Exception:
            raise

    async def _call_anthropic_async(self, client, prompt: str, schema=None):
        url = f"{self.base_url}/messages"

        async def _do(payload):
            resp = await client.post(url, json=payload)
            if resp.status_code != 200:
                raise RuntimeError(
                    f"Anthropic API returned {resp.status_code}: {resp.text[:500]}"
                )
            return _extract_text(resp.json(), "anthropic")

        try:
            if schema is not None:
                json_prompt = prompt + (
                    '\nOutput the result as a JSON object. Return ONLY valid JSON, no other text.'
                )
                content = await _do({
                    "model": self.name, "max_tokens": 2048,
                    "messages": [{"role": "user", "content": json_prompt}],
                    **self.extra_kwargs,
                })
                try:
                    json_output = trim_and_load_json(content)
                    if hasattr(schema, "model_validate"):
                        return schema.model_validate(json_output)
                    return json_output
                except Exception:
                    retry_prompt = prompt + (
                        '\nOutput the result as a JSON object with a single key "response".'
                    )
                    content = await _do({
                        "model": self.name, "max_tokens": 2048,
                        "messages": [{"role": "user", "content": retry_prompt}],
                        **self.extra_kwargs,
                    })
                    json_output = trim_and_load_json(content)
                    if hasattr(schema, "model_validate"):
                        return schema.model_validate(json_output)
                    return json_output
            return await _do({
                "model": self.name, "max_tokens": 2048,
                "messages": [{"role": "user", "content": prompt}],
                **self.extra_kwargs,
            })
        except Exception:
            raise

    # ── Connection test（供前端"测试连接"使用）──────────────

    def test_connection(self, timeout: float = 15.0) -> Dict[str, Any]:
        """探测端点连通性：优先 /models，失败则最小 chat 请求。"""
        import httpx

        host = self.base_url or "https://api.openai.com/v1"
        probe_urls = []
        if self.api_format == "anthropic":
            probe_urls = [f"{host}/models", f"{host}/messages"]
        elif self.api_format == "openai_json":
            probe_urls = [f"{host}/models", f"{host}/responses"]
        else:
            probe_urls = [f"{host}/models", f"{host}/chat/completions"]
        headers = _build_headers(self.api_key or "", self.api_format)
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
