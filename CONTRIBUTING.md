# Contributing Guide

This file defines how the team collaborates. Everyone should follow the same process so the project stays easy to review, test, and integrate.

## Team Communication

- Use the team chat for quick questions, blockers, and daily updates.
- Use GitHub Issues for planned work, bugs, and feature requests.
- Use Pull Requests for code review and discussion about implementation.
- Ask for help early if you are blocked for more than 30 minutes.
- Keep messages clear: explain what you tried, what happened, and what you need.

## Before Starting Work

1. Read the related docs and issue.
2. Confirm the expected output with your mentor or team lead if unclear.
3. Create a new branch from `main`.
4. Keep your work focused on one task.

## Branch Naming Policy

Use short, descriptive branch names:

```txt
feature/transcript-agent
feature/scene-planner
fix/alignment-timestamps
docs/setup-guide
chore/update-gitignore
```

Allowed prefixes:

- `feature/` - new feature.
- `fix/` - bug fix.
- `docs/` - documentation only.
- `test/` - tests only.
- `chore/` - maintenance, configs, cleanup.

## Commit Message Policy

Use this format:

```txt
type(scope): short description
```

Examples:

```txt
feature(transcript): add structured script generation
fix(align): handle words with missing timestamps
docs(setup): add backend setup instructions
test(planner): add scene plan validation tests
chore(repo): update gitignore
```

Allowed commit types:

- `feature` - user-facing feature or important project capability.
- `fix` - bug fix.
- `docs` - documentation changes.
- `test` - adding or updating tests.
- `refactor` - code restructuring without behavior changes.
- `chore` - tooling, configs, formatting, or maintenance.

Commit rules:

- Keep commits small and meaningful.
- Do not commit secrets, API keys, `.env`, generated media, or local virtual environments.
- Do not use vague messages like `update`, `changes`, or `final`.
- If a commit touches multiple unrelated areas, split it.

## Pull Request Policy

Every PR must include:

- A clear title.
- A short summary of what changed.
- The issue or task it relates to, if available.
- How the change was tested.
- Screenshots or a sample clip for frontend/render changes when useful.
- Notes about blockers, tradeoffs, or unfinished parts.

PR size rules:

- Keep PRs focused on one topic.
- Avoid mixing docs, backend, frontend, and formatting changes unless the task needs it.
- Large tasks should be split into smaller PRs.

Review rules:

- At least one teammate should review before merging.
- The author should respond to comments respectfully and clearly.
- Reviewers should focus on correctness, readability, tests, and maintainability.
- Do not approve code you do not understand.

Merge rules:

- Merge only after CI passes.
- Merge only after requested changes are resolved.
- Delete the branch after merging.

## Code Organization Rules

- Routes should handle HTTP request/response logic only.
- Pipeline stages and reusable logic should live in `backend/services/`.
- Each pipeline stage should consume and return structured JSON.
- Prompts should live in `backend/prompts/`, not inside Python files.
- Tests should live in `backend/tests/`.
- Frontend pages should live in `frontend/src/pages/`.
- Reusable frontend components should live in `frontend/src/components/`.

## Prompt Policy

Prompts are part of the product and must be reviewed like code.

When adding a prompt:

- Create a separate `.md` file in `backend/prompts/`.
- Explain the purpose of the prompt at the top.
- Define the expected output format.
- Ask for JSON when the backend needs structured output.
- Tell the AI to stay factually accurate and not invent facts, definitions, sources, or data.
- Mention which service or pipeline stage uses the prompt.

## Responsible AI Rules

- Scripts are educational content — keep them factually accurate and reviewable by a human before rendering.
- Use only generated or license-cleared assets. Never embed copyrighted images, GIFs, or clips.
- Use licensed TTS voices only. Do not clone a real person's voice without consent.
- Record the source and license of every asset used in a video.

## Environment Variable Policy

- Add required variables to `.env.example`.
- Never commit `.env`.
- Use clear names like `OPENAI_API_KEY`, `TTS_API_KEY`, and `DATABASE_URL`.
- Document new variables in `docs/setup.md` or `docs/deployment.md`.

## Definition of Done

A task is done when:

- The requested behavior works.
- The code is placed in the correct folder.
- Tests are added or updated when relevant.
- Docs are updated when setup, behavior, or usage changes.
- The PR description explains what changed.
- CI passes.
