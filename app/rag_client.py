"""OpenAI-compatible RAG API client."""

import httpx
from dataclasses import dataclass, field
from typing import List, Optional
from app.config import RAG_API_TIMEOUT_SECONDS


@dataclass
class RAGResponse:
    answer: str
    contexts: List[str] = field(default_factory=list)
    warning: Optional[str] = None


class RAGClientError(Exception):
    pass


class RAGClient:
    def __init__(self, base_url: str, api_key: str):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self._client = httpx.Client(timeout=RAG_API_TIMEOUT_SECONDS)

    def query(self, question: str, model: str = "deepseek-chat") -> RAGResponse:
        url = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        body = {
            "model": model,
            "messages": [{"role": "user", "content": question}],
        }

        try:
            response = self._client.post(url, headers=headers, json=body)
        except httpx.TimeoutException as e:
            raise RAGClientError(f"RAG API request timed out: {e}") from e
        except httpx.RequestError as e:
            raise RAGClientError(f"RAG API request failed: {e}") from e

        if response.status_code != 200:
            raise RAGClientError(
                f"RAG API returned {response.status_code}: {response.text[:500]}"
            )

        data = response.json()
        return self._parse_response(data)

    def _parse_response(self, data: dict) -> RAGResponse:
        try:
            choice = data["choices"][0]
            message = choice.get("message", {})
            answer = message.get("content", "")
        except (KeyError, IndexError, TypeError) as e:
            raise RAGClientError(f"Failed to parse RAG API response: {e}")

        # 检索依据（contexts）多格式探测，兼容主流 RAG 服务：
        #   1. message.contexts      —— mini_rag / 部分 RAG 网关自定义字段
        #   2. message.citations     —— 部分 OpenAI 兼容服务
        #   3. 顶层 contexts/context —— 部分服务把依据放顶层
        contexts = []
        if isinstance(message.get("contexts"), list):
            contexts = message["contexts"]
        elif isinstance(message.get("citations"), list):
            contexts = [c.get("text") or c.get("content") or str(c) for c in message["citations"]]
        elif isinstance(data.get("contexts"), list):
            contexts = data["contexts"]
        elif isinstance(data.get("context"), list):
            contexts = data["context"]

        # 字符串形式的 contexts 也容错
        if isinstance(contexts, str):
            contexts = [contexts]
        contexts = [c for c in contexts if isinstance(c, str) and c.strip()]

        warning = None
        if not contexts:
            warning = (
                "RAG 服务未返回检索依据（contexts/citations 字段）。"
                "检索类指标（Contextual Relevancy/Recall/Precision）将无法正确评分；"
                "请确认 RAG 服务在响应中携带依据片段，或自定义字段名。"
            )

        return RAGResponse(answer=answer, contexts=contexts, warning=warning)

    def close(self):
        self._client.close()
