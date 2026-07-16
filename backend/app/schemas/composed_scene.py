"""Pydantic contracts for the composition stage.

The input models mirror the Scene Planner, Alignment and Asset Service JSON
contracts.  ``CompositionOutput`` is the only payload emitted to the renderer.
"""

from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class StrictModel(BaseModel):
    """Reject fields outside the agreed pipeline contract."""

    model_config = ConfigDict(extra="forbid")


class LayoutName(str, Enum):
    TITLE_SLIDE = "title_slide"
    IMAGE_LEFT_TEXT_RIGHT = "image_left_text_right"
    TEXT_LEFT_IMAGE_RIGHT = "text_left_image_right"


class ElementType(str, Enum):
    TEXT = "text"
    IMAGE = "image"
    ICON = "icon"
    DIAGRAM = "diagram"
    GIF = "gif"
    CLIP = "clip"
    SVG = "svg"
    SHAPE = "shape"
    CHART = "chart"


class Region(str, Enum):
    LEFT = "left"
    RIGHT = "right"
    CENTER = "center"
    TOP = "top"
    BOTTOM = "bottom"


class Importance(str, Enum):
    PRIMARY = "primary"
    SECONDARY = "secondary"


class AppearanceTrigger(StrictModel):
    type: Literal["segment_start", "word"]
    word_id: str | None = None

    @model_validator(mode="after")
    def validate_word_reference(self) -> "AppearanceTrigger":
        if self.type == "word" and not self.word_id:
            raise ValueError("A word trigger requires word_id.")
        if self.type == "segment_start" and self.word_id is not None:
            raise ValueError("A segment_start trigger must not contain word_id.")
        return self


class VisualElement(StrictModel):
    cue_id: str = Field(min_length=1)
    description: str = Field(min_length=1)
    element_type: ElementType
    content: str | None = None
    asset_id: str | None = None
    linked_segment_id: str = Field(min_length=1)
    appearance_trigger: AppearanceTrigger
    preferred_region: Region
    importance: Importance

    @model_validator(mode="after")
    def validate_element_source(self) -> "VisualElement":
        if self.element_type == ElementType.TEXT:
            if not self.content:
                raise ValueError("A text element requires content.")
            if self.asset_id is not None:
                raise ValueError("A text element cannot reference asset_id.")
        elif not self.asset_id:
            raise ValueError("A visual element requires asset_id.")
        return self


class PlannerScene(StrictModel):
    scene_id: str = Field(min_length=1)
    layout: LayoutName
    script_segments: list[str] = Field(min_length=1)
    visual_elements: list[VisualElement] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_references(self) -> "PlannerScene":
        if len(self.script_segments) != len(set(self.script_segments)):
            raise ValueError("script_segments must not contain duplicates.")
        cue_ids = [element.cue_id for element in self.visual_elements]
        if len(cue_ids) != len(set(cue_ids)):
            raise ValueError("cue_id values must be unique within a scene.")
        unknown_segments = {
            element.linked_segment_id
            for element in self.visual_elements
            if element.linked_segment_id not in self.script_segments
        }
        if unknown_segments:
            raise ValueError(f"Unknown linked segment IDs: {sorted(unknown_segments)}")
        return self


class ScenePlanDocument(StrictModel):
    video_id: str = Field(min_length=1)
    scenes: list[PlannerScene] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_scene_ids(self) -> "ScenePlanDocument":
        scene_ids = [scene.scene_id for scene in self.scenes]
        if len(scene_ids) != len(set(scene_ids)):
            raise ValueError("scene_id values must be unique.")
        return self


class AssetRecord(StrictModel):
    asset_id: str = Field(min_length=1)
    scene_id: str = Field(min_length=1)
    cue_id: str = Field(min_length=1)
    url: str = Field(min_length=1)
    type: ElementType
    license: str | None = None
    source: str | None = None


class AssetCollection(StrictModel):
    video_id: str = Field(min_length=1)
    assets: list[AssetRecord] = Field(default_factory=list)


class SegmentTimestamp(StrictModel):
    segment_id: str = Field(min_length=1)
    start: float = Field(ge=0)
    end: float = Field(gt=0)

    @model_validator(mode="after")
    def validate_range(self) -> "SegmentTimestamp":
        if self.end <= self.start:
            raise ValueError("A segment end must be after its start.")
        return self


class WordTimestamp(StrictModel):
    word_id: str = Field(min_length=1)
    segment_id: str = Field(min_length=1)
    word: str = Field(min_length=1)
    start: float = Field(ge=0)
    end: float = Field(gt=0)

    @model_validator(mode="after")
    def validate_range(self) -> "WordTimestamp":
        if self.end <= self.start:
            raise ValueError("A word end must be after its start.")
        return self


class AlignmentData(StrictModel):
    video_id: str = Field(min_length=1)
    segment_timestamps: list[SegmentTimestamp] = Field(min_length=1)
    word_timestamps: list[WordTimestamp] = Field(default_factory=list)


class Canvas(StrictModel):
    width: int = Field(default=1920, gt=0)
    height: int = Field(default=1080, gt=0)
    background_color: str = "#FFFFFF"


class Position(StrictModel):
    x: float = Field(ge=0)
    y: float = Field(ge=0)


class Size(StrictModel):
    width: float = Field(gt=0)
    height: float = Field(gt=0)


class ComposedElement(StrictModel):
    cue_id: str = Field(min_length=1)
    element_type: ElementType
    content: str | None = None
    asset_id: str | None = None
    asset_url: str | None = None
    position: Position
    size: Size
    layer: int = Field(ge=0)
    linked_segment_id: str = Field(min_length=1)
    start: float = Field(ge=0)
    end: float = Field(gt=0)

    @model_validator(mode="after")
    def validate_output_source_and_timing(self) -> "ComposedElement":
        if self.end <= self.start:
            raise ValueError("An element end must be after its start.")
        if self.element_type == ElementType.TEXT:
            if not self.content or self.asset_id is not None or self.asset_url is not None:
                raise ValueError("A composed text element must contain only text content.")
        elif not self.asset_id or not self.asset_url:
            raise ValueError("A composed visual element requires asset_id and asset_url.")
        return self


class ComposedScene(StrictModel):
    scene_id: str = Field(min_length=1)
    layout: LayoutName
    canvas: Canvas
    script_segments: list[str] = Field(min_length=1)
    start: float = Field(ge=0)
    end: float = Field(gt=0)
    elements: list[ComposedElement] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_scene_bounds(self) -> "ComposedScene":
        if self.end <= self.start:
            raise ValueError("A scene end must be after its start.")
        for element in self.elements:
            if not self.start <= element.start < element.end <= self.end:
                raise ValueError(f"Cue '{element.cue_id}' is outside the scene timeline.")
            if element.position.x + element.size.width > self.canvas.width:
                raise ValueError(f"Cue '{element.cue_id}' exceeds the canvas width.")
            if element.position.y + element.size.height > self.canvas.height:
                raise ValueError(f"Cue '{element.cue_id}' exceeds the canvas height.")
        return self


class ComposedLayout(StrictModel):
    scenes: list[ComposedScene] = Field(min_length=1)


class CompositionOutput(StrictModel):
    video_id: str = Field(min_length=1)
    composed_layout: ComposedLayout
