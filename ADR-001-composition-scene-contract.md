# ADR-001: Composition Scene Contract & Composition Engine Selection

**Status:** Accepted  
**Author:** Nada Ahmed Samir  
**Date:** July 2026

---

# Context

The AI video generation pipeline is divided into multiple stages:

```
Script
   ↓
Scene Planner
   ↓
Composition
   ↓
Animation
   ↓
Rendering
```

The Composition stage receives a high-level `ScenePlan` describing **what** should appear in a scene and is responsible for producing a renderer-ready `ComposedScene` describing **where** everything should appear.

Sprint 1 also requires visible static evidence proving that the calculated layout is correct.

To determine the most appropriate preview technology, a **time-boxed composition-engine spike** was performed comparing several approaches.

---

# Composition Engine Spike

The following approaches were investigated.

## Option 1 — SVG

### Advantages

- Native support for exact coordinates (x, y)
- Easy generation directly from Python
- Lightweight with no rendering server required
- Opens immediately in any modern browser
- Supports text, images, icons, and vector graphics
- Easy to inspect and debug since SVG is plain text
- Ideal for static layout validation

### Limitations

- Text wrapping must be implemented manually
- Limited animation support compared to dedicated rendering engines
- Local images require proper file paths or embedding

---

## Option 2 — Manim

### Advantages

- Python-native animation framework
- Excellent for educational and mathematical animations
- Powerful timeline-based rendering

### Limitations

- Heavy rendering pipeline
- More complex than required for Sprint 1
- Focused primarily on animation rather than layout preview

---

## Option 3 — Remotion

### Advantages

- Modern React-based video generation
- Excellent support for timelines and animations
- Suitable for production-quality video rendering

### Limitations

- Requires React and Node.js
- Introduces additional technologies outside the Python pipeline
- Better suited for later rendering stages than Sprint 1 composition

---

# Decision

SVG was selected as the composition preview technology for Sprint 1.

The Composition Service remains responsible for calculating deterministic layouts and producing a validated `ComposedScene`.

SVG is used **only** to visualize the calculated layout and provide static evidence that the composition logic works correctly.

The renderer remains independent from the Composition Service and may later be implemented using another technology.

---

# Architecture

```
                 Scene Planner
                      │
                      │ ScenePlan
                      ▼
        +-----------------------------+
        |     Composition Service     |
        |-----------------------------|
        | Validate ScenePlan          |
        | Select Layout Template      |
        | Calculate Positions         |
        | Calculate Sizes             |
        | Assign Layers               |
        | Build ComposedScene         |
        +-----------------------------+
                      │
                      │ ComposedScene
                      ▼
          SVG Preview / Future Renderer
```

---

# Responsibilities

## Scene Planner

Responsible for deciding:

- Scene type
- Layout type
- Title
- Body text
- Required assets
- Script segment references

It does **not** calculate coordinates.

---

## Composition Service

Responsible for:

- Validating the ScenePlan
- Selecting the requested layout
- Calculating element positions
- Calculating element sizes
- Assigning layer order
- Producing a renderer-ready `ComposedScene`

---

## Renderer

Responsible for:

- Drawing the composed scene
- Applying animations
- Producing the final video

---

# Supported Layouts

Sprint 1 currently supports:

- `title_slide`
- `image_left_text_right`
- `text_left_image_right`

Each layout deterministically calculates:

- Position
- Size
- Layer order

---

# Timing

Composition does **not** derive timestamps from transcripts.

Timing is expected to be supplied in future iterations by an Alignment stage through `script_segment_id` mappings.

Sprint 1 therefore treats timing as optional placeholder metadata.

---

# Validation

The Composition models use Pydantic validation to ensure:

- Required fields are present
- Valid layout names
- Valid element roles
- Positive sizes
- Elements remain inside canvas bounds
- Renderer-ready output schema

---

# Consequences

## Advantages

- Lightweight implementation
- Deterministic output
- Easy debugging
- Easy unit testing
- Clear separation between planning and rendering
- Portable scene contract independent of renderer

## Limitations

- Static layouts only
- Manual text wrapping
- Limited layout catalogue
- No animation support during Sprint 1

These limitations are acceptable for the Sprint 1 milestone.

---

# Future Work

Future iterations may introduce:

- Responsive layouts
- Constraint-based positioning
- Automatic collision detection
- Dynamic scaling
- Additional layout templates
- Animation metadata
- Timeline integration
- Integration with a dedicated rendering engine such as Remotion or Manim
