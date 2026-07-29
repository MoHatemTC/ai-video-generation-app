# Week 3 — HTML Generation Pipeline: Kickoff Plan

## 1. Goal
Turn a `scene_plan.json` into a set of self-contained, animated `.html` files (or one merged file — see open question below) using 4 predefined layout templates, an updated scene planner that tags each scene with a `template` field, an `html_code_writer` agent, and a single wrapper function Omar can call for integration.

## 2. What's already built (context for Antigravity)
- `render_custom.py` — orchestrates: ingest ScenePlan → generate a *custom* Jinja2 template per topic via CrewAI → inject asset URLs → validate against `ScenePlan` Pydantic schema → render.
- `crew_agent.py` — CrewAI agent (`generate_template_with_crewai`) that prompts Gemini to produce a full Jinja2/HTML template (glassmorphism + Three.js style, TTS-gated scene transitions, mandatory transcript block, animated asset classes).
- `asset_agent.py` — CrewAI agent (`generate_assets_with_crewai`) that maps each visual cue's `asset_id`/description to an Iconify SVG URL, with a keyword-based fallback if the LLM call fails.
- `docker_scene_plan.json` — sample ScenePlan with `scene_id`, `text`, `subtitle`, `hold_ms`, `layout_hint`, and `visual_cues[]` (each with `cue_id`, `description`, `element_type`, `asset_id`, `appearance_trigger`, `preferred_region`, `importance`).
- `what-is-a-vpn__1_.html` — reference rendered video. Scene 0 (`#scene-0`) is the title/intro layout to copy structure from (logo row → left-title + cloud/visual → bottom row, staggered `fadeUp`/`popIn` animations). Scene 5 (`#scene-5`) is the outro/recap layout (checklist + final badge). Scenes 1–4 show content-layout patterns (risk-diagram, tunnel-diagram, flow-diagram, cards) to draw the 2 content templates from.

## 3. This week's shift: **static templates**, not per-topic generation
Today `crew_agent.py` asks an LLM to invent a brand-new Jinja2 template from scratch every run. The new task instead wants:
- 4 **fixed** HTML/Jinja2 templates (Intro, Content A, Content B, Outro) written once, by hand or with light AI assistance — analogous to PowerPoint layouts.
- The scene planner picks *which* of the 4 templates fits each scene (new `template` field), instead of an LLM freely designing layout every time.
- The `html_code_writer` agent's job shrinks to: given a scene + its assigned template + its assets, populate the template and emit one complete inlined HTML file — not invent layout/CSS from nothing.

## 4. Build checklist

### A. 4 static templates
- [ ] `template_intro.html` — adapt scene-0 of the VPN reference (logo, title, hero visual, bottom row).
- [ ] `template_content_a.html` — e.g. side-by-side / diagram-with-icons layout (scenes 1–3 style).
- [ ] `template_content_b.html` — e.g. card-grid layout (scene 4 style), for scenes that don't fit template A.
- [ ] `template_outro.html` — adapt scene-5 (checklist + final badge).
- Each template: Jinja2 placeholders for `scene.text`, `scene.subtitle`, `cue.asset_url`, `cue.description`, `cue.content`, all CSS inlined in `<style>`, all JS inlined in `<script>`, transcript block preserved, TTS-gated transition script preserved from the existing base player script in `crew_agent.py`.

### B. Scene planner extension
- [ ] Add a `template` field (enum: `intro` / `content_a` / `content_b` / `outro`) to the ScenePlan schema and to whatever step currently generates `scene_plan.json`.
- [ ] Feed short template descriptions into that generation step's prompt so it assigns the right template per scene based on `layout_hint`/content shape.

### C. `html_code_writer` agent
- [ ] New CrewAI (or plain LLM call) agent, replacing/superseding `generate_template_with_crewai`.
- [ ] Input: one scene object (with its now-required `template` field) + the matching static template + resolved asset URLs (from `asset_agent.py`, unchanged).
- [ ] Model: strong LLM — evaluate Qwen (hosted API) vs. local execution for cost/latency/availability; document the decision.
- [ ] Output: one complete, self-contained HTML file per scene (inline CSS + JS, zero errors).

### D. Integration wrapper
- [ ] Single callable function, e.g. `generate_video_html(scene_plan: dict, asset_data: dict | None) -> dict`, with a documented input/output contract (what it takes, what it returns — file paths? HTML strings? one file or many?) so Omar Dorgham can call it directly.

### E. Deliverables to produce
- [ ] Source + docs for: 4 templates, updated scene planner, `html_code_writer` agent, wrapper function.
- [ ] At least one finalized generated HTML output (ideally the Docker sample) proving inline CSS/JS animations render with zero console errors.

## 5. Open questions to resolve before/while building
1. **Output shape**: does the wrapper return one HTML file per scene, or one merged multi-scene HTML file (like the VPN reference, which is a single file with all scenes as `<div class="scene">` and one shared player script)? The task says "generate a complete .html file per scene," but the reference example and `render_custom.py` both produce one merged file. Worth confirming with your mentor — it changes how the wrapper and the shared TTS/transition script are structured.
2. **Where does `template` get assigned**: inside the existing scene-plan generation step (prompt-based) or as a separate rule-based post-processing step keyed off `layout_hint`?
3. **Qwen access**: hosted API key available, or does it need to run locally? Affects the `html_code_writer` LLM call setup.
4. **Content A vs. Content B split**: what rule decides between them — number of visual cues, `layout_hint` value, or something else?

## 6. What to hand Antigravity to start
Give it, in one message or as attached files:
- [ ] This plan file.
- [ ] `render_custom.py`, `crew_agent.py`, `asset_agent.py` (as-is, for the current pipeline shape and the base player script/CSS to reuse).
- [ ] `docker_scene_plan.json` (or another sample ScenePlan) as a concrete input to test against.
- [ ] `what-is-a-vpn__1_.html` as the visual/structural reference for the intro and outro templates.
- [ ] The `ScenePlan` Pydantic schema file (`backend/app/schemas/scene.py`) — referenced by `render_custom.py` but not yet provided; needed to add the `template` field correctly.
- [ ] Answers to the 4 open questions above, or explicit permission for Antigravity to pick reasonable defaults and flag them.
- [ ] The exact repo path/structure so it knows where `html_code_writer` and the wrapper function should live relative to the existing `backend/app/pipeline/render/` modules.
