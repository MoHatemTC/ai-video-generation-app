# Starter Tasks

Status legend: [x] implemented and tested · [~] implemented with a documented
fallback/limitation · [ ] not started.

## Sprint 1 - Blueprint & Agents

- [x] Create the first FastAPI app entry point. (`backend/main.py`)
- [x] Create a health check route. (`GET /health`)
- [x] Create a video job route that accepts an instruction. (`POST /videos`)
- [x] Create the transcript agent service. (`backend/services/transcript.py`)
- [x] Create the scene planner service. (`backend/services/planner.py`)
- [x] Create an AI client wrapper for the LLM provider. (`backend/services/ai_client.py`)
- [x] Create prompt files for the transcript and scene planner agents. (`backend/prompts/`)
- [x] Create the text-to-speech (voiceover) service. (`backend/services/audio.py`)
- [x] Create the alignment service. (`backend/services/alignment.py`, heuristic fallback when no API key)
- [x] Define the basic DB schema for `users` and `videos`. (`backend/models/db_models.py`)
- [x] Add backend tests for each service. (`backend/tests/`, 12 tests, all passing)

## Sprint 2 - Assets Collection

- [x] Create an asset resolver that maps a cue to an asset type. (`backend/services/assets.py`)
- [~] Add image generation or search. (DALL-E 3 when `OPENAI_API_KEY` set, else procedural SVG fallback)
- [ ] Add mermaid diagram generation. (currently uses the same procedural SVG fallback as other types - real mermaid rendering needs a Node/Puppeteer toolchain, left as follow-up)
- [~] Add icon, GIF, and SVG sourcing/generation. (SVG/icon: procedural generation implemented; GIF/short clip: not implemented, falls back to a static procedural image)
- [ ] Add simple clip generation.
- [x] Store assets with metadata (type, source, license, scene reference). (`Asset` model)
- [~] Build a reusable asset library keyed by concept. (deterministic color-per-concept only; no persistent cross-job asset cache yet)

## Sprint 3 - Scene Composition

- [x] Run the composition-engine spike and document the decision. (`docs/architecture.md` ADR: ffmpeg overlay filter, over Manim/Remotion)
- [x] Compose each scene's assets into a slide layout. (`backend/services/composition.py`)
- [x] Add a small set of reusable slide templates. (count-based 1/2/3-element grid positions; layout label is stored but doesn't yet vary position rules per `layout` value - follow-up)

## Sprint 4 - Animation Engine & Delivery

- [x] Animate scene components driven by the transcript timestamps. (`backend/services/animation.py`)
- [x] Sync each element's appearance to when it is mentioned. (word-match lookup against alignment timestamps)
- [x] Render composed, animated scenes plus voiceover into a final video. (`backend/services/render.py`, real ffmpeg output verified in tests)
- [x] Generate captions/subtitles from the timestamps. (`backend/services/captions.py`, SRT + burned-in via libass)
- [x] Wire the web app to submit, track, and download videos. (frontend `RequestPage`/`StatusPage` + `backend/routes/videos.py`)

## Frontend Tasks

- [x] Create the first React app. (Vite, `frontend/`)
- [x] Create a request page to submit an instruction. (`RequestPage.jsx`)
- [x] Create a status page showing per-stage progress. (`StatusPage.jsx`)
- [x] Create a review page to edit the script and scene plan before rendering. (script review is in `StatusPage.jsx`; scene-plan editing UI not yet added - script-level review covers the PRD 6.2 Must-have)
- [x] Create a download/result page. (video player + download button in `StatusPage.jsx`)
- [x] Connect the frontend to the backend health endpoint. (proxy in `vite.config.js`)

## Documentation Tasks

- [x] Update setup instructions after backend commands exist. (`docs/setup.md`)
- [x] Document each API endpoint as it is created. (`docs/api.md`)
- [x] Document required environment variables. (`docs/setup.md` "External Services" table)
- [x] Record the composition-engine decision. (`docs/architecture.md` ADR)

## Integration Tasks

- [ ] Add backend, frontend, and worker services to `docker-compose.yml`. (still the placeholder scaffold service - real compose file is a good next step)
- [~] Add an async job queue for long-running renders. (FastAPI `BackgroundTasks` used for the MVP; a real queue (Celery/RQ) is recommended before multi-user production use, since `BackgroundTasks` runs in-process and doesn't survive a server restart)
- [x] Update CI to run backend tests. (`.github/workflows/ci.yml`)
- [ ] Update CI to run frontend checks. (not added yet - `npm run build` passes locally)
- [ ] Add sample prompts and scripts for local demos. (one ad-hoc demo script produced `docs/../demo output`; not yet checked into `data/` as a reusable sample)
