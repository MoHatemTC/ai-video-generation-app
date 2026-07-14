from unittest.mock import patch

from backend.models.script import ScriptSegment, VideoScriptBlueprint
from backend.services import transcript


def _fake_blueprint():
    return VideoScriptBlueprint(
        title="Intro to Photosynthesis",
        target_audience="general",
        estimated_total_duration=30,
        segments=[
            ScriptSegment(segment_id=1, text="Plants convert sunlight into energy.",
                          visual_cues="show a sun icon", duration_seconds=15),
            ScriptSegment(segment_id=2, text="This process is called photosynthesis.",
                          visual_cues="show a leaf diagram", duration_seconds=15),
        ],
    )


def test_script_schema_has_expected_fields():
    assert "segments" in VideoScriptBlueprint.model_fields
    assert "estimated_total_duration" in VideoScriptBlueprint.model_fields


def test_generate_segmented_script_calls_ai_client_and_returns_blueprint():
    with patch("backend.services.transcript.structured_completion", return_value=_fake_blueprint()) as mock_call:
        result = transcript.generate_segmented_script(
            instruction="I want a video about photosynthesis",
            tone="professional",
            audience="general",
            length_minutes=1.0,
        )

    mock_call.assert_called_once()
    assert isinstance(result, VideoScriptBlueprint)
    assert len(result.segments) == 2
    assert result.segments[0].segment_id == 1


def test_generate_segmented_script_propagates_missing_api_key_error():
    from backend.services.ai_client import AIConfigError

    with patch("backend.services.transcript.structured_completion", side_effect=AIConfigError("no key")):
        try:
            transcript.generate_segmented_script("topic", "professional", "general", 1.0)
            assert False, "expected AIConfigError to propagate"
        except AIConfigError:
            pass
