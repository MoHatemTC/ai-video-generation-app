# Backend

FastAPI app implementing all 8 pipeline stages end-to-end. Entry point:
`backend/main.py` (`uvicorn backend.main:app --reload`).

## Folder Guide

- `main.py` - FastAPI app, CORS, DB init, router registration, `/health`.
- `db.py` - SQLAlchemy engine/session setup (SQLite by default).
- `routes/` - `intake.py` (quick script-only preview), `videos.py` (full job lifecycle).
- `services/` - one file per pipeline stage, plus `pipeline.py` (orchestrator)
  and `ai_client.py` (shared, swappable LLM/TTS client).
- `models/` - `db_models.py` (SQLAlchemy: `User`, `Video`), plus Pydantic
  schemas for each stage's structured output (`script.py`, `scene.py`, `timeline.py`, `video.py`).
- `prompts/` - versioned prompt templates, kept out of service code.
- `tests/` - one test module per service, plus a full pipeline integration test.

See `docs/setup.md` for how to run it and `docs/api.md` for the endpoint reference.
