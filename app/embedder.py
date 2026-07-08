"""SiliconFlow embedding model wrapped for deepeval compatibility."""

from typing import List, Optional, Any
from langchain_openai import OpenAIEmbeddings
from deepeval.models import DeepEvalBaseEmbeddingModel


class SiliconFlowEmbeddingModel(DeepEvalBaseEmbeddingModel):
    """OpenAI-compatible embedding model adapter for SiliconFlow / any provider."""

    def __init__(
        self,
        api_key: str,
        model_name: str,
        base_url: str,
        timeout: Optional[float] = None,
        max_retries: int = 3,
        **kwargs: Any,
    ):
        self._model: Optional[OpenAIEmbeddings] = None
        self._api_key = api_key
        self._model_name = model_name
        self._base_url = base_url
        self._timeout = timeout
        self._max_retries = max_retries
        self._extra_kwargs = kwargs
        super().__init__()

    def get_model_name(self) -> str:
        return self._model_name

    def load_model(self):
        if self._model is None:
            self._model = OpenAIEmbeddings(
                api_key=self._api_key,
                model=self._model_name,
                base_url=self._base_url,
                timeout=self._timeout,
                max_retries=self._max_retries,
                **self._extra_kwargs,
            )
        return self._model

    def embed_text(self, text: str) -> List[float]:
        self.load_model()
        return self._model.embed_query(text)

    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        self.load_model()
        return self._model.embed_documents(texts)

    async def a_embed_text(self, text: str) -> List[float]:
        return self.embed_text(text)

    async def a_embed_texts(self, texts: List[str]) -> List[List[float]]:
        return self.embed_texts(texts)
