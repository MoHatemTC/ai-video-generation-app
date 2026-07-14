# Setup Guide

The backend pipeline (all 8 stages) and a minimal React frontend are implemented
and runnable end-to-end. This guide reflects the actual current state, not a plan.

## Requirements

- Python 3.11+
- Node.js 20+
- ffmpeg (required by the render stage - `ffmpeg -version` to check)
- An OpenAI API key for real script/scene-plan generation, TTS voiceover, and
  Whisper alignment. Without a key, the pipeline still runs end-to-end using
  documented fallbacks (see "Running without an API key" below) - useful for
  local development and CI.

## Local Setup

1. Clone the repository.
2. Copy `.env.example` to `.env` and add `OPENAI_API_KEY` (optional - see fallback note).
3. Install backend dependencies: `pip install -r requirements.txt`.
4. Install frontend dependencies: `cd frontend && npm install`.

## Running the Backend

```bash
uvicorn backend.main:app --reload --port 8000
```

- Health check: `GET http://localhost:8000/health`
- Interactive API docs: `http://localhost:8000/docs`
- SQLite DB file `video_studio.db` is created automatically on first run.

## Running the Frontend

```bash
cd frontend
npm run dev
```

Opens on `http://localhost:5173` and proxies `/videos`, `/intake`, `/health`
to the backend on port 8000 (see `frontend/vite.config.js`).

## Running Tests

```bash
pytest backend/tests/ -v
```

All AI-provider calls (LLM script/scene-plan generation, TTS) are mocked in
tests so the suite runs without an API key or network access. The render
stage runs for real via ffmpeg and asserts on the actual output `.mp4`.

## Running without an API key

Every stage that calls a paid provider degrades gracefully instead of
crashing the job, so the pipeline is runnable offline for development:

| Stage | With API key | Without API key |
|---|---|---|
| Script / Scene plan | Real LLM output | Fails at that stage (these two genuinely need an LLM - no meaningful fallback) |
| Voiceover (TTS) | Real speech audio | Fails at that stage (needs a real audio provider) |
| Alignment | Real Whisper word timestamps | Even-split heuristic from each segment's `duration_seconds` |
| Image assets | DALL-E generated images | Procedural SVG "concept card" placeholder |
| Composition / Animation / Render / Captions | Always run for real (no external provider needed) | Always run for real |

In short: script generation and voiceover need a real `OPENAI_API_KEY` to
produce a meaningful video: everything downstream of them is provider-agnostic
and always exercises the real code path (see `backend/tests/test_pipeline_integration.py`,
which mocks only the two LLM calls and the TTS call, and still produces a
real, playable `.mp4` via actual ffmpeg rendering).

## External Services

| Capability | Env vars | Status |
|---|---|---|
| LLM (transcript + planner agents) | `OPENAI_API_KEY` | Implemented via `backend/services/ai_client.py` |
| Text-to-speech (voiceover) | `OPENAI_API_KEY` (uses OpenAI TTS) | Implemented |
| Alignment (timestamps) | `OPENAI_API_KEY` (uses Whisper API) | Implemented, with offline heuristic fallback |
| Image assets | `OPENAI_API_KEY` (uses DALL-E 3) | Implemented, with procedural SVG fallback |
| Render | ffmpeg installed on the system | Implemented (ffmpeg overlay-filter based, see `docs/architecture.md`) |

`TTS_PROVIDER`/`TTS_API_KEY` and `IMAGE_PROVIDER`/`IMAGE_API_KEY` in
`.env.example` are reserved for swapping to a non-OpenAI provider later;
today both are served by the OpenAI client above.
