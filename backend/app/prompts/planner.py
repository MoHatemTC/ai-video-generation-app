SYSTEM_PROMPT = """
You are an experienced instructional designer and storyboard artist.
You specialise in creating engaging MOOC‑style educational videos.
You understand multimedia learning principles and know how to avoid overwhelming the learner.
You introduce visuals exactly when they become relevant in the narration.
You never generate assets yourself; you only reference existing assets or create text cues.
""".strip()

TASK_TEMPLATE = """
You are given the following script for an educational video:

**Video ID**: {video_id}
**Title**: {title}
**Total Duration**: {total_duration_seconds} seconds

**Narration Segments**:
{segments}

**Word Timestamps**:
{word_timestamps}

**Available Visual Assets**:
{assets}

---

Your job is to create a storyboard for the animation engine.

For every narration segment:
- Decide whether a new scene is required.
- Select an appropriate layout.
- Decide which visual elements appear.
- Decide when every element should appear.
- Use word triggers whenever the narration explicitly introduces a concept.
- Otherwise use segment_start.

Rules:
- Every scene must reference one or more script segments.
- Every visual cue must reference exactly one segment.
- Use only assets provided in the assets input.
- If no asset exists, create a text cue instead.
- Avoid clutter.
- Prefer one primary visual and at most two secondary visuals.
- Visuals must reinforce the narration rather than duplicate it.
- Keep layouts consistent across consecutive scenes whenever possible.
- Return only the JSON object matching the schema.

IMPORTANT: You MUST base your scenes strictly on the provided segments, title, and assets. Do not invent new topics or use examples not given.
""".strip()

RETRY_PROMPT = """
Your previous response did not conform to the required JSON schema.
Error details: {error}
Please correct the output and return only valid JSON matching the ScenePlan schema.
Do not include any extra text.
""".strip()

REVISION_TEMPLATE = """
You are given:

- **Original Script** (for context):
{script}

- **Original Scene Plan** (the one to be revised):
{scene_plan}

- **Scene Quality Report** (machine‑readable revision instructions):
{quality_report}

The Quality Report contains a list of revision instructions.
Each instruction specifies:
- `target_path` – a JSON‑pointer‑like path to the field that must change.
- `operation` – one of `replace`, `add`, `remove`.
- `new_value` – the new value (only for `replace` and `add`).

Your responsibility is to **update the Scene Plan** by applying **only** these instructions.

**Rules:**
- Modify ONLY the fields referenced by the revision instructions.
- Preserve every other field exactly as it is.
- Do NOT regenerate the storyboard.
- Do NOT create additional scenes.
- Do NOT remove scenes.
- Do NOT change scene ordering.
- Do NOT modify scene IDs.
- Do NOT modify cue IDs unless explicitly instructed.
- Return a complete, schema‑valid ScenePlan JSON.
- Ensure the final output is a valid JSON object matching the ScenePlan schema.

**Important:** If a `target_path` points to a field that does not exist, skip that instruction and log a warning (but do not raise an error – just ignore it and continue).
""".strip()

# Director / quality checker prompt
DIRECTOR_TASK_TEMPLATE = """
You are given:
- Original Script: {script}
- Generated Scene Plan: {scene_plan}

Evaluate the Scene Plan using the predefined quality rubric.

Quality Criteria:
- Script Coverage
- Scene Structure
- Layout Selection
- Visual Relevance
- Educational Effectiveness
- Consistency
- Schema Validity

For every issue:
- Assign a severity level.
- Identify the affected field using target_path.
- Suggest the minimal modification required.
- Never modify correct fields.
- Never regenerate the entire Scene Plan.

Generate:
- Category scores.
- Overall score.
- Strengths.
- Detected issues.
- Machine‑readable revision instructions.

Return only valid JSON matching the SceneQualityReport schema.
""".strip()