# RAG Evaluation Platform

B/S-architecture RAG evaluation platform powered by [deepeval](https://github.com/confident-ai/deepeval).

## Quick Start

### Backend
```bash
pip install -r requirements.txt
export DEEPSEEK_API_KEY=your_key
uvicorn app.main:app --reload --port 8000
```

### Frontend
```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173.

## Architecture
- **Backend**: FastAPI + deepeval (official) + SQLite
- **Frontend**: React + TypeScript + Tailwind CSS + TanStack Query + Recharts

## Testing
```bash
# Backend (54 tests)
pytest tests/ -v --ignore=tests/test_pipeline_goldens.py --ignore=tests/test_pipeline_evaluate.py

# Backend integration tests (requires DEEPSEEK_API_KEY)
DEEPSEEK_API_KEY=your_key pytest tests/test_pipeline_goldens.py tests/test_pipeline_evaluate.py -v

# Frontend (16 tests)
cd frontend && npm test
```

## Evaluation Pipeline
1. Upload knowledge base documents
2. Configure your RAG API endpoint (OpenAI-compatible)
3. deepeval Synthesizer generates goldens (Q&A pairs)
4. Review and confirm goldens
5. Pipeline calls your RAG API for each question and runs metrics
6. View results dashboard with scores and per-question breakdown

## Metrics
- **Retriever**: ContextualRelevancy, ContextualRecall, ContextualPrecision
- **Generator**: AnswerRelevancy, Faithfulness

## Models
- **Evaluation**: deepseek-v4-flash (via DeepSeek API)
- **Embedding**: SiliconFlow BAAI/bge-m3
