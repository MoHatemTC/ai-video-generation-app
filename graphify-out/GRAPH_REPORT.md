# Graph Report - .  (2026-08-06)

## Corpus Check
- cluster-only mode — file stats not available

## Summary
- 498 nodes · 843 edges · 32 communities (28 shown, 4 thin omitted)
- Extraction: 97% EXTRACTED · 3% INFERRED · 0% AMBIGUOUS · INFERRED: 28 edges (avg confidence: 0.53)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `5caf6dcb`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- AlignmentService
- test_audio.py
- AssetService
- ScenePlan
- render_custom.py
- devDependencies
- process_video_job
- _search_csv
- server.cjs
- render-graphs.js
- crew_agent.py
- App.jsx
- run_suite
- update-superpowers.sh
- start-server.sh
- stop-server.sh
- find-polluter.sh

## God Nodes (most connected - your core abstractions)
1. `AlignmentService` - 22 edges
2. `AssetService` - 21 edges
3. `ScenePlan` - 20 edges
4. `AudioService` - 19 edges
5. `process_video_job()` - 18 edges
6. `VideoScriptBlueprint` - 18 edges
7. `TTSRequest` - 16 edges
8. `ScenePlanner` - 15 edges
9. `generate_video_html()` - 14 edges
10. `TimestampMap` - 12 edges

## Surprising Connections (you probably didn't know these)
- `run_live_test()` --calls--> `process_video_job()`  [EXTRACTED]
  run_live_pipeline_test.py → backend/app/pipeline/orchestrator.py
- `main()` --calls--> `AssetService`  [EXTRACTED]
  live_test.py → backend/app/services/assets/images.py
- `search()` --calls--> `_search_csv()`  [INFERRED]
  .agent/.shared/mobile-uiux-promax/scripts/mobile-search.py → .agent/.shared/ui-ux-pro-max/scripts/core.py
- `search_stack()` --calls--> `_search_csv()`  [INFERRED]
  .agent/.shared/mobile-uiux-promax/scripts/mobile-search.py → .agent/.shared/ui-ux-pro-max/scripts/core.py
- `process_video_job()` --calls--> `SceneDirector`  [EXTRACTED]
  backend/app/pipeline/orchestrator.py → backend/app/agents/director.py

## Import Cycles
- None detected.

## Communities (32 total, 4 thin omitted)

### Community 0 - "AlignmentService"
Cohesion: 0.05
Nodes (63): BaseModel, ScriptSegment, VideoScriptBlueprint, AudioTrack, BaseModel, Timestamp schemas for the Alignment stage. This module defines the public…, Reference to the generated voiceover audio file., Precise timing for a single spoken word, with identifiers for downstream… (+55 more)

### Community 1 - "test_audio.py"
Cohesion: 0.05
Nodes (52): ABC, AudioTrack, BaseModel, Schema representing the output contract for generated audio metadata. Matches…, Schema representing the input payload for generating a voiceover., TTSRequest, AudioService, generate_voiceover() (+44 more)

### Community 2 - "AssetService"
Cohesion: 0.05
Nodes (39): AssetItem, AssetResponseContract, BaseModel, Standardized visual asset representing a flat item structure for Stage 6…, The final schema delivery wrapper expected by Youssef's Animation Engine., AssetService, process_scene_elements(), Any (+31 more)

### Community 3 - "ScenePlan"
Cohesion: 0.08
Nodes (36): Any, Task, SceneDirector, extract_scene_plan_from_raw(), Any, Task, ScenePlanner, QualityDimension (+28 more)

### Community 4 - "render_custom.py"
Cohesion: 0.07
Nodes (38): generate_assets_with_crewai(), normalize_model_name(), Returns a dict mapping asset_id -> Iconify API URL string., _build_writer_prompt(), normalize_model_name(), populate_scene_template(), HTML Code Writer Agent — populates static Jinja2 templates using CrewAI +…, Direct Jinja2 rendering — always works since templates use standard Jinja2… (+30 more)

### Community 5 - "devDependencies"
Cohesion: 0.05
Nodes (41): autoprefixer, eslint, @eslint/js, eslint-plugin-react-hooks, eslint-plugin-react-refresh, dependencies, lucide-react, react (+33 more)

### Community 6 - "process_video_job"
Cohesion: 0.10
Nodes (25): get_fallback_config(), get_planner_config(), process_video_job(), JobResponse, BaseModel, RenderJob, User, Video (+17 more)

### Community 7 - "_search_csv"
Cohesion: 0.12
Nodes (21): _format_result(), main(), search(), search_stack(), BM25, detect_domain(), _load_csv(), Build BM25 index from documents (+13 more)

### Community 8 - "server.cjs"
Cohesion: 0.11
Nodes (26): broadcast(), clients, computeAcceptKey(), CONTENT_DIR, crypto, debounceTimers, decodeFrame(), encodeFrame() (+18 more)

### Community 9 - "render-graphs.js"
Cohesion: 0.33
Nodes (8): combineGraphs(), { execSync }, extractDotBlocks(), extractGraphBody(), fs, main(), path, renderToSvg()

### Community 10 - "crew_agent.py"
Cohesion: 0.43
Nodes (6): _build_agent_prompt(), generate_fallback_custom_template(), generate_template_with_crewai(), normalize_model_name(), CrewAI Agent for Generating Customized Jinja2 HTML Video Templates. Uses Google…, Normalize user configured model name for CrewAI Google Gemini integration.

### Community 11 - "App.jsx"
Cohesion: 0.53
Nodes (3): App(), PIPELINE_STAGES, ScenePlayer()

### Community 13 - "run_suite"
Cohesion: 0.67
Nodes (3): main(), Run all test_*.py in .agent/.tests/<skill_name>/. Returns (passed_files,…, run_suite()

## Knowledge Gaps
- **44 isolated node(s):** `update-superpowers.sh script`, `crypto`, `http`, `fs`, `path` (+39 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **4 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `generate_voiceover()` connect `test_audio.py` to `AlignmentService`, `process_video_job`?**
  _High betweenness centrality (0.100) - this node is a cross-community bridge._
- **Why does `ScenePlan` connect `ScenePlan` to `render_custom.py`?**
  _High betweenness centrality (0.084) - this node is a cross-community bridge._
- **Why does `AlignmentService` connect `AlignmentService` to `process_video_job`?**
  _High betweenness centrality (0.084) - this node is a cross-community bridge._
- **Are the 5 inferred relationships involving `AlignmentService` (e.g. with `VideoScriptBlueprint` and `AudioTrack`) actually correct?**
  _`AlignmentService` has 5 INFERRED edges - model-reasoned connections that need verification._
- **Are the 3 inferred relationships involving `AssetService` (e.g. with `AssetItem` and `TestAssetServiceQualityEvaluation`) actually correct?**
  _`AssetService` has 3 INFERRED edges - model-reasoned connections that need verification._
- **Are the 4 inferred relationships involving `AudioService` (e.g. with `AudioTrack` and `TTSRequest`) actually correct?**
  _`AudioService` has 4 INFERRED edges - model-reasoned connections that need verification._
- **What connects `update-superpowers.sh script`, `crypto`, `http` to the rest of the system?**
  _44 weakly-connected nodes found - possible documentation gaps or missing edges._