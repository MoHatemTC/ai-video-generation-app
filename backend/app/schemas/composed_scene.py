from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, model_validator


class StrictModel(BaseModel):
    """Base model that rejects unexpected input fields."""

    model_config = ConfigDict(extra="forbid")


class LayoutName(str, Enum):
    """Layouts supported during Sprint 1."""

    TITLE_SLIDE = "title_slide"
    IMAGE_LEFT_TEXT_RIGHT = "image_left_text_right"
    TEXT_LEFT_IMAGE_RIGHT = "text_left_image_right"


class ElementType(str, Enum):
    """Element types understood by composition and rendering."""

    TEXT = "text"
    IMAGE = "image"
    ICON = "icon"
    DIAGRAM = "diagram"
    SVG = "svg"


class ElementRole(str, Enum):
    """Semantic roles used by the layout rules."""

    TITLE = "title"
    BODY = "body"
    MAIN_VISUAL = "main_visual"


class TimingReference(StrictModel):
    """Optional timing already mapped to a script segment."""

    script_segment_id: str = Field(min_length=1)
    start_time_seconds: float | None = Field(default=None, ge=0)
    end_time_seconds: float | None = Field(default=None, gt=0)

    @model_validator(mode="after")
    def validate_time_range(self) -> "TimingReference":
        if (
            self.start_time_seconds is not None
            and self.end_time_seconds is not None
            and self.end_time_seconds <= self.start_time_seconds
        ):
            raise ValueError(
                "end_time_seconds must be greater than start_time_seconds."
            )
        return self


class PlannedElement(StrictModel):
    """High-level element requested by the Scene Planner."""

    element_id: str = Field(min_length=1)
    element_type: ElementType
    role: ElementRole
    text: str | None = None
    asset_url: str | None = None
    alt_text: str | None = None

    @model_validator(mode="after")
    def validate_content_source(self) -> "PlannedElement":
        if self.element_type == ElementType.TEXT:
            if not self.text:
                raise ValueError("Text elements require text.")
            if self.asset_url is not None:
                raise ValueError("Text elements cannot reference asset_url.")
        elif not self.asset_url:
            raise ValueError(
                f"{self.element_type.value} elements require asset_url."
            )
        return self


class ScenePlan(StrictModel):
    """Typed high-level input received from the Scene Planner."""

    scene_id: str = Field(min_length=1)
    layout: LayoutName
    script_segment_ids: list[str] = Field(default_factory=list)
    elements: list[PlannedElement] = Field(min_length=1)
    timing: list[TimingReference] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_scene_plan(self) -> "ScenePlan":
        element_ids = [element.element_id for element in self.elements]
        if len(element_ids) != len(set(element_ids)):
            raise ValueError("element_id values must be unique.")

        timing_ids = {item.script_segment_id for item in self.timing}
        unknown_ids = timing_ids - set(self.script_segment_ids)
        if unknown_ids:
            raise ValueError(
                "Timing references unknown script segments: "
                f"{sorted(unknown_ids)}"
            )
        return self


class Canvas(StrictModel):
    """Static slide canvas."""

    width: int = Field(default=1920, gt=0)
    height: int = Field(default=1080, gt=0)
    background_color: str = "#FFFFFF"


class Position(StrictModel):
    """Top-left position in pixels."""

    x: float = Field(ge=0)
    y: float = Field(ge=0)


class Size(StrictModel):
    """Element dimensions in pixels."""

    width: float = Field(gt=0)
    height: float = Field(gt=0)


class ComposedElement(StrictModel):
    """Exact renderer-ready representation of one scene element."""

    element_id: str = Field(min_length=1)
    element_type: ElementType
    role: ElementRole
    position: Position
    size: Size
    layer: int = Field(ge=0)
    text: str | None = None
    asset_url: str | None = None
    alt_text: str | None = None
    script_segment_ids: list[str] = Field(default_factory=list)
    start_time_seconds: float | None = Field(default=None, ge=0)
    end_time_seconds: float | None = Field(default=None, gt=0)

    @model_validator(mode="after")
    def validate_composed_element(self) -> "ComposedElement":
        if self.element_type == ElementType.TEXT:
            if not self.text:
                raise ValueError("Composed text elements require text.")
            if self.asset_url is not None:
                raise ValueError(
                    "Composed text elements cannot reference asset_url."
                )
        elif not self.asset_url:
            raise ValueError(
                f"Composed {self.element_type.value} elements require "
                "asset_url."
            )

        if (
            self.start_time_seconds is not None
            and self.end_time_seconds is not None
            and self.end_time_seconds <= self.start_time_seconds
        ):
            raise ValueError(
                "Element end_time_seconds must be greater than start time."
            )
        return self


class ComposedScene(StrictModel):
    """Final static scene contract consumed by animation/rendering."""

    scene_id: str = Field(min_length=1)
    layout: LayoutName
    canvas: Canvas = Field(default_factory=Canvas)
    script_segment_ids: list[str] = Field(default_factory=list)
    elements: list[ComposedElement] = Field(min_length=1)
    start_time_seconds: float | None = Field(default=None, ge=0)
    end_time_seconds: float | None = Field(default=None, gt=0)

    @model_validator(mode="after")
    def validate_scene(self) -> "ComposedScene":
        element_ids = [element.element_id for element in self.elements]
        if len(element_ids) != len(set(element_ids)):
            raise ValueError(
                "Composed element_id values must be unique."
            )

        for element in self.elements:
            if (
                element.position.x + element.size.width
                > self.canvas.width
            ):
                raise ValueError(
                    f"Element '{element.element_id}' exceeds canvas width."
                )
            if (
                element.position.y + element.size.height
                > self.canvas.height
            ):
                raise ValueError(
                    f"Element '{element.element_id}' exceeds canvas height."
                )

        if (
            self.start_time_seconds is not None
            and self.end_time_seconds is not None
            and self.end_time_seconds <= self.start_time_seconds
        ):
            raise ValueError(
                "Scene end_time_seconds must be greater than start time."
            )
        return self
