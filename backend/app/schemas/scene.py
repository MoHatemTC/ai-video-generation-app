from typing import List, Optional, Literal, Any
from pydantic import BaseModel

class AppearanceTrigger(BaseModel):
    type: Literal["segment_start", "segment_end", "word"]
    word_id: Optional[str] = None

class VisualCue(BaseModel):
    cue_id: str
    description: str
    element_type: Literal["text", "image", "diagram", "icon", "gif", "video", "svg"]
    content: Optional[str] = None
    asset_id: Optional[str] = None
    linked_segment_id: str
    appearance_trigger: AppearanceTrigger
    preferred_region: Literal["top", "bottom", "left", "right", "center", "background"]
    importance: Literal["primary", "secondary"]

class Scene(BaseModel):
    scene_id: str
    text: str
    script_segment_ids: List[str]
    layout_hint: str
    visual_cues: List[VisualCue]

class ScenePlan(BaseModel):
    schema_version: str = "1.0"
    video_id: str
    title: str
    total_duration_seconds: float
    scenes: List[Scene]

# ---------- Quality Report Schemas ----------
class RevisionInstruction(BaseModel):
    instruction_id: str
    severity: Literal["critical", "major", "minor"]
    issue_type: Literal[
        "missing_scene", "missing_segment", "layout_issue",
        "visual_issue", "consistency_issue", "schema_issue", "educational_issue"
    ]
    target_path: str
    operation: Literal["replace", "add", "remove"]
    new_value: Optional[Any] = None
    reason: str
    recommendation: str

class CategoryScores(BaseModel):
    script_coverage: int
    scene_structure: int
    layout_selection: int
    visual_relevance: int
    educational_effectiveness: int
    consistency: int
    schema_validity: int

class SceneQualityReport(BaseModel):
    overall_score: int
    passed: bool
    category_scores: CategoryScores
    strengths: List[str]
    detected_issues: List[str]
    revision_instructions: List[RevisionInstruction]