"""Hardcoded configuration for the evaluation platform."""

import os

# Evaluation model (used by Synthesizer critic + all metrics)
# Temporarily using deepseek-chat — reverts to deepseek-v4-flash once deepeval registers it
EVAL_MODEL_NAME = os.getenv("EVAL_MODEL_NAME", "deepseek-chat")
EVAL_MODEL_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
EVAL_MODEL_BASE_URL = os.getenv("EVAL_MODEL_BASE_URL", "https://api.deepseek.com")

# Embedding model (used by ContextConstructionConfig for chunking)
EMBEDDING_MODEL_NAME = os.getenv("EMBEDDING_MODEL_NAME", "BAAI/bge-m3")
EMBEDDING_API_KEY = os.getenv(
    "EMBEDDING_API_KEY",
    "sk-foqvyfnzfehmqqxjrxowgogxrqbtvsikuggjerhqlbzwlnok",
)
EMBEDDING_BASE_URL = os.getenv(
    "EMBEDDING_BASE_URL",
    "https://api.siliconflow.cn/v1",
)

# Chunking parameters for Synthesizer ContextConstructionConfig
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "400"))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "50"))

# Goldens generation
MAX_GOLDENS_PER_CONTEXT = int(os.getenv("MAX_GOLDENS_PER_CONTEXT", "3"))

# Task timeout (seconds)
TASK_TIMEOUT_SECONDS = int(os.getenv("TASK_TIMEOUT_SECONDS", "600"))

# Storage root
DATA_DIR = os.getenv("DATA_DIR", "./data")

# Database path
DATABASE_URL = os.getenv("DATABASE_URL", "rag_eval.db")

# RAG API request timeout
RAG_API_TIMEOUT_SECONDS = int(os.getenv("RAG_API_TIMEOUT_SECONDS", "30"))

# Model name to use when querying the RAG API (defaults to deepseek-chat for testing)
RAG_MODEL_NAME = os.getenv("RAG_MODEL_NAME", "deepseek-chat")
