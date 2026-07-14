# API Documentation

Base URL (local dev): `http://localhost:8000`. Full interactive schema also
available at `/docs` (Swagger UI) once the server is running.

## `GET /health`

Purpose: liveness check.

Response:
```json
{ "status": "ok", "app": "Sprints Video Studio" }
```

## `POST /videos`

Purpose: submit an instruction, create a video job, and run stage 1
(script generation) synchronously. Returns with `status: "awaiting_review"`
so the user can review the script before the (slower, costlier) remaining
stages run.

Request:
```json
{
  "instruction": "I want a video about how photosynthesis works",
  "tone": "professional",
  "audience": "general",
  "length_minutes": 1.5
}
```

Response (`201`):
```json
{
  "id": "6d9b6b1e-...",
  "status": "awaiting_review",
  "stage_detail": "awaiting_review",
  "error_message": null,
  "output_url": null
}
```

Error case: if script generation fails (e.g. missing `OPENAI_API_KEY`), the
job is still created with `status: "failed"` and `error_message` set.

## `GET /videos/{id}`

Purpose: poll job status and per-stage progress (PRD 7.10).

Response: same shape as above. `status` is one of `queued`, `script`,
`awaiting_review`, `planning`, `audio`, `alignment`, `assets`,
`composition`, `animation`, `rendering`, `completed`, `failed`.

## `GET /videos/{id}/script`

Purpose: fetch the generated script JSON for human review (PRD 6.2).

Response: the `VideoScriptBlueprint` JSON (title, target_audience,
estimated_total_duration, segments[]).

Errors: `404` if the job doesn't exist, `409` if the script hasn't been
generated yet.

## `POST /videos/{id}/approve`

Purpose: approve (optionally edited) the script and trigger stages 2-8 as a
background task (scene planning -> voiceover -> alignment -> assets ->
composition -> animation -> render).

Request (optional body - omit to approve as-is):
```json
{ "approved_script_json": "{...edited VideoScriptBlueprint JSON...}" }
```

Response: job status, now `planning` (processing continues in the background;
poll `GET /videos/{id}` for progress).

Errors: `409` if the job isn't currently `awaiting_review`.

## `GET /videos/{id}/download`

Purpose: stream the final rendered `.mp4` once the job is `completed`.

Errors: `409` if the video isn't ready yet.

## `POST /intake` (legacy/simple endpoint)

Purpose: a synchronous, no-job-tracking endpoint that only runs the script
stage and returns the script directly. Useful for quick script previews
without creating a `Video` row. Superseded by `POST /videos` for the full
product flow.
