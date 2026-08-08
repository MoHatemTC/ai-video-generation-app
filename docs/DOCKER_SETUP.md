# Local Setup Guide — Running the Project with Docker

**Branch:** `feature/mahdi-docker-setup`

This guide walks you through running the full backend + frontend stack locally using
Docker, without installing Python or Node dependencies directly on your machine.

## 1. Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) installed and running
  (you'll see the whale icon in your system tray/menu bar when it's up)
- Git

That's it — you don't need Python, Node, or any of the project's libraries installed
locally. Docker handles all of that inside the containers.

## 2. Clone the repo and switch to this branch

```bash
git clone https://github.com/MoHatemTC/ai-video-generation-app.git
cd ai-video-generation-app
git checkout <this-branch-name>
```

## 3. Create your `.env` file

Copy the example file and fill in your own keys:

```bash
cp .env.example .env
```

Open `.env` and fill in:

| Variable | What it's for |
|---|---|
| `LITELLM_API_KEY` | Team's internal LLM proxy key |
| `GROQ_API_KEY` | Free fallback model provider ([console.groq.com](https://console.groq.com)) |
| `GEMINI_API_KEY` (if used) | For the asset/composition Gemini calls |
| `SUPABASE_URL` / `SUPABASE_KEY` | Database + asset storage |

> Never commit your real `.env` file — it's already excluded via `.gitignore`.

## 4. Build and run everything

From the project root:

```bash
docker compose up --build
```

First run will take a few minutes (downloading base images + installing dependencies).
Subsequent runs are much faster.

To view the live logs of the running services, use:
```bash
docker compose logs -f
```

## 5. Where to find things once it's running

| Service | URL |
|---|---|
| Backend API (FastAPI docs) | http://localhost:8000/docs |
| Frontend (web app) | http://localhost:5173 |

## 6. Making changes while it's running

Both the backend and frontend folders are mounted as live volumes, so any code change
you save locally is picked up automatically — no need to rebuild for normal code edits.

You only need to rebuild if you change dependencies (`requirements.txt` or
`package.json`):

```bash
docker compose up --build
```

## 7. Stopping everything

```bash
# Ctrl+C in the terminal running docker compose, then:
docker compose down
```

## 8. Common issues

| Problem | Fix |
|---|---|
| Port already in use | Something else on your machine is using 8000 or 5173 — stop it, or change the port mapping in `docker-compose.yml` |
| `Playwright rendering fallback to PIL generator` / `Executable doesn't exist at .../chrome-headless-shell` | Playwright's Python package was installed but its browser binary wasn't — the Dockerfile now runs `playwright install --with-deps chromium` during the build so this shouldn't happen anymore. If you still see it, rebuild with `docker compose up --build` (a cached layer may be skipping the install step) |
| Changes not showing up | Make sure you saved the file inside the mounted folder (`backend/` or `frontend/`), not somewhere else |
| `.env` values not picked up | Restart the stack after editing `.env` — env vars are only read at container startup |