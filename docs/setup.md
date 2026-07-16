# Setup Guide

This project starts as a scaffold. Interns will add backend, frontend, and integration files as tasks are assigned.

## Requirements

- Git
- Python 3.11 or newer
- Node.js 20 or newer, when frontend implementation starts
- ffmpeg, when the render stage starts
- Docker, optional for local containers

## Local Setup

1. Clone the repository.
2. Copy `.env.example` to `.env` and fill in the keys you need.
3. Read `CONTRIBUTING.md`.
4. Pick an assigned task.
5. Create only the files needed for that task.

## Backend Setup

The backend will live in `backend/`.

When backend implementation starts, the team should:

1. Add needed packages to `requirements.txt`.
2. Create the first FastAPI entry file.
3. Add the first pipeline stage under `backend/services/`.
4. Add tests in `backend/tests/`.
5. Update this setup guide with the exact run command.

## Frontend Setup

The frontend will live in `frontend/`.

When frontend implementation starts, the team should:

1. Choose the agreed React setup.
2. Add frontend dependencies.
3. Add pages under `frontend/src/pages/`.
4. Update this setup guide with the exact run command.

## External Services

Each pipeline stage depends on an external capability. Configure these in `.env` as stages are built:

- **LLM** (transcript + planner agents) - `OPENAI_API_KEY` or `GEMINI_API_KEY`.
- **Text-to-speech** (voiceover) - `TTS_PROVIDER`, `TTS_API_KEY`.
- **Alignment** (timestamps) - a Whisper/WhisperX model or STT API.
- **Assets** (image generation/search) - `IMAGE_PROVIDER`, `IMAGE_API_KEY`.
- **Render** - ffmpeg installed on the system.

Keep each provider behind a swappable client so it can be replaced later.
