# Architecture Decision Record (ADR)

## ADR-001: Sprint 1 Composition Scene Contract

**Author:** Nada Ahmed Samir  
**Project:** Sprints Video Studio  
**Status:** Proposed  
**Date:** 13 July 2026

## Context

The Composition stage sits between the Scene Planner and the Animation/Render stage. Its responsibility is to convert scene information into a validated composed-scene representation that the renderer can consume.

During Sprint 1, the final upstream Scene Planner contract and downstream renderer requirements are still being developed by other team members. Temporary dummy data is therefore used to allow the Composition lane to be scaffolded and tested independently.

The current implementation includes:

- `backend/app/schemas/composed_scene.py`
- `backend/app/services/composition.py`
- `backend/tests/test_composition.py`

## Decision

For the Sprint 1 scaffold, the Composition service receives a scene-plan dictionary whose elements already include:

- Element identifier
- Element type
- Position
- Size
- Text or asset reference, when applicable

The service validates this input with Pydantic and returns a `ComposedScene` object.

The current service does **not** calculate element coordinates from the layout name. It treats the supplied coordinates and dimensions as input assumptions.

## Coordinate Assumptions

- Coordinates are represented in pixels.
- The origin `(0, 0)` is the top-left corner of the slide/canvas.
- `x` increases from left to right.
- `y` increases from top to bottom.
- `x` and `y` must be greater than or equal to zero.
- `width` and `height` must be greater than zero.
- A scene may contain one or more elements.
- Each element in the list is validated using the same `Element` schema.

## Error-Handling Decision

The service follows a fail-fast approach:

- Valid input returns a `ComposedScene`.
- Missing required top-level keys or invalid nested values raise `ValueError`.
- Invalid or incomplete scenes are not passed to the Animation/Render stage.
- The orchestrator is responsible for catching the error, recording the job failure, retrying, or requesting corrected input.

This prevents incomplete scene data from causing harder-to-diagnose failures later in the pipeline.

## Testing Decision

The unit tests cover three essential behaviours:

1. A valid scene plan returns a valid composed scene.
2. A missing required field raises `ValueError`.
3. An invalid nested value, such as a negative coordinate, raises `ValueError`.

These tests cover the successful path, missing-key path, and Pydantic validation path without overcomplicating the Sprint 1 scaffold.

## Alternatives Considered

### 1. Pass the raw scene plan directly to the renderer

This was rejected because high-level scene instructions are not sufficiently precise for rendering. The renderer needs validated element types, positions, sizes, and later timing information.

### 3. Return a partial scene when validation fails

This was rejected because downstream stages should not receive invalid or incomplete rendering instructions.

## Consequences

### Positive

- The Composition contract can be developed and tested independently.
- Pydantic provides consistent validation for every element.
- The renderer will eventually receive structured, predictable data.
- The assumptions are documented clearly.

### Limitations

- Timing, asset resolution, layering, styles, and animations are not yet included.
- The service currently depends on temporary scene-plan data.
- The input contract must be updated after alignment with the Scene Planner and renderer owners.

## Future Work

- Confirm the Scene Planner output schema.
- Confirm the Animation/Render input requirements.
- Add canvas dimensions, timing, layer order, styles, and asset references.
- Replace dummy data with real pipeline outputs.
