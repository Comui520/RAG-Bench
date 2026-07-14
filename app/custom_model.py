"""Generic OpenAI-compatible custom model for deepeval.

Implements DeepEvalBaseLLM so any OpenAI-compatible API
(OpenAI, DeepSeek, SiliconFlow, vLLM, Ollama, etc.) can be used
as the evaluation model in Synthesizer and metrics.
"""

from typing import Optional, Tuple, Any

import httpx
from deepeval.models import DeepEvalBaseLLM


class CustomOpenAIModel(DeepEvalBaseLLM):
    """A deepeval-compatible LLM backed by any OpenAI-compatible API."""

    def __init__(
        self,
        model_name: str,
        api_key: str,
        base_url: str,
        temperature: float = 0.0,
        timeout: float = 120.0,
        max_retries: int = 3,
        **kwargs,
    ):
        self.model_name = model_name
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.temperature = temperature
        self.timeout = timeout
        self.max_retries = max_retries
        self.extra_kwargs = kwargs
        self._client: Optional[httpx.Client] = None
        self._async_client: Optional[httpx.AsyncClient] = None
        super().__init__()

    # ── DeepEvalBaseLLM interface ──

    def get_model_name(self) -> str:
        return self.model_name

    def load_model(self, async_mode: bool = False):
        """Return the HTTP client (sync or async)."""
        if async_mode:
            if self._async_client is None:
                self._async_client = httpx.AsyncClient(
                    timeout=self.timeout,
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                    },
                )
            return self._async_client
        else:
            if self._client is None:
                self._client = httpx.Client(
                    timeout=self.timeout,
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                    },
                )
            return self._client

    def generate(self, prompt: str, schema=None) -> Tuple[str, float]:
        """Send prompt to the OpenAI-compatible API, return (response, cost)."""
        return self._generate(prompt, schema)

    async def a_generate(self, prompt: str, schema=None) -> Tuple[str, float]:
        """Async version of generate."""
        return await self._a_generate(prompt, schema)

    # ── Internal ──

    def _generate(self, prompt: str, schema=None) -> Tuple[str, float]:
        client = self.load_model(async_mode=False)
        return self._call_api(client, prompt, schema)

    async def _a_generate(self, prompt: str, schema=None) -> Tuple[str, float]:
        client = self.load_model(async_mode=True)
        return await self._call_api_async(client, prompt, schema)

    def _call_api(self, client: httpx.Client, prompt: str, schema=None) -> Tuple[str, float]:
        body = self._build_body(prompt, schema)
        url = f"{self.base_url}/chat/completions"

        for attempt in range(self.max_retries):
            try:
                resp = client.post(url, json=body)
                if resp.status_code == 200:
                    data = resp.json()
                    return self._parse_response(data)
                elif resp.status_code in (429, 500, 502, 503):
                    import time
                    time.sleep(2 ** attempt)
                    continue
                else:
                    raise RuntimeError(
                        f"API returned {resp.status_code}: {resp.text[:500]}"
                    )
            except httpx.TimeoutException:
                if attempt == self.max_retries - 1:
                    raise RuntimeError("API request timed out after retries")
                import time
                time.sleep(2 ** attempt)

        raise RuntimeError("API request failed after all retries")

    async def _call_api_async(self, client: httpx.AsyncClient, prompt: str, schema=None) -> Tuple[str, float]:
        body = self._build_body(prompt, schema)
        url = f"{self.base_url}/chat/completions"

        for attempt in range(self.max_retries):
            try:
                resp = await client.post(url, json=body)
                if resp.status_code == 200:
                    data = resp.json()
                    return self._parse_response(data)
                elif resp.status_code in (429, 500, 502, 503):
                    import asyncio
                    await asyncio.sleep(2 ** attempt)
                    continue
                else:
                    raise RuntimeError(
                        f"API returned {resp.status_code}: {resp.text[:500]}"
                    )
            except httpx.TimeoutException:
                if attempt == self.max_retries - 1:
                    raise RuntimeError("API request timed out after retries")
                import asyncio
                await asyncio.sleep(2 ** attempt)

        raise RuntimeError("API request failed after all retries")

    def _build_body(self, prompt: str, schema=None) -> dict:
        body: dict = {
            "model": self.model_name,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": self.temperature,
        }
        if schema is not None:
            body["response_format"] = {"type": "json_object"}
        return body

    def _parse_response(self, data: dict) -> Tuple[str, float]:
        try:
            content = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError):
            raise RuntimeError(f"Unexpected API response format: {data}")
        return str(content), 0.0

    # ── Cleanup ──

    def close(self):
        if self._client:
            self._client.close()
            self._client = None
        if self._async_client:
            # AsyncClient needs to be closed via async context
            self._async_client = None

    def __del__(self):
        self.close()
