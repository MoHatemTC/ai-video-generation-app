# Product Requirements Document (PRD)
## AI-Powered E-Learning Video Generator

| | |
|---|---|
| **Product (working title)** | Sprints Video Studio |
| **Document type** | Product Requirements Document (PRD) |
| **Version** | v1.0 (Draft) |
| **Owner** | Program / Product Lead |
| **Builders** | Internship cohort (fresh graduates & junior professionals) |
| **Status** | Draft for review |

---

## 1. Overview

### 1.1 Summary
Sprints Video Studio is an AI-powered tool that turns a simple instruction — e.g., *"I want a video about X, generate it"* — into a complete, MOOC-style e-learning video. From that single prompt the system writes the script, plans the scenes, generates the voiceover, aligns the narration to precise timestamps, sources or generates the visual assets (images, diagrams, icons, GIFs, SVGs, short clips), composes each scene, and animates it. The defining feature: visual components animate **in sync with the narration** — each element appears on screen exactly when the instructor's voice mentions it, keeping the video engaging. The user submits a topic through a web app and receives the finished video.

### 1.2 Vision
Let anyone produce engaging, consistent, MOOC-style educational videos at scale from a prompt — matching the Sprints.ai course format — without manual scripting, recording, asset hunting, or video editing.

### 1.3 Why now
Producing course videos is slow and expensive: scripting, slide design, voiceover recording, asset sourcing, animation, and syncing are all manual. LLMs (script + scene planning), text-to-speech (voiceover), forced alignment (timestamps), and programmatic animation now make it possible to generate timed, animated e-learning videos automatically — turning hours of production into minutes.

### 1.4 Video style (v1)
- **Slide + voiceover (MOOC style).** Slides are the main visual; the instructor voice explains. A presenter face is not required and is out of scope for v1.
- The architecture keeps "style" configurable so additional styles can be added later; v1 ships and validates the Slide + voiceover style first.

---

## 2. Problem Statement

Creating e-learning videos consistently requires teams to:
- Write an accurate, well-structured script for each topic.
- Design slides and decide what visuals appear and when.
- Record or generate a clear voiceover.
- Source relevant, license-safe assets (images, diagrams, icons, GIFs).
- Animate elements and sync them to the narration.
- Re-do all of the above whenever content changes or a new topic is added.

The result is a slow, costly production bottleneck that is hard to scale across many topics and courses, and content quickly goes stale.

---

## 3. Goals & Objectives

### 3.1 Product goals
1. **Prompt-to-video** — generate a complete e-learning video from a single simple instruction.
2. **Engaging by design** — animate visual components in sync with the narration so elements appear as they are mentioned.
3. **On-brand, MOOC-style output** — produce Slide + voiceover videos consistent with the Sprints.ai format.
4. **Relevant visuals** — source or generate assets that match each scene's content.
5. **Reliable pipeline** — run scripting → audio → timestamps → assets → composition → animation → render end-to-end.
6. **Self-serve web app** — let users request and download videos without editing tools.

### 3.2 Learning objectives (for the internship team)
Build a working AI product while practicing: Python, APIs, JSON, and file handling; LLM APIs (OpenAI / Gemini) and multi-agent design; prompt engineering for script and scene planning; text-to-speech and forced-alignment (timestamped transcription); asset generation and sourcing (images, mermaid diagrams, icons, GIFs, SVGs); programmatic scene composition and animation (SVG / Manim / JS templates); rendering pipelines; responsible AI with human verification; and professional engineering practices (GitHub, documentation, modular code, team collaboration), culminating in a final demo.

### 3.3 Success is *not*
- A talking-head / avatar presenter (out of scope for v1).
- Publishing without human review — generated scripts and videos are checked before use.
- A full manual video editor / timeline UI.

---

## 4. Target Users & Personas

| Persona | Profile | Primary need |
|---|---|---|
| **Instructional designer** | Sprints content team producing course videos. | Generate on-brand course videos fast, at scale. |
| **Subject-matter expert / instructor** | Domain expert with no video-editing skills. | Turn expertise into a polished video from a prompt. |
| **Self-directed creator / learner** | Wants an explainer video on a topic. | Get a clear, engaging video without production work. |

All three use the same core flow; differences show up mainly in how much they review and refine the generated script before rendering.

---

## 5. Scope

