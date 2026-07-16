# Starter Tasks

These tasks are intentionally not implemented in the scaffold. Interns should create the needed files as part of the learning process. They are grouped to roughly follow the sprint plan in `docs/PRD.md`.

## Sprint 1 - Blueprint & Agents

- Create the first FastAPI app entry point.
- Create a health check route.
- Create a video job route that accepts an instruction.
- Create the transcript agent service (instruction to structured script).
- Create the scene planner service (script to scene plan with cues).
- Create an AI client wrapper for the LLM provider.
- Create prompt files for the transcript and scene planner agents.
- Create the text-to-speech (voiceover) service.
- Create the alignment service (word/segment timestamps).
- Define the basic DB schema for `users` and `videos`.
- Add backend tests for each service.

## Sprint 2 - Assets Collection

- Create an asset resolver that maps a cue to an asset type.
- Add image generation or search.
- Add mermaid diagram generation.
- Add icon, GIF, and SVG sourcing/generation.
- Add simple clip generation.
- Store assets with metadata (type, source, license, scene reference).
- Build a reusable asset library keyed by concept.

## Sprint 3 - Scene Composition

- Run the composition-engine spike (SVG combiner, Manim, JS templates / Remotion).
- Document the decision in an architecture decision record.
- Compose each scene's assets into a slide layout.
- Add a small set of reusable slide templates.

## Sprint 4 - Animation Engine & Delivery

- Animate scene components driven by the transcript timestamps.
- Sync each element's appearance to when it is mentioned.
- Render composed, animated scenes plus voiceover into a final video.
- Generate captions/subtitles from the timestamps.
- Wire the web app to submit, track, and download videos.

## Frontend Tasks

- Create the first React app.
- Create a request page to submit an instruction.
- Create a status page showing per-stage progress.
- Create a review page to edit the script and scene plan before rendering.
- Create a download/result page.
- Connect the frontend to the backend health endpoint.

## Documentation Tasks

- Update setup instructions after backend commands exist.
- Document each API endpoint as it is created.
- Document required environment variables.
- Record the composition-engine decision.

## Integration Tasks

- Add backend, frontend, and worker services to `docker-compose.yml`.
- Add an async job queue for long-running renders.
- Update CI to run backend tests.
- Update CI to run frontend checks.
- Add sample prompts and scripts for local demos.
