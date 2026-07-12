# Sprints Video Studio

AI-powered e-learning video generator that turns a simple instruction — e.g. *"I want a video about X, generate it"* — into a complete, MOOC-style video with script, voiceover, timed visuals, and narration-synced animation.

This repository is intentionally a learning scaffold. It provides the project structure, documentation, contribution rules, and collaboration workflow. Interns should create the actual feature files as part of their assigned tasks.

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
