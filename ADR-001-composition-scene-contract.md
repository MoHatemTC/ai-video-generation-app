# ADR-002: Use SVG for Sprint 1 Composition Preview

## Status

Accepted — 16 July 2026

## Context

The Composition lane needs to consume three structured JSON inputs:

- Scene Plan: scenes, layouts, visual cues, asset references, and appearance
  triggers;
- Assets: asset URLs and metadata linked to a scene and cue;
- Alignment: segment and word timestamps.

The implementation must produce a renderer-ready JSON output that preserves
the video and scene IDs, resolves visual asset URLs, calculates deterministic
1920×1080 layouts, and assigns each element a start/end time. The team also
needs a simple way to review the calculated slide layouts before the later
Animation and Render stage produces video.

The current implementation includes:

- `composed_scene.py`: strict Pydantic input/output contracts;
- `composition.py`: a Python service that validates inputs and builds the
  renderer-ready `CompositionOutput`;
- `svg_preview_renderer.py`: an optional static preview renderer;
- `run_composition.py`: a command-line runner that writes JSON output and SVG
  previews;
- automated tests for successful composition and invalid input cases.

Three possible preview/composition approaches were considered:

| Option   | Assessment                                                                                                                                       |
| -------- | ------------------------------------------------------------------------------------------------------------------------------------------------ |
| SVG      | Can be generated from Python, uses exact coordinates, opens in a browser, and is lightweight for static review.                                  |
| Manim    | Python-native and strong for advanced educational animation, but introduces more rendering complexity than the current slide-layout scope needs. |
| Remotion | Strong for React-based video templates and timeline animation, but adds a Node.js/React rendering runtime to the Python backend.                 |

## Decision

We will use **SVG as the initial static composition-preview format**.

`CompositionService` will remain engine-agnostic: it only creates validated
JSON describing scenes, elements, positions, sizes, layers, resolved assets,
and timing. `SvgPreviewRenderer` will consume that JSON and create one SVG file
per scene for visual review. It does not change the JSON contract and does not
implement final animation or MP4 rendering.

The proof of concept has been run successfully using filled sample Scene Plan,
Asset, and Alignment JSON. It produced a populated `composition_output.json`
and three scene SVG files for the supported layouts:

- `title_slide`
- `image_left_text_right`
- `text_left_image_right`

## Consequences

### Positive

- The Python service remains simple, deterministic, and easy to test.
- The shared JSON contract is independent of the final animation engine.
- SVG previews make positions, text, asset regions, and layer order visible in
  a browser before rendering video.
- Segment-start and word-trigger timing are already included in output for the
  future animation stage.
- No additional rendering server, Node.js runtime, or animation dependency is
  needed for Sprint 1.

### Negative / limitations

- The SVG renderer produces static review files; it does not animate the
  `start` and `end` values.
- Text wrapping is basic and only three reusable layouts are supported.
- A visual element requires a non-empty `asset_id` and `asset_url`; placeholder
  local paths are labelled in previews, while real hosted URLs can display the
  actual asset.
- Final transitions, audio composition, and MP4 generation remain work for the
  Animation and Render stage.

## Reconsideration

Revisit this decision if the project requires complex reusable motion graphics,
an advanced visual timeline, production React video templates, or specialised
mathematical animations. In that case, run a new time-boxed spike and consider
Remotion for template-driven video generation or Manim for specialised
educational animations. The existing `CompositionOutput` contract should remain
the boundary unless the new renderer proves that additional data is needed.