### 5.1 In scope (v1)
- Simple instruction intake ("generate a video about X").
- Transcript / script generation (agent).
- Scene planning (agent) — break the script into scenes with visual cues.
- Voiceover generation (text-to-speech).
- Timestamped transcription (word/segment timestamps for sync).
- Asset collection & generation (images, mermaid diagrams, icons, GIFs, SVGs, simple clips).
- Scene composition (combine assets into slide layouts).
- Animation & sync engine (elements appear in time with the narration).
- Rendering to a final video file.
- Web app to submit a request and download the video.
- Basic database (users, videos).
- Style: Slide + voiceover (MOOC), no presenter face.

### 5.2 Out of scope (v1)
- Talking-head / avatar / lip-synced presenter.
- Manual timeline / drag-and-drop video editor.
- Multi-language voiceover (stretch goal).
- Background music composition.
- LMS publishing / SCORM packaging.
- Interactive or branching video.
- Payments / subscriptions.

---

## 6. User Flows

### 6.1 Generation flow
1. User enters a simple instruction (topic + optional details) in the web app.
2. **Transcript agent** writes a structured script.
3. **Planner agent** breaks the script into scenes and assigns visual cues per line.
4. **Audio generation** produces the voiceover from the script.
5. **Timestamped transcription** aligns narration to word/segment timestamps.
6. **Asset step** sources or generates the visuals each scene needs.
7. **Composition** assembles each scene's layout from its assets.
8. **Animation engine** animates elements and syncs their appearance to the timestamps.
9. **Render** produces the final video; the user downloads it.

### 6.2 Review checkpoint (human-in-the-loop)
- Before rendering, the user can review (and optionally edit) the generated script and scene plan. This keeps content accurate and avoids wasting render time on a flawed script.

---

## 7. Functional Requirements

Requirements use **MoSCoW** priority: (M) Must, (S) Should, (C) Could.

### 7.1 Instruction Intake
- (M) Accept a simple text instruction describing the desired video topic.
- (S) Accept optional parameters (target length, audience level, tone).
- (C) Accept a source document/outline to base the video on.

### 7.2 Transcript Generation Agent
- (M) Generate a structured script from the instruction, segmented into lines/sections.
- (M) Output structured JSON (segments with text and intended visual cues).
- (S) Keep the script within a target length / duration.

### 7.3 Scene Planner Agent
- (M) Break the script into scenes; for each scene, specify the layout and the visual elements to show.
- (M) Attach a visual cue to script segments so the composition/animation stages know *what* appears and *when* it should be mentioned.
- (S) Choose an appropriate visual type per cue (image, diagram, icon, GIF, SVG, clip).

### 7.4 Audio (Voiceover) Generation
- (M) Generate a clear voiceover from the script using a text-to-speech engine.
- (S) Support selectable voice(s) and speaking rate.
- (C) Cache audio to avoid regenerating unchanged segments.

### 7.5 Timestamped Transcription (Alignment)
- (M) Produce word/segment-level timestamps aligning the narration to the script.
- (M) Expose timestamps in a structured format the animation engine can consume.

### 7.6 Asset Collection & Generation
- (M) For each scene cue, source or generate a suitable asset: generated/searched images, mermaid diagrams, icons, GIFs, generated SVGs, and simple clips.
- (M) Store assets with metadata (type, source, license, scene reference).
- (S) Maintain a reusable asset library / resolver keyed by concept.
- (M) Use only license-safe or generated assets (see Responsible AI).

### 7.7 Scene Composition
- (M) Assemble each scene's assets into a coherent slide layout matching the planned design.
- (M) Produce a composed scene representation the animation engine can render.
- (S) Support a small set of reusable slide templates/layouts.

### 7.8 Animation & Sync Engine
- (M) Animate scene components (appear / transition) driven by the transcript timestamps.
- (M) Ensure each element appears in sync with the moment it is mentioned in the narration.
- (S) Support a basic set of entrance/transition animations.
- (C) Allow per-element timing overrides.

### 7.9 Rendering & Delivery
- (M) Render the composed, animated scenes plus voiceover into a single video file.
- (M) Make the final video available for the user to download.
- (S) Generate subtitles/captions from the timestamped transcript.

### 7.10 Web App & Job Management
- (M) Web app to submit an instruction, track generation status, and download the result.
- (M) Handle generation as an asynchronous job (rendering is long-running).
- (S) Show per-stage progress (script → audio → assets → render).

