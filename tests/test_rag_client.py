"""Unit tests for RAG API client."""

import httpx
import pytest
from app.rag_client import RAGClient, RAGResponse, RAGClientError


class TestRAGClient:
    def test_builds_correct_request(self, httpx_mock):
        import json as j
        httpx_mock.add_response(
            method="POST",
            url="https://rag.example.com/v1/chat/completions",
            json={
                "choices": [{
                    "message": {
                        "content": "The answer is 42.",
                        "contexts": ["doc chunk 1", "doc chunk 2"],
                    }
                }]
            },
        )
        client = RAGClient(base_url="https://rag.example.com/v1", api_key="sk-test")
        result = client.query("What is the answer?")

        assert result.answer == "The answer is 42."
        assert result.contexts == ["doc chunk 1", "doc chunk 2"]

        request = httpx_mock.get_request()
        assert request.headers["Authorization"] == "Bearer sk-test"
        body = j.loads(request.content)
        assert body["messages"][0]["content"] == "What is the answer?"

    def test_handles_timeout(self, httpx_mock):
        import app.config
        app.config.RAG_API_TIMEOUT_SECONDS = 1

        def raise_timeout(request):
            raise httpx.TimeoutException("timed out")

        httpx_mock.add_callback(raise_timeout)

        client = RAGClient(base_url="https://rag.example.com/v1", api_key="sk")
        with pytest.raises(RAGClientError, match="timed out"):
            client.query("test")

    def test_handles_non_200_response(self, httpx_mock):
        httpx_mock.add_response(status_code=500, json={"error": "server error"})
        client = RAGClient(base_url="https://rag.example.com/v1", api_key="sk")
        with pytest.raises(RAGClientError, match="500"):
            client.query("test")

    def test_extracts_contexts_from_response(self, httpx_mock):
        httpx_mock.add_response(
            method="POST",
            url="https://rag.example.com/v1/chat/completions",
            json={
                "choices": [{
                    "message": {
                        "content": "Answer.",
                        "contexts": ["ctx1"],
                    }
                }]
            },
        )
        client = RAGClient(base_url="https://rag.example.com/v1", api_key="sk")
        result = client.query("q")
        assert result.contexts == ["ctx1"]

    def test_handles_missing_contexts_gracefully(self, httpx_mock):
        httpx_mock.add_response(
            method="POST",
            url="https://rag.example.com/v1/chat/completions",
            json={
                "choices": [{
                    "message": {
                        "content": "Answer only.",
                    }
                }]
            },
        )
        client = RAGClient(base_url="https://rag.example.com/v1", api_key="sk")
        result = client.query("q")
        assert result.answer == "Answer only."
        assert result.contexts == []
