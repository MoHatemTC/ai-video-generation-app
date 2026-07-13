from backend.app.services.composition import CompositionService
import pytest
def test_compose_service()->None:
    """test the CompositionService function"""

    scene_plan={
        "scene_id":"scene_1",
        "layout":"title_slide",
        "elements":[
            {
                "element_id":"title_1",
                "element_type":"text",
                "position":{"x":100,"y":50},
                "size":{"width":800,"height":200},
                "text":"Undertsand RAG Systems"
            }
        ],
    }

    service=CompositionService()

    result=service.compose_scene(scene_plan=scene_plan)

    assert result.scene_id == "scene_1"
    assert result.layout == "title_slide"
    assert len(result.elements) == 1
    assert result.elements[0].text == "Undertsand RAG Systems"



def test_compose_service_raises_error_when_scene_id_is_missing() -> None:
    """Test that an invalid scene plan is rejected."""

    invalid_scene_plan = {
        "layout": "title_slide",
        "elements": [],
    }

    service = CompositionService()

    with pytest.raises(ValueError):
        service.compose_scene(scene_plan=invalid_scene_plan)
        

def test_compose_service_raises_error_for_negative_position() -> None:
    """Test that a negative position is rejected."""

    invalid_scene_plan = {
        "scene_id": "scene_1",
        "layout": "title_slide",
        "elements": [
            {
                "element_id": "title_1",
                "element_type": "text",
                "position": {"x": -10, "y": 50},
                "size": {"width": 800, "height": 200},
                "text": "Understand RAG Systems",
            }
        ],
    }

    service = CompositionService()

    with pytest.raises(ValueError):
        service.compose_scene(scene_plan=invalid_scene_plan)