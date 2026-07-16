
This folder will contain the generation pipeline, API, prompts, data models, and tests.

Interns should create implementation files as part of assigned tasks.

# 🎨 Asset Service Lane — Sprint 1 (Omar Eldaly)

- `routes/` - API endpoints.
- `services/` - pipeline stages and business logic.
- `models/` - data models.
- `prompts/` - AI prompts.
- `tests/` - automated tests.

## Rule

Do not put all logic in one file. Keep routes small, and make each pipeline stage a separate, testable service that consumes and returns structured JSON.
