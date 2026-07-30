# backend/app/validators/scene_validator.py

from typing import Dict, Any, List, Tuple
from ..schemas.scene import ScenePlan, CategoryScores, RevisionInstruction
from ..config.quality import QualityRubric

def _cap_score(score: float) -> int:
    """Ensure score is between 0 and 100, rounded."""
    return int(round(min(100.0, max(0.0, score))))

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
    segment_ids = {str(seg.get("segment_id", seg.get("id"))) for seg in script.get("segments", [])}
    referenced_ids = set()
    for scene in scene_plan.scenes:
        referenced_ids.update(scene.script_segment_ids)
    
    missing = segment_ids - referenced_ids
    coverage_score = (len(referenced_ids) / len(segment_ids)) * 100 if segment_ids else 100
    coverage_score = _cap_score(coverage_score)

    # --- 2. Scene Structure ---
    structure_issues = 0
    for scene in scene_plan.scenes:
        # Catch whitespace-only strings
        if not scene.scene_id or not scene.scene_id.strip():
            structure_issues += 1
        if not scene.text or not scene.text.strip():
            structure_issues += 1
        if not scene.layout_hint or not scene.layout_hint.strip():
            structure_issues += 1
        # Catch empty lists
        if len(scene.script_segment_ids) == 0:
            structure_issues += 1
    structure_score = _cap_score(100 - structure_issues * 10)

    # --- 3. Layout Selection ---
    layouts = [s.layout_hint for s in scene_plan.scenes]
    if not layouts:
        layout_score = 0
    else:
        unique = len(set(layouts))
        # Cap at 100
        layout_score = _cap_score((unique / len(layouts)) * 100 if len(layouts) > 1 else 100)

    # --- 4. Visual Relevance ---
    total_cues = sum(len(s.visual_cues) for s in scene_plan.scenes)
    if total_cues == 0:
        visual_score = 0
    else:
        valid = 0
        for scene in scene_plan.scenes:
            for cue in scene.visual_cues:
                # Check for whitespace-only or missing IDs/descriptions
                if not cue.cue_id or not cue.cue_id.strip():
                    continue
                if not cue.description or not cue.description.strip():
                    continue
                # Asset/content must exist and not be whitespace-only if it's a text cue
                asset_ok = (
                    cue.asset_id is not None and cue.asset_id.strip() != ""
                ) or (
                    cue.content is not None and cue.content.strip() != ""
                )
                if asset_ok:
                    valid += 1
        visual_score = _cap_score((valid / total_cues) * 100)

    # --- 5. Educational Effectiveness ---
    scenes_with_visuals = sum(1 for s in scene_plan.scenes if s.visual_cues)
    edu_score = _cap_score(
        (scenes_with_visuals / len(scene_plan.scenes)) * 100 if scene_plan.scenes else 0
    )

    # --- 6. Consistency ---
    if len(layouts) <= 1:
        cons_score = 100
    else:
        changes = sum(1 for i in range(1, len(layouts)) if layouts[i] != layouts[i-1])
        cons_score = _cap_score(100 - changes * 20)

    # --- 7. Schema Validity ---
    schema_issues = 0
    for scene in scene_plan.scenes:
        if not scene.scene_id or not scene.scene_id.strip():
            schema_issues += 1
        if not scene.text or not scene.text.strip():
            schema_issues += 1
        for cue in scene.visual_cues:
            if not cue.cue_id or not cue.cue_id.strip():
                schema_issues += 1
            if not cue.description or not cue.description.strip():
                schema_issues += 1
            if not cue.linked_segment_id or not cue.linked_segment_id.strip():
                schema_issues += 1
    schema_score = _cap_score(100 - schema_issues * 15)

    # Build CategoryScores (already capped)
    scores = CategoryScores(
        script_coverage=coverage_score,
        scene_structure=structure_score,
        layout_selection=layout_score,
        visual_relevance=visual_score,
        educational_effectiveness=edu_score,
        consistency=cons_score,
        schema_validity=schema_score,
    )

    # --- Generate Revision Instructions for detected issues ---
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
            reason=f"{structure_issues} structural issues (whitespace or empty fields)",
            recommendation="Ensure each scene has non-empty id, text, layout_hint, and at least one segment"
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
            reason="Some visual cues lack asset/content or have empty IDs/descriptions",
            recommendation="Provide asset_id or content for all cues, ensure IDs and descriptions are non-empty"
        )
        instructions.append(instr)
        detected_issues.append("Some visual cues have missing or whitespace-only fields")

    if schema_issues > 0:
        instr = RevisionInstruction(
            instruction_id="auto_schema_issues",
            severity="major",
            issue_type="schema_issue",
            target_path="scenes",
            operation="replace",
            new_value=None,
            reason=f"{schema_issues} schema issues (missing or whitespace-only fields)",
            recommendation="Ensure all required fields are filled with non-whitespace values"
        )
        instructions.append(instr)
        detected_issues.append(f"{schema_issues} schema issues")

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