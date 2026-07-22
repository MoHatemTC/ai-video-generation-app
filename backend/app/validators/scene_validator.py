from typing import Dict, Any, List, Tuple
from ..schemas.scene import ScenePlan, CategoryScores, RevisionInstruction
from ..config.quality import QualityRubric

def validate_scene_plan(
    script: Dict[str, Any],
    scene_plan: ScenePlan,
    rubric: QualityRubric
) -> Tuple[CategoryScores, List[RevisionInstruction], List[str]]:
    """
    Run all code-level checks on the ScenePlan.
    Returns:
        - CategoryScores (0-100 each)
        - List of RevisionInstructions (for detected issues)
        - List of detected issue strings (for the report)
    """
    # --- 1. Script Coverage ---
    segment_ids = {seg["id"] for seg in script.get("segments", [])}
    referenced_ids = set()
    for scene in scene_plan.scenes:
        referenced_ids.update(scene.script_segment_ids)
    missing = segment_ids - referenced_ids
    coverage_score = (len(referenced_ids) / len(segment_ids)) * 100 if segment_ids else 100

    # --- 2. Scene Structure ---
    structure_issues = 0
    for scene in scene_plan.scenes:
        if not scene.scene_id or not scene.text or not scene.layout_hint:
            structure_issues += 1
        if len(scene.script_segment_ids) == 0:
            structure_issues += 1
    structure_score = max(0, 100 - structure_issues * 10)

    # --- 3. Layout Selection ---
    layouts = [s.layout_hint for s in scene_plan.scenes]
    if not layouts:
        layout_score = 0
    else:
        unique = len(set(layouts))
        layout_score = min(100, (unique / len(layouts)) * 100) if len(layouts) > 1 else 100

    # --- 4. Visual Relevance ---
    total_cues = sum(len(s.visual_cues) for s in scene_plan.scenes)
    if total_cues == 0:
        visual_score = 0
    else:
        valid = 0
        for scene in scene_plan.scenes:
            for cue in scene.visual_cues:
                asset_ok = cue.asset_id is not None or cue.content is not None
                if cue.linked_segment_id not in segment_ids:
                    # issue but still count as valid? we'll track separately.
                    pass
                if not asset_ok:
                    # invalid
                    pass
                else:
                    valid += 1
        visual_score = (valid / total_cues) * 100

    # --- 5. Educational Effectiveness ---
    scenes_with_visuals = sum(1 for s in scene_plan.scenes if s.visual_cues)
    edu_score = (scenes_with_visuals / len(scene_plan.scenes)) * 100 if scene_plan.scenes else 0

    # --- 6. Consistency ---
    if len(layouts) <= 1:
        cons_score = 100
    else:
        changes = sum(1 for i in range(1, len(layouts)) if layouts[i] != layouts[i-1])
        cons_score = max(0, 100 - changes * 20)

    # --- 7. Schema Validity ---
    schema_issues = 0
    for scene in scene_plan.scenes:
        if not scene.scene_id or not scene.text:
            schema_issues += 1
        for cue in scene.visual_cues:
            if not cue.cue_id or not cue.description:
                schema_issues += 1
    schema_score = max(0, 100 - schema_issues * 15)

    # Build CategoryScores
    scores = CategoryScores(
        script_coverage=round(coverage_score),
        scene_structure=round(structure_score),
        layout_selection=round(layout_score),
        visual_relevance=round(visual_score),
        educational_effectiveness=round(edu_score),
        consistency=round(cons_score),
        schema_validity=round(schema_score),
    )

    # Generate revision instructions for detected issues
    instructions = []
    detected_issues = []

    if missing:
        instr = RevisionInstruction(
            instruction_id="auto_missing_segments",
            severity="critical",
            issue_type="missing_segment",
            target_path="scenes",
            operation="add",
            new_value=None,
            reason=f"Missing segments: {missing}",
            recommendation="Add scenes for the missing segments"
        )
        instructions.append(instr)
        detected_issues.append(f"Missing segments: {missing}")

    if structure_issues > 0:
        instr = RevisionInstruction(
            instruction_id="auto_structure_issues",
            severity="major",
            issue_type="scene_structure",
            target_path="scenes",
            operation="replace",
            new_value=None,
            reason=f"{structure_issues} structural issues found",
            recommendation="Ensure each scene has id, text, and layout_hint"
        )
        instructions.append(instr)
        detected_issues.append(f"{structure_issues} structural issues")

    if visual_score < 100:
        instr = RevisionInstruction(
            instruction_id="auto_visual_issues",
            severity="minor",
            issue_type="visual_issue",
            target_path="visual_cues",
            operation="replace",
            new_value=None,
            reason="Some visual cues lack asset or content",
            recommendation="Provide asset_id or content for all cues"
        )
        instructions.append(instr)
        detected_issues.append("Some visual cues have no asset or content")

    if schema_issues > 0:
        instr = RevisionInstruction(
            instruction_id="auto_schema_issues",
            severity="major",
            issue_type="schema_issue",
            target_path="scenes",
            operation="replace",
            new_value=None,
            reason=f"{schema_issues} schema issues (missing fields)",
            recommendation="Ensure all required fields are filled"
        )
        instructions.append(instr)
        detected_issues.append(f"{schema_issues} schema issues")

    # Add additional generic consistency issue if layout changes too often
    if cons_score < 80:
        instr = RevisionInstruction(
            instruction_id="auto_consistency",
            severity="minor",
            issue_type="consistency_issue",
            target_path="scenes[*].layout_hint",
            operation="replace",
            new_value=None,
            reason="Layouts change too frequently",
            recommendation="Keep layouts consistent across consecutive scenes"
        )
        instructions.append(instr)
        detected_issues.append("Layouts change too frequently")

    return scores, instructions, detected_issues