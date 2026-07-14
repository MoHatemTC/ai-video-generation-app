from typing import List, Literal
from pydantic import BaseModel, Field

VisualAssetType = Literal["image", "diagram", "icon", "gif", "svg", "clip"]


class VisualElement(BaseModel):
    element_id: str = Field(..., description="Unique id referenced by the animation stage")
    concept: str = Field(..., description="The concept/keyword this element visualizes")
    asset_type: VisualAssetType = Field(..., description="Preferred asset type for this element")
    appear_at_word: str = Field(
        ..., description="The word/phrase in the narration that triggers this element's entrance"
    )


class Scene(BaseModel):
    scene_id: int = Field(..., description="Matches the source segment_id from the script")
    layout: Literal["title", "bullet_list", "diagram_focus", "image_focus", "split"] = Field(
        ..., description="Slide layout template to use for composition"
    )
    elements: List[VisualElement] = Field(..., description="Visual elements to place in this scene")


class ScenePlan(BaseModel):
    scenes: List[Scene] = Field(..., description="One scene plan entry per script segment")
