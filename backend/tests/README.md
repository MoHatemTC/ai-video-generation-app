# 🎬 AI Video Generation Platform

FastAPI app implementing all 8 pipeline stages end-to-end. 
Entry point: `backend/main.py` (`uvicorn backend.main:app --reload`).

---

# 🎨 Asset Service Lane — Sprint 1 (Omar Eldaly)

This service takes raw, loose visual cues from scripts/slides and refines them into highly detailed, ready-to-use descriptive image generation prompts using specialized AI agents.

## Core Features
- **Asset Metadata Registry**: Logs generated assets dynamically into `data/supabase_asset_metadata.json`.
- **Async Pipeline Support**: Fully integrated with the backend orchestrator loop using standard dict data contracts.
- **Robust Mock Testing**: Covered by automated unit tests under `backend/tests/test_assets.py`.

## Directory Map
- `main.py` - FastAPI app, CORS, DB init, router registration, `/health`.
- `backend/app/services/assets/` - Contains our image handling and generation pipelines.