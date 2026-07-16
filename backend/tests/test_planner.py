# backend/tests/test_planner.py
import pytest
import json
from unittest.mock import patch, MagicMock

from app.agents.planner import ScenePlanner
from app.schemas.scene import ScenePlan, Scene, VisualCue, AppearanceTrigger

# Sample input as defined in the PRD / notebook
SAMPLE_SCRIPT = {
    "video_id": "video_api_001",
    "title": "Understanding APIs",
    "total_duration_seconds": 9.2,
    "segments": [
        {"id": "seg_1", "text": "Welcome to our course on APIs.", "visual_cue": "Intro title"},
        {"id": "seg_2", "text": "API stands for Application Programming Interface.", "visual_cue": "Definition"},
    ],
    "word_timestamps": [
        {"word_id": "word_1", "segment_id": "seg_1", "word": "Welcome"},
        {"word_id": "word_2", "segment_id": "seg_1", "word": "course"},
        {"word_id": "word_3", "segment_id": "seg_1", "word": "APIs"},
        {"word_id": "word_4", "segment_id": "seg_2", "word": "API"},
        {"word_id": "word_5", "segment_id": "seg_2", "word": "Application"},
        {"word_id": "word_6", "segment_id": "seg_2", "word": "Programming"},
        {"word_id": "word_7", "segment_id": "seg_2", "word": "Interface"},
    ],
    "assets": [
        {"asset_id": "asset_api_icon", "element_type": "icon", "description": "API icon"},
        {"asset_id": "asset_api_diagram", "element_type": "diagram", "description": "Application communicates with server"},
    ],
}

@pytest.fixture
def planner():
    # Use a dummy API key for testing; we'll mock the LLM calls
    with patch.dict(os.environ, {"GROQ_API_KEY": "test-key"}):
        return ScenePlanner(api_key="test-key", max_retries=1)

def test_plan_scenes_success(planner):
    # Mock the Crew kickoff to return a valid JSON
    mock_output = MagicMock()
    mock_output.raw = json.dumps({
        "schema_version": "1.0",
        "video_id": "video_api_001",
        "title": "Understanding APIs",
        "total_duration_seconds": 9.2,
        "scenes": [
            {
                "scene_id": "scene_1",
                "text": "Welcome to our course on APIs.",
                "script_segment_ids": ["seg_1"],
                "layout_hint": "title_with_center_visual",
                "visual_cues": [
                    {
                        "cue_id": "cue_1",
                        "description": "Course title",
                        "element_type": "text",
                        "content": "Understanding APIs",
                        "asset_id": None,
                        "linked_segment_id": "seg_1",
                        "appearance_trigger": {"type": "segment_start", "word_id": None},
                        "preferred_region": "top",
                        "importance": "primary",
                    },
                    {
                        "cue_id": "cue_2",
                        "description": "API icon",
                        "element_type": "icon",
                        "content": None,
                        "asset_id": "asset_api_icon",
                        "linked_segment_id": "seg_1",
                        "appearance_trigger": {"type": "word", "word_id": "word_3"},
                        "preferred_region": "center",
                        "importance": "primary",
                    },
                ],
            },
            {
                "scene_id": "scene_2",
                "text": "API stands for Application Programming Interface.",
                "script_segment_ids": ["seg_2"],
                "layout_hint": "text_with_diagram",
                "visual_cues": [
                    {
                        "cue_id": "cue_3",
                        "description": "API definition",
                        "element_type": "text",
                        "content": "Application Programming Interface",
                        "asset_id": None,
                        "linked_segment_id": "seg_2",
                        "appearance_trigger": {"type": "word", "word_id": "word_5"},
                        "preferred_region": "top",
                        "importance": "primary",
                    },
                    {
                        "cue_id": "cue_4",
                        "description": "Communication diagram",
                        "element_type": "diagram",
                        "content": None,
                        "asset_id": "asset_api_diagram",
                        "linked_segment_id": "seg_2",
                        "appearance_trigger": {"type": "word", "word_id": "word_4"},
                        "preferred_region": "center",
                        "importance": "primary",
                    },
                ],
            },
        ],
    })

    with patch("app.agents.planner.Crew.kickoff", return_value=mock_output):
        result = planner.plan_scenes(SAMPLE_SCRIPT)

    assert isinstance(result, ScenePlan)
    assert result.video_id == "video_api_001"
    assert len(result.scenes) == 2
    # Check one visual cue
    cue = result.scenes[0].visual_cues[0]
    assert cue.element_type == "text"
    assert cue.appearance_trigger.type == "segment_start"

def test_plan_scenes_retry_on_invalid_json(planner):
    # Simulate two failures: first invalid JSON, then valid
    mock_invalid = MagicMock()
    mock_invalid.raw = "{ invalid json }"
    mock_valid = MagicMock()
    mock_valid.raw = json.dumps({
        "schema_version": "1.0",
        "video_id": "video_api_001",
        "title": "Test",
        "total_duration_seconds": 5.0,
        "scenes": [],
    })

    with patch("app.agents.planner.Crew.kickoff", side_effect=[mock_invalid, mock_valid]):
        result = planner.plan_scenes(SAMPLE_SCRIPT)
    assert isinstance(result, ScenePlan)
    # We only have one retry (max_retries=1), so the second attempt should succeed.

def test_plan_scenes_failure_all_retries(planner):
    # Simulate repeated invalid JSON
    mock_invalid = MagicMock()
    mock_invalid.raw = "{ invalid }"

    with patch("app.agents.planner.Crew.kickoff", return_value=mock_invalid):
        with pytest.raises(RuntimeError, match="Failed to generate valid ScenePlan"):
            planner.plan_scenes(SAMPLE_SCRIPT)