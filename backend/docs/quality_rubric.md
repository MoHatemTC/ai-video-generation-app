# Quality Rubric – Scene Plan Evaluation

This document explains the weighting and threshold logic used in the `QualityRubric` configuration.

## Overall Criteria & Weightings

| Dimension | Weight | Rationale |
| :--- | :--- | :--- |
| **Script Coverage** | 20% | Ensures every spoken segment has a corresponding visual scene. If a segment is missing, the learner loses the visual aid, hurting comprehension. This is the most critical dimension. |
| **Visual Relevance** | 20% | Validates that every visual cue actually has content (either an asset reference or inline text). Empty cues are useless and break the animation engine. |
| **Scene Structure** | 15% | Checks that scenes have IDs, text, and a layout hint. These are mandatory fields for rendering. Whitespace-only values cause downstream failures. |
| **Educational Effectiveness** | 15% | Ensures that scenes are not purely audio – they should contain at least one visual to reinforce the narration. |
| **Layout Selection** | 15% | Encourages variety in layouts without being chaotic. Scoring increases with diverse layouts but caps at 100 to prevent over-penalization. |
| **Consistency** | 10% | Penalizes frequent layout changes between consecutive scenes, which can distract or confuse the learner (cognitive load). |
| **Schema Validity** | 5% | Catches missing or whitespace-only required fields. Low weight because Pydantic already validates types, but we catch edge cases like `""` or `"   "`. |

## Pass Thresholds

- **Overall Score ≥ 70**: The plan is acceptable for production.
- **Category Score ≥ 60**: No single dimension should fail completely. A score below 60 indicates a critical gap (e.g., missing a whole segment or having zero visual cues) that must be fixed before production.

## Scoring Guards

All scores are **capped between 0 and 100** to prevent negative values from over-penalization.  
The `validate_scene_plan` function uses `.strip()` checks to treat whitespace-only strings as missing data, ensuring robustness against malformed LLM outputs.