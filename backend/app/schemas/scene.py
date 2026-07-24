# backend/app/schemas/scene.py
from pydantic import BaseModel, Field
from typing import List, Optional, Literal


class AppearanceTrigger(BaseModel):
    """Defines when a visual cue appears in the narration."""

    type: Literal["segment_start", "segment_end", "word"]
    word_id: Optional[str] = None


class VisualCue(BaseModel):
    """A single visual element to be rendered on screen."""

    cue_id: str
    description: str
    element_type: Literal["text", "image", "diagram", "icon", "gif", "video", "svg"]
    content: Optional[str] = None  # inline text if element_type == "text"
    asset_id: Optional[str] = None  # reference to external asset
    linked_segment_id: str  # must match a script segment id
    appearance_trigger: AppearanceTrigger
    preferred_region: Literal["top", "bottom", "left", "right", "center", "background"]
    importance: Literal["primary", "secondary"]
    trigger_time_seconds: float


class Scene(BaseModel):
    """A storyboard scene grouping one or more script segments and their visuals."""

    scene_id: str
    text: str  # narration text for this scene
    subtitle: Optional[str] = None  # subtitle text for video bar
    hold_ms: Optional[int] = 5000  # delay in ms for fallback / transition timing
    script_segment_ids: List[str]  # one or more segment ids
    layout_hint: str  # free‑form hint for the animation engine
    visual_cues: List[VisualCue]


class ScenePlan(BaseModel):
    """Top‑level output contract for the Scene Planner."""

    schema_version: str = "1.0"
    video_id: str
    title: str
    total_duration_seconds: float
    scenes: List[Scene]
