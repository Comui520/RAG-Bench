"""OpenAI-compatible RAG API client."""

import httpx
from dataclasses import dataclass, field
from typing import List, Optional
from app.config import RAG_API_TIMEOUT_SECONDS


@dataclass
class RAGResponse:
    answer: str
    contexts: List[str] = field(default_factory=list)


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
            contexts = message.get("contexts", [])
        except (KeyError, IndexError, TypeError) as e:
            raise RAGClientError(f"Failed to parse RAG API response: {e}")

        if not isinstance(contexts, list):
            contexts = []

        return RAGResponse(answer=answer, contexts=contexts)

    def close(self):
        self._client.close()
