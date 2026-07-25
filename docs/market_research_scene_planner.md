# Competitor E‑Learning Video Style Analysis

## Overview
To inform our Scene Planner design, I analysed the visual styles of major e‑learning platforms: Coursera, Udemy, Khan Academy, and edX. The goal was to identify design patterns that enhance learning retention and engagement.

## Key Observations

### 1. Text & Title Overlays
- **Coursera / edX**: Use minimal text overlays, often with a large course title at the beginning and key terms highlighted later.
- **Khan Academy**: Relies heavily on a "talking head" style with on‑screen text appearing as the instructor speaks, often as bullet points or definitions.
- **Udemy**: Frequently uses text overlays that animate in sync with spoken words, especially for definitions and step‑by‑step instructions.

**Takeaway**: Text cues should appear exactly when the narrator mentions a concept (word‑level triggers) to reinforce learning without distraction.

### 2. Diagrams & Icons
- All platforms use diagrams to illustrate processes (e.g., API communication, system architecture).
- Icons are used to represent abstract ideas (e.g., a gear for settings, a cloud for cloud computing) and appear at the same time as the spoken term.

**Takeaway**: Our VisualCue schema with `asset_id` and `element_type` supports both diagrams and icons, and appearance triggers should allow both segment‑start and word‑based triggers.

### 3. Layout Consistency
- Consecutive scenes often maintain a consistent layout (e.g., title top‑left, diagram centre‑right) to reduce cognitive load.
- Transitions are smooth; visuals change only when the topic shifts.

**Takeaway**: The planner should prefer consistent layouts (e.g., same `layout_hint` for sequential scenes) unless a major topic change warrants a new layout.

### 4. Use of Animated GIFs / Short Clips
- Some advanced courses use short GIFs or video clips to demonstrate dynamic processes (e.g., code execution).
- These are typically triggered at segment start and remain visible throughout the segment.

**Takeaway**: Our schema supports `gif` and `video` types, and the trigger can be `segment_start` to keep them persistent.

### 5. Visual Clutter Avoidance
- Effective videos limit on‑screen text to 3–5 lines and use at most 2–3 visual elements per scene.
- Primary visuals are larger and more prominent; secondary visuals are smaller and placed in corners.

**Takeaway**: The planner’s rule to prefer one primary and at most two secondary visuals aligns with industry best practices.

## Design Principles to Adopt
1. **Synchronisation**: Visuals must appear exactly when the narration introduces the concept (word‑level triggers).
2. **Reinforcement, not duplication**: Visuals should complement the narration, not just repeat the spoken text.
3. **Progressive disclosure**: Show new information step‑by‑step; avoid showing all visuals at once.
4. **Consistent styling**: Use uniform layout patterns across scenes for predictability.

## Conclusion
Our Scene Planner agent should generate scenes that follow these patterns, ensuring our videos are as effective as (or better than) current market leaders. The Pydantic schema already supports all required elements; we only need to enforce these heuristics in the LLM prompt.