### 7.11 Data / Storage
- (M) Basic database with **users** and **videos** tables (video job status, metadata, output link).
- (S) Store intermediate artifacts (script, scenes, assets, timestamps) per video.

---

## 8. AI & Agent Requirements

| Agent / AI capability | Purpose | Output |
|---|---|---|
| Transcript Generator Agent | Instruction → structured script | JSON script (segments + cues) |
| Scene Planner Agent | Script → scene plan | Scenes with layouts + visual cues |
| Audio Generation (TTS) | Script → voiceover | Audio track |
| Timestamped Transcription | Narration → alignment | Word/segment timestamps |
| Asset resolution / generation | Cue → asset | Image / diagram / icon / GIF / SVG / clip |

Requirements:
- (M) Agents must exchange **structured JSON** so each stage can consume the previous stage's output.
- (M) Responses must be safely parsed with error handling and per-stage retries.
- (M) Prompts must instruct the script agent to stay factually accurate and avoid inventing false information.
- (S) Keep prompts modular and versioned so they can be iterated without touching pipeline code.
- (S) Track token / API cost per generation.

---

## 9. Responsible AI Requirements

- (M) **Content accuracy**: educational scripts must be factually correct; a human reviews the script before rendering.
- (M) **Human-in-the-loop**: users can review/edit the script and plan before the final video is produced.
- (M) **Asset licensing**: use only generated or license-cleared assets; never embed copyrighted images, GIFs, or clips without rights.
- (M) **Voice licensing**: use licensed TTS voices; do not clone a real person's voice without consent.
- (M) **Accessibility**: generate captions/subtitles from the timestamped transcript.
- (S) **Attribution**: record the source/license of every asset used in a video.
- (S) **Bias & appropriateness**: keep generated content neutral, inclusive, and audience-appropriate.

---

## 10. Technical Requirements & Architecture

