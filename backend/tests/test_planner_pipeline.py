# backend/tests/test_pipeline.py
import pytest
import json
from unittest.mock import AsyncMock, patch, MagicMock

from app.agents.planner import ScenePlanner
from app.agents.director import SceneDirector
from app.schemas.scene import ScenePlan, SceneQualityReport

# Sample input (same as before)
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

@pytest.mark.asyncio
async def test_full_pipeline():
    # Mock the responses from Crew (the kickoff_async calls)
    # We'll patch the crew creation and the litellm calls inside the agents.

    # 1. Planner returns a valid ScenePlan
    mock_plan = {
        "schema_version": "1.0",
        "video_id": "video_api_001",
        "title": "Understanding APIs",
        "total_duration_seconds": 9.2,
        "scenes": [
            {
                "scene_id": "scene_1",
                "text": "Welcome to our course on APIs.",
                "script_segment_ids": ["seg_1"],
                "layout_hint": "centered",
                "visual_cues": [
                    {
                        "cue_id": "cue_1",
                        "description": "Course title",
                        "element_type": "text",
                        "content": "Understanding APIs",
                        "asset_id": None,
                        "linked_segment_id": "seg_1",
                        "appearance_trigger": {"type": "segment_start", "word_id": None},
                        "preferred_region": "center",
                        "importance": "primary",
                    }
                ],
            }
        ],
    }

    # 2. Director returns a SceneQualityReport with one revision instruction
    mock_report = {
        "overall_score": 85,
        "passed": True,
        "category_scores": {
            "script_coverage": 90,
            "scene_structure": 80,
            "layout_selection": 85,
            "visual_relevance": 90,
            "educational_effectiveness": 85,
            "consistency": 80,
            "schema_validity": 100,
        },
        "strengths": ["Good coverage", "Clear layout"],
        "detected_issues": ["Visual cue could be more prominent"],
        "revision_instructions": [
            {
                "instruction_id": "rev_1",
                "severity": "minor",
                "issue_type": "visual_issue",
                "target_path": "scenes[0].visual_cues[0].preferred_region",
                "operation": "replace",
                "new_value": "top",
                "reason": "Center is less visible",
                "recommendation": "Move title to top",
            }
        ],
    }

    # 3. Planner.revise_scenes returns the updated plan
    mock_revised = mock_plan.copy()
    mock_revised["scenes"][0]["visual_cues"][0]["preferred_region"] = "top"

    # Patch the Crew.kickoff_async method for both planner and director
    # We'll patch the Crew class itself to return a custom result
    with patch("crewai.Crew.kickoff_async", new_callable=AsyncMock) as mock_kickoff:
        # First call (planner) -> returns mock_plan
        # Second call (director) -> returns mock_report
        # Third call (revision) -> returns mock_revised
        mock_kickoff.side_effect = [
            MagicMock(raw=json.dumps(mock_plan)),
            MagicMock(raw=json.dumps(mock_report)),
            MagicMock(raw=json.dumps(mock_revised)),
        ]

        planner = ScenePlanner(api_key="dummy", base_url="http://fake")
        director = SceneDirector(api_key="dummy", base_url="http://fake")

        # Run pipeline
        scene_plan = await planner.plan_scenes(SAMPLE_SCRIPT)
        quality_report = await director.evaluate(SAMPLE_SCRIPT, scene_plan)
        revised_plan = await planner.revise_scenes(SAMPLE_SCRIPT, scene_plan, quality_report)

        # Assertions
        assert isinstance(scene_plan, ScenePlan)
        assert scene_plan.video_id == "video_api_001"
        assert quality_report.passed is True
        assert len(quality_report.revision_instructions) == 1
        assert revised_plan.scenes[0].visual_cues[0].preferred_region == "top"