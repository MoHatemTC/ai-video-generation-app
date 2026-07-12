# Architecture

This repository is divided into simple learning areas built around a staged generation pipeline.

## Backend

The backend runs the generation pipeline and exposes an API. It is responsible for:

- Accepting a simple instruction and creating a video job.
- Generating a structured script (transcript agent).
- Planning scenes and visual cues (planner agent).
- Generating the voiceover (text-to-speech).
- Producing word/segment timestamps (forced alignment).
- Sourcing or generating assets for each scene cue.
- Composing scenes and animating elements in sync with the narration.
- Rendering the final video and tracking job status.
- Calling the LLM and TTS providers through shared, swappable clients.

Recommended folders:

- `backend/routes/` - API endpoints.
- `backend/services/` - pipeline stages and business logic.
- `backend/models/` - data structures and database models.
- `backend/prompts/` - AI prompt templates.
- `backend/tests/` - backend tests.

## Frontend

The frontend is responsible for:

- Submitting a video instruction with optional parameters.
- Showing generation status and per-stage progress.
- Letting the user review and edit the script and scene plan before rendering.
- Downloading the finished video.

Recommended folders:

- `frontend/src/pages/` - full screens.
- `frontend/src/components/` - reusable UI pieces.
- `frontend/src/api/` - backend API calls.

## Pipeline Stages

The core of the product is an ordered pipeline. Each stage consumes the previous stage's structured JSON output and can fail and retry independently.

1. **Transcript** - instruction to a structured script (segments + visual cues).
2. **Planner** - script to a scene plan (layout + visual elements per scene).
3. **Audio** - script to a voiceover track (TTS).
4. **Alignment** - voiceover to word/segment timestamps.
5. **Assets** - each cue to a suitable asset (image, mermaid diagram, icon, GIF, SVG, clip).
6. **Composition** - assemble each scene's assets into a slide layout.
7. **Animation** - animate elements so they appear in time with the narration.
8. **Render** - combine animated scenes and audio into a final video file.

## AI Prompt Flow

Prompts should not be hard-coded inside service files.

Expected flow:

1. A stage loads a prompt from `backend/prompts/`.
2. The stage sends the previous stage's data to the AI client.
3. The AI client returns a structured JSON response.
4. The stage safely parses and validates the response before passing it on.

## Data Flow

Basic product flow:

1. User submits an instruction; the backend creates a `Video` job.
2. Transcript stage produces a `Script`.
3. Planner stage produces `Scene` plans with visual cues.
4. Audio stage produces an `AudioTrack`.
5. Alignment stage produces a `TimestampMap`.
6. Asset stage resolves an `Asset` per cue.
7. Composition and animation stages build the timed scenes.
8. Render stage produces the final video; the user downloads it.

## Job Management

Rendering is long-running, so generation runs as an asynchronous job. The API creates a job, a worker runs the pipeline stages, and the frontend polls status until the video is ready.
