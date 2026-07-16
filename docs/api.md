# API Documentation

API endpoints should be documented here as they are created.

For each endpoint, include:

- Method and path.
- Purpose.
- Request body example.
- Response example.
- Error cases.

## Example Format

```txt
POST /videos

Purpose:
Submit a simple instruction and start a video generation job.

Request:
JSON body, e.g. { "instruction": "A short video about photosynthesis", "length": "short", "audience": "beginner" }

Response:
JSON with the created job, e.g. { "id": "vid_123", "status": "queued" }
```

```txt
GET /videos/{id}

Purpose:
Check generation status and per-stage progress, and get the download link when ready.

Response:
JSON with status, current stage, and output link when the render is complete.
```
