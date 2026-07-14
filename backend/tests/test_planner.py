from unittest.mock import patch

from backend.models.scene import Scene, ScenePlan, VisualElement
from backend.models.script import ScriptSegment, VideoScriptBlueprint
from backend.services import planner


def _fake_script():
    return VideoScriptBlueprint(
        title="T", target_audience="general", estimated_total_duration=15,
        segments=[ScriptSegment(segment_id=1, text="Plants use sunlight to grow.",
                                 visual_cues="sun", duration_seconds=15)],
    )


def _fake_scene_plan():
    return ScenePlan(scenes=[
        Scene(scene_id=1, layout="image_focus", elements=[
            VisualElement(element_id="e1", concept="sunlight", asset_type="image", appear_at_word="sunlight")
        ])
    ])


def test_plan_scenes_returns_scene_plan():
    with patch("backend.services.planner.structured_completion", return_value=_fake_scene_plan()) as mock_call:
        result = planner.plan_scenes(_fake_script())

    mock_call.assert_called_once()
    assert isinstance(result, ScenePlan)
    assert result.scenes[0].scene_id == 1
    assert result.scenes[0].elements[0].asset_type == "image"
