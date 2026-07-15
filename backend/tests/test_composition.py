from pathlib import Path

import pytest

from backend.app.schemas.composed_scene import ComposedScene
from backend.app.services.composition import CompositionService


def create_image_left_text_right_plan() -> dict:
    """Return realistic dummy input from the Scene Planner."""

    return {
        "scene_id": "scene_1",
        "layout": "image_left_text_right",
        "script_segment_ids": ["seg_1"],
        "elements": [
            {
                "element_id": "title_1",
                "element_type": "text",
                "role": "title",
                "text": "How RAG Works",
            },
            {
                "element_id": "diagram_1",
                "element_type": "diagram",
                "role": "main_visual",
                "asset_url": "assets/rag_diagram.svg",
                "alt_text": "RAG retrieval and generation diagram",
            },
            {
                "element_id": "body_1",
                "element_type": "text",
                "role": "body",
                "text": (
                    "1. Retrieve trusted context\n"
                    "2. Add context to the prompt\n"
                    "3. Generate a grounded answer"
                ),
            },
        ],
        "timing": [
            {
                "script_segment_id": "seg_1",
                "start_time_seconds": 0.0,
                "end_time_seconds": 6.0,
            }
        ],
    }


def test_image_left_text_right_layout() -> None:
    service = CompositionService()
    result = service.compose_scene(
        create_image_left_text_right_plan()
    )

    assert isinstance(result, ComposedScene)
    assert result.scene_id == "scene_1"
    assert result.canvas.width == 1920
    assert result.canvas.height == 1080
    assert len(result.elements) == 3

    title = next(
        element for element in result.elements
        if element.role.value == "title"
    )
    image = next(
        element for element in result.elements
        if element.role.value == "main_visual"
    )
    body = next(
        element for element in result.elements
        if element.role.value == "body"
    )

    assert title.position.y < image.position.y
    assert image.position.x < body.position.x
    assert image.position.x + image.size.width <= result.canvas.width
    assert body.position.x + body.size.width <= result.canvas.width
    assert result.start_time_seconds == 0.0
    assert result.end_time_seconds == 6.0


def test_text_left_image_right_layout() -> None:
    scene_plan = create_image_left_text_right_plan()
    scene_plan["layout"] = "text_left_image_right"

    result = CompositionService().compose_scene(scene_plan)

    image = next(
        element for element in result.elements
        if element.role.value == "main_visual"
    )
    body = next(
        element for element in result.elements
        if element.role.value == "body"
    )

    assert body.position.x < image.position.x


def test_title_slide_layout() -> None:
    scene_plan = {
        "scene_id": "scene_title",
        "layout": "title_slide",
        "elements": [
            {
                "element_id": "title_1",
                "element_type": "text",
                "role": "title",
                "text": "Understanding APIs",
            },
            {
                "element_id": "icon_1",
                "element_type": "icon",
                "role": "main_visual",
                "asset_url": "assets/server.svg",
                "alt_text": "Computer server icon",
            },
        ],
    }

    result = CompositionService().compose_scene(scene_plan)

    visual = next(
        element for element in result.elements
        if element.role.value == "main_visual"
    )
    visual_center = visual.position.x + (visual.size.width / 2)

    assert visual_center == pytest.approx(result.canvas.width / 2)


def test_missing_main_visual_raises_error() -> None:
    scene_plan = create_image_left_text_right_plan()
    scene_plan["elements"] = [
        element
        for element in scene_plan["elements"]
        if element["role"] != "main_visual"
    ]

    with pytest.raises(ValueError, match="main_visual"):
        CompositionService().compose_scene(scene_plan)


def test_duplicate_title_role_raises_error() -> None:
    scene_plan = create_image_left_text_right_plan()
    scene_plan["elements"].append(
        {
            "element_id": "title_2",
            "element_type": "text",
            "role": "title",
            "text": "Duplicate title",
        }
    )

    with pytest.raises(ValueError, match="exactly one 'title'"):
        CompositionService().compose_scene(scene_plan)


def test_svg_preview_is_created(tmp_path: Path) -> None:
    service = CompositionService()
    result = service.compose_scene(
        create_image_left_text_right_plan()
    )

    preview_path = service.save_svg(
        result,
        tmp_path / "composition_preview.svg",
    )

    assert preview_path.exists()
    preview = preview_path.read_text(encoding="utf-8")
    assert "<svg" in preview
    assert "How RAG Works" in preview
    assert "RAG retrieval and generation diagram" in preview
