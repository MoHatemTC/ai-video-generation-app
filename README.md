# Sprints Video Studio

AI-powered e-learning video generator that turns a simple instruction — e.g. *"I want a video about X, generate it"* — into a complete, MOOC-style video with script, voiceover, timed visuals, and narration-synced animation.

## Current Status

The full 8-stage pipeline is implemented and runs end-to-end (backend
FastAPI + SQLite, minimal React frontend), with real ffmpeg rendering
producing a playable `.mp4`. Script generation and voiceover need a real
`OPENAI_API_KEY`; every downstream stage runs for real either way, with
documented fallbacks where no key is set (see `docs/setup.md`, "Running
without an API key"). See `docs/tasks.md` for exactly what's done vs. still
a follow-up (e.g. real mermaid diagrams, GIF/clip generation, a durable job
queue, and CI).

This repository started as a learning scaffold for an internship cohort; the
documentation/contribution-workflow framing below still applies to anyone
extending it further.

## Project Areas

- `backend/` - pipeline stages, API, prompts, data models, and tests.
- `frontend/` - user interface for submitting requests and downloading videos.
- `data/` - sample prompts, scripts, scene plans, and assets for local development.
- `docs/` - product, setup, architecture, deployment, and workflow documentation.
- `scripts/` - helper scripts for setup, testing, and local tasks.

## The Pipeline

The product runs a prompt through an ordered pipeline. Each stage consumes the previous stage's structured output:

`instruction → transcript → scene plan → voiceover → timestamps → assets → composition → animation → render`

## First Steps

1. Read `docs/PRD.md`.
2. Read `docs/architecture.md`.
3. Read `CONTRIBUTING.md`.
4. Pick a task from `docs/tasks.md`.
5. Create a branch and open a pull request when ready.

## Important Rule

Do not add large feature code directly to `main`. Every change should go through a branch and pull request.