### 10.1 Suggested stack
- **Language**: Python (agents / pipeline) with JavaScript/TypeScript for the web app and any JS-based scene templates.
- **LLM API**: OpenAI or Gemini for the transcript and planner agents (keep the interface abstracted).
- **Text-to-speech**: a TTS engine/API for the voiceover (keep abstracted so it can be swapped).
- **Timestamps / alignment**: a speech-to-text model with word-level timestamps (e.g., Whisper / WhisperX) for forced alignment.
- **Assets**: an image-generation model or search for images; **mermaid** for diagrams; icon libraries; GIF sources; programmatic **SVG** generation; simple generated clips.
- **Scene composition & animation (spike in Sprint 3)**: evaluate and pick one — SVG composition, the **Manim** Python library, or JS templates (e.g., **Remotion** for React-based programmatic video). Remotion and Manim are strong candidates for timestamp-driven animation.
- **Rendering**: ffmpeg (and/or the chosen engine's renderer) to combine animated scenes with audio.
- **Backend**: FastAPI with an asynchronous job queue for long-running renders.
- **Frontend**: a React web app.
- **Database**: PostgreSQL (users, videos, and intermediate artifacts).
- **Storage**: object/file storage for assets and rendered videos.
- **Version control & collaboration**: GitHub with modular code and documentation.

### 10.2 High-level components
1. **Orchestration / pipeline service** — runs the agents and stages in sequence.
2. **Transcript service** — generates the script.
3. **Planner service** — produces the scene plan.
4. **Audio service** — text-to-speech voiceover.
5. **Alignment service** — timestamped transcription.
6. **Asset service** — sources/generates and stores assets.
7. **Composition service** — assembles scenes.
8. **Animation & render engine** — animates and renders the final video.
9. **Web app + API + job management** — request, track, download.
10. **Storage layer** — users, videos, scripts, scenes, assets, timestamps.

### 10.3 Core data entities
`User`, `Video` (job + status + output), `Script` (segments), `Scene` (layout + cues), `Asset` (type + source + license), `AudioTrack`, `TimestampMap`, `RenderJob`.

---

## 11. Non-Functional Requirements

- **Reliability**: each pipeline stage handles failures independently and can retry without restarting the whole job.
- **Performance**: generation runs asynchronously; the web app stays responsive while renders complete in the background.
- **Cost control**: cache scripts/audio/assets; monitor LLM, TTS, and image-generation spend; cap video length in v1.
- **Scalability**: pipeline stages are modular so heavy steps (assets, render) can scale independently.
- **Security**: protect user data; no secrets in the repo; API keys via environment variables.
- **Maintainability**: modular code, clear stage boundaries, meaningful commits.
- **Documentation**: README, setup guide, architecture notes, agent/prompt docs, and the composition-engine decision record.

---

## 12. Success Metrics

### 12.1 Product metrics
| Metric | What it measures |
|---|---|
| Generation success rate | Share of prompts that produce a complete video |
| Time-to-video | End-to-end generation time per video |
| Sync accuracy | How well element appearance matches the narration timing |
| Output quality rating | Human rating of clarity, visuals, and engagement |
| Asset relevance | How well assets match each scene's content |
| Cost per video | Combined LLM + TTS + asset + render cost |

### 12.2 Internship success criteria
A working end-to-end web app that turns a simple prompt into a finished Slide + voiceover video; functioning transcript and planner agents; voiceover with accurate timestamps; assets composed into scenes; animation synced to the narration; a clean GitHub repo with documentation; responsible-AI practices applied; and a polished final demo.

---

## 13. Milestones (Sprint Plan)

The whole project runs across **four sprints**. Each sprint begins with a short market-research side task (see note).

| Sprint | Focus | Key outputs |
|---|---|---|
| **Sprint 1** | Blueprint & Agents | Transcript Generator Agent, Planner Agent, Audio Generation (TTS), Timestamped Transcription (word/segment timestamps); basic DB schema (users & videos tables); the pipeline blueprint tying stages together |
| **Sprint 2** | Assets Collection | Per-member asset sourcing/generation — images (generated or searched), diagrams (mermaid), icons, GIFs, generated SVGs, simple clips — assembled into a reusable asset library/resolver |
| **Sprint 3** | Scene Composition | Compose assets into a final scene look; run a spike comparing approaches (SVG combiner, Manim, JS templates / Remotion) and select one; produce composed scenes |
| **Sprint 4** | Animation Engine & Delivery | Animation engine that animates components and syncs element appearance to the transcript timestamps; final render; web-app integration; testing, documentation, and final demo |

**Market-research side task (all members, start of each sprint — first one submitted with the learner's first technical task):** research competitors and how e-learning videos look, and identify the key concepts an e-learning video should include. The Sprint 1 findings feed the blueprint and scene design.

---

## 14. Team Roles (Internship)

Every team member is an **AI Engineer**. The team shares full ownership of the AI product; the areas below indicate primary ownership so nothing falls through the cracks — not separate job titles. Ownership can rotate across sprints.

- **AI Engineer — Product & Delivery (rotating)** — owns the PRD, backlog, blueprint, and demo narrative.
- **AI Engineer — Agents & Orchestration** — transcript and planner agents, pipeline wiring, prompt iteration.
- **AI Engineer — Audio & Alignment** — voiceover generation and timestamped transcription.
- **AI Engineer — Assets** — image/diagram/icon/GIF/SVG/clip sourcing and generation, asset library.
- **AI Engineer — Composition & Animation** — scene composition and the timestamp-driven animation/render engine.
- **AI Engineer — Web App & QA** — FastAPI/React web app, job management, testing, documentation.

On a small team these areas overlap; the point is clear ownership per area while everyone contributes as an AI Engineer across the codebase.

---

## 15. Risks & Mitigations

| Risk | Mitigation |
|---|---|
| Asset licensing / copyright | Use only generated or license-cleared assets; record source and license per asset. |
| Timestamp / sync inaccuracy | Use forced alignment (e.g., WhisperX); test element timing against narration. |
| Long render times / high cost | Async jobs, caching of script/audio/assets, capped video length in v1. |
| Content inaccuracy (hallucination) | Human review of the script before rendering; accuracy-focused prompts. |
| Composition-engine uncertainty (many options) | Time-boxed spike in Sprint 3; pick one and document the decision. |
| TTS voice licensing / consent | Use licensed voices only; no unauthorized voice cloning. |
| Scope creep (talking head, multi-language) | Enforce v1 scope; defer stretch goals to a backlog. |

---

## 16. Assumptions & Dependencies

- Access to an LLM API (OpenAI / Gemini), a TTS engine, an image-generation/search option, and an alignment model.
- A rendering environment (ffmpeg and/or the chosen animation engine) is available.
- v1 targets the Slide + voiceover style, a single language, and short videos.
- Users can describe the desired video in a simple instruction and review the generated script before rendering.