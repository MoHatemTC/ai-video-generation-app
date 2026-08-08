# Knowledge Share — Dockerizing the Project

**Presenter:** [Mahdi]
**Branch:** `feature/mahdi-docker-setup`
**Topic:** How I containerized the backend + frontend, what came up, and how the team can run it

---

## 1. Why we needed this

Before this, running the project meant everyone setting up Python, Node, ffmpeg, and all
the individual package versions by hand on their own machine — easy to get "works on my
machine" bugs. Docker packages the whole environment so everyone runs the exact same
setup with one command.

## 2. What I set up

- A `Dockerfile` for the backend (Python 3.11 + ffmpeg, since `whisperx` needs it)
- A `Dockerfile` for the frontend (Node 20, runs the Vite dev server)
- A `docker-compose.yml` at the project root that runs both together, with:
  - Backend on port 8000
  - Frontend on port 5173
  - Live volumes so code edits show up without rebuilding
- A `DOCKER_SETUP.md` guide so the rest of the team can get it running without me walking
  them through it live

## 3. What I learned / had to figure out

- **Layer caching**: copying `requirements.txt`/`package.json` before the rest of the code,
  so Docker only reinstalls dependencies when they actually change — makes rebuilds much
  faster.
- **`--host 0.0.0.0`**: Vite only listens on localhost by default, which is invisible from
  outside its own container — had to explicitly bind it to all interfaces.
- **Volumes vs. copied code**: mounted the source folders as volumes for live-reload during
  development, but excluded `node_modules` from the mount so the container's own installed
  version doesn't get overwritten by the host's (or a missing one).

## 4. Problems hit while testing the running stack

- Saw some Gemini model warnings in the logs during a run, but the pipeline had a fallback
  in place and the video still generated successfully end-to-end — didn't need any code
  changes for this one.
- The video renderer (`mp4_renderer`) logged `Executable doesn't exist at
  .../chrome-headless-shell` and fell back to a slower PIL-based renderer. Cause: Playwright's
  Python package gets installed via `pip`, but the actual browser binary it drives has to be
  downloaded separately with `playwright install`. The base Dockerfile wasn't running that
  step. Fixed by adding `RUN playwright install --with-deps chromium` to the backend
  Dockerfile (the `--with-deps` flag also pulls in the system libraries Chromium needs to
  launch inside a slim Linux image).
- Neither of these were Docker setup issues exactly — they only became visible once the
  full stack was actually running end-to-end, which is part of why containerizing and
  testing early is useful.

## 5. What the team needs to know going forward

- Run everything with `docker compose up --build` from the project root — see
  `DOCKER_SETUP.md` for the full walkthrough.
- Everyone needs their own `.env` file (not committed) with their own API keys.
- If you change `requirements.txt` or `package.json`, you need to rebuild
  (`docker compose up --build`) — normal code edits don't need a rebuild.

## 6. Next steps / open questions for the team

- Should we pin exact model names in one shared config file instead of scattering them
  across services, so we only have to update them in one place when Google changes
  availability again?
- Do we want a `docker-compose.prod.yml` variant later, or is dev-only scope enough for
  now?