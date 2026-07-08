"""Pydantic request/response models for the API."""

from typing import List, Optional
from pydantic import BaseModel, Field


class EvaluateRequest(BaseModel):
    rag_base_url: str = Field(..., min_length=1, description="RAG service base URL")
    rag_api_key: str = Field(..., min_length=1, description="RAG service API key")
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
    status: str
    rag_base_url: str
    created_at: Optional[str] = None
    completed_at: Optional[str] = None


class UploadedFile(BaseModel):
    id: int
    filename: str
    file_size: int
