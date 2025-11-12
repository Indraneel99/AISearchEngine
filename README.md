---
title: Articles Search Engine
emoji: 🔎
colorFrom: blue
colorTo: indigo
sdk: gradio
sdk_version: "5.45.0"
app_file: frontend/app.py
python_version: "3.12"
pinned: false
---

# Articles Search Engine

A compact, production-style RAG pipeline. It ingests Substack, Medium and top publications RSS articles, stores them in Postgres (Supabase), creates dense/sparse embeddings in Qdrant, and exposes search and answer endpoints via FastAPI with a simple Gradio UI.

## How it works (brief)
- Ingest RSS → Supabase:
  - Prefect flow (`src/pipelines/flows/rss_ingestion_flow.py`) reads feeds from `src/configs/feeds_rss.yaml`, parses articles, and writes them to Postgres using SQLAlchemy models.
- Embed + index in Qdrant:
  - Content is chunked, embedded (e.g., BAAI bge models), and upserted to a Qdrant collection with payload indexes for filtering and hybrid search.
  - Collection and indexes are created via utilities in `src/infrastructure/qdrant/`.
- Search + generate:
  - FastAPI (`src/api/main.py`) exposes search endpoints (keyword, semantic, hybrid) and assembles answers with citations.
  - LLM providers are pluggable with fallback (OpenRouter, OpenAI, Hugging Face).
  - Opik is used for Evaluation
- UI + deploy:
  - Gradio app for quick local search (`frontend/app.py`).
  - Containerization with Docker and optional deploy to Google Cloud Run.

## Tech stack
- Python 3.12, FastAPI, Prefect, SQLAlchemy
- Supabase (Postgres) for articles
- Qdrant for vector search (dense + sparse/hybrid)
- OpenRouter / OpenAI / Hugging Face for LLM completion, Opik for LLM Evaluation
- Gradio UI, Docker, Google Cloud Run
- Config via Pydantic Settings, `uv` or `pip` for deps

## Run locally (minimal)
1) Configure environment (either `.env` or shell). Key variables (Pydantic nested with `__`):
   - Supabase: `SUPABASE_DB__HOST`, `SUPABASE_DB__PORT`, `SUPABASE_DB__NAME`, `SUPABASE_DB__USER`, `SUPABASE_DB__PASSWORD`
   - Qdrant: `QDRANT__URL`, `QDRANT__API_KEY`
   - LLM (choose one): `OPENROUTER__API_KEY` or `OPENAI__API_KEY` or `HUGGING_FACE__API_KEY`
   - Optional CORS: `ALLOWED_ORIGINS`

2) Install dependencies:
```bash
# with uv
uv venv && source .venv/bin/activate
uv pip install -r requirements.txt

# or with pip
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

3) Initialize storage:
```bash
python src/infrastructure/supabase/create_db.py
python src/infrastructure/qdrant/create_collection.py
python src/infrastructure/qdrant/create_indexes.py
```

4) Ingest and embed:
```bash
python src/pipelines/flows/rss_ingestion_flow.py
python src/pipelines/flows/embeddings_ingestion_flow.py
```

5) Start services:
```bash
# REST API
uvicorn src.api.main:app --reload

# Gradio UI (optional)
python frontend/app.py
```

## Project structure (high-level)
- `src/api/` — FastAPI app, routes, middleware, exceptions
- `src/infrastructure/supabase/` — DB init and sessions
- `src/infrastructure/qdrant/` — Vector store and collection utilities
- `src/pipelines/` — Prefect flows and tasks for ingestion/embeddings
- `src/models/` — SQL and vector models
- `frontend/` — Gradio UI
- `configs/` — RSS feeds config

