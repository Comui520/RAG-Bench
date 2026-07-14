"""Infrastructure configuration for the evaluation platform."""

import os

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
