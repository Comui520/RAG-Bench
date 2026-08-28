"""Pydantic request/response models for the API."""

from typing import List, Optional
from pydantic import BaseModel, Field


class ModelConfig(BaseModel):
    """Configuration for an LLM or embedding model."""
    provider: str = Field(default="custom", description="deepseek|openai|anthropic|siliconflow|custom")
    api_format: str = Field(default="openai_chat", description="openai_chat|openai_json|anthropic")
    model_name: str = Field(..., min_length=1, description="Model identifier")
    api_key: str = Field(..., min_length=1, description="API key")
    base_url: str = Field(..., min_length=1, description="API base URL")


class EvaluateRequest(BaseModel):
    # User-facing task label
    task_name: Optional[str] = Field(default=None, max_length=120, description="Optional evaluation name")
    # RAG service under test
    rag_base_url: str = Field(..., min_length=1, description="RAG service base URL")
    rag_api_key: str = Field(..., min_length=1, description="RAG service API key")
    rag_model: str = Field(default="deepseek-chat", description="Model name for RAG queries")
    # Evaluation model (Synthesizer + metrics)
    eval_model: ModelConfig = Field(description="LLM for evaluation")
    # Embedding model (chunking)
    embed_model: Optional[ModelConfig] = Field(default=None, description="Embedding model")
    # Existing task
    task_id: Optional[str] = Field(default=None, description="Existing task ID from upload")


class TaskStatus(BaseModel):
    task_id: str
    status: str
    phase: str
    progress: float = Field(default=0.0, ge=0.0, le=1.0)
    error_message: Optional[str] = None
    created_at: Optional[str] = None
    completed_at: Optional[str] = None


class GoldenItem(BaseModel):
    id: int
    input: str
    expected_output: str
    context: Optional[str] = None


class MetricScore(BaseModel):
    name: str
    score: float
    passed: bool


class EvalResultItem(BaseModel):
    id: int
    golden_id: int
    input: str
    expected_output: str
    actual_output: str
    retrieval_context: Optional[str] = None
    metrics: List[MetricScore]
    passed: bool


class TaskResult(BaseModel):
    task_id: str
    status: str
    overall_scores: List[MetricScore]
    details: List[EvalResultItem]


class HistoryItem(BaseModel):
    task_id: str
    task_name: Optional[str] = None
    status: str
    rag_base_url: str
    created_at: Optional[str] = None
    completed_at: Optional[str] = None


class UploadedFile(BaseModel):
    id: int
    filename: str
    file_size: int


class ModelsResponse(BaseModel):
    """Response from GET /api/models proxy."""
    data: List[dict]
