# Asset Quality and Integration Documentation

This document outlines the criteria for evaluating generated assets and the technical specifications for ensuring compatibility with downstream systems, specifically the Animation Engine.

## 1. Asset Quality Evaluation Criteria

The quality of generated assets is measured against the following four pillars. Each asset should ideally meet all criteria to be considered "production-ready."

### 1.1. Style Consistency
- **Description:** All assets within a single video project must adhere to a consistent and predefined visual style. This ensures a professional and cohesive viewing experience.
- **Criteria:**
    - **Art Style:** Must match the project's designated style (e.g., "flat 2D digital illustration," "minimalist line art," "corporate infographic style").
    - **Color Palette:** Must use a consistent color palette defined for the project.
    - **Composition:** Elements should be composed similarly across assets (e.g., consistent character proportions, lighting direction).

### 1.2. Prompt Adherence
- **Description:** The generated image must be a faithful and accurate representation of the textual cue from the video script.
- **Criteria:**
    - **Object Accuracy:** All key objects and subjects mentioned in the cue must be present.
    - **Action/Context Accuracy:** The scene depicted must match the action or context described in the cue.
    - **Exclusion of Negative Elements:** The asset must not contain elements that were explicitly excluded via negative prompts (e.g., no text, no human figures).

### 1.3. Technical Quality
- **Description:** Assets must meet minimum technical standards to be usable in the video production pipeline.
- **Criteria:**
    - **Resolution:** Minimum resolution of 1920x1080 pixels.
    - **Aspect Ratio:** Must be 16:9 unless otherwise specified.
    - **Artifacts:** Must be free of common AI-generated artifacts (e.g., distorted hands/faces, nonsensical text, blurry areas, watermarks).
    - **File Format:** Must be in PNG format with a transparent background if required.

### 1.4. Brand & Content Appropriateness
- **Description:** All assets must be appropriate for the Sprints brand and the educational context of the videos.
- **Criteria:**
    - **Professionalism:** Assets should be professional and suitable for a corporate/educational audience.
    - **Inclusivity:** Assets should reflect diversity and inclusivity where applicable.
    - **Brand Alignment:** Must not contain elements that contradict Sprints' brand guidelines.

## 2. Prompt Refinement & Fallback Rules

The asset pipeline utilizes CrewAI and an LLM to refine simple script cues into production-ready prompts.
- **Automated Guardrails:** The pipeline checks every generated prompt. It ensures the presence of required style keywords (e.g., `flat 2d`, `illustration`) and strictly filters out forbidden concepts using negative lookbehinds (e.g., `(?<!\bno\s)(?<!\bwithout\s)(?<!\bavoid\s)\bshadows\b`).
- **Resilient Fallback:** If the LLM generates a prompt that fails the quality checks, or if the API connection fails, the system automatically falls back to a deterministic, safe format: `flat 2d illustration, {cue}, no text, no shadows`.

## 3. Animation Engine Integration Contract

**[TODO: Proposed standard pending final confirmation with Youssef]**

This section defines the technical JSON payload contract proposed for compatibility with Youssef's Animation Engine.

### 3.1. Data Schema (`AssetItem`)
The downstream engine expects a flat array of visual assets. Each asset will adhere to the following schema structure:
- `asset_id`: Unique identifier for the asset (e.g., `videoID_sceneX_imgY`).
- `scene_reference`: Identifies which scene the asset belongs to (`scene_id`).
- `cue_reference`: Ties the asset back to the original script cue (`cue_id`).
- `prompt`: The finalized, quality-checked visual description.
- `url`: The fully qualified storage URL where the asset is hosted (e.g., Supabase URL).
- `aspect_ratio`: Defines the framing (Standard is `16:9`).
- `resolution`: Defines the quality (Standard is `1920x1080`).
- `license`: Rights associated with the asset (e.g., `open-source`).

### 3.2. Execution & Testing Instructions

To verify the pipeline logic and test the integration payload generation locally:

**Run the Automated Test Suite:**
```bash
pytest backend/tests/test_assets.py
```

**Execute the Asset Pipeline:**
```bash
# This will process mock cues, run the prompt refinement, and output the finalized JSON to data/supabase_asset_metadata.json
python run_asset_pipeline.py
```