

---
FastAPI app implementing all 8 pipeline stages end-to-end. Entry point:
`backend/main.py` (`uvicorn backend.main:app --reload`).

# 🎨 Asset Service Lane — Sprint 1 (Omar Eldaly)

This service takes raw, loose visual cues from scripts/slides and refines them into highly detailed, ready-to-use descriptive image generation prompts using specialized AI agents.

### 🛠️ Architecture & Core Concepts

1. **Asynchronous Task Processing (`asyncio.gather`)**
   * Sourcing assets (talking to LLM APIs) is an **I/O-bound operation**.
   * Instead of resolving visual cues one-by-one, `process_scene_elements` uses `asyncio.gather` to trigger all prompt refinements concurrently. This keeps API response times fast.

2. **Event-Loop Protection (`run_in_executor`)**
   * CrewAI's `.kickoff()` execution is synchronous and blocking by default.
   * To prevent the FastAPI app from freezing while waiting for the LLM to respond, the blocking kickoff is isolated inside Python's default ThreadPoolExecutor using `loop.run_in_executor(None, ...)`.

3. **Metadata Sourcing & Local Storage**
   * When a visual cue is successfully refined, `register_asset_in_storage` mock-persists its metadata (assigning `source="generated"` and `license="open-source"`) into a local database file at `data/supabase_asset_metadata.json` for asset ownership tracing.

4. **Primary LLM Driver (Gemini Flash 1.5)**
   * Configured using `gemini/gemini-1.5-flash` under the director's free-quota guideline, with a safe static fallback (`Illustration showing: {cue}`) in case of API timeouts.

---

### 💻 How to Run & Verify the Service

#### 1. Environment Setup
Ensure your local `.env` file exists in the root directory and contains your active API key:
```env
GEMINI_API_KEY="your-gemini-api-key-here"
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
