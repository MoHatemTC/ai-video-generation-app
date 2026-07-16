# Frontend

Minimal React (Vite) app covering the full user flow from PRD 6.1: submit an
instruction, review/edit the generated script, watch stage progress, and
download the finished video.

## Structure

- `src/pages/RequestPage.jsx` - submit an instruction (+ tone/audience/length).
- `src/pages/StatusPage.jsx` - polls job status, shows per-stage progress,
  the script review/edit step, and the final video player + download button.
- `src/api/client.js` - all backend calls in one place.

## Run

```bash
npm install
npm run dev
```

Proxies API calls to `http://localhost:8000` (the backend) — see `vite.config.js`.
