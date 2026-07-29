# backend/tests/test_director.py
import pytest
import json
from unittest.mock import AsyncMock, patch, MagicMock
from backend.app.agents.director import SceneDirector
from backend.app.schemas.scene import ScenePlan, SceneQualityReport

SAMPLE_SCRIPT = {
    "video_id": "video_api_001",
    "title": "Understanding APIs",
    "total_duration_seconds": 9.2,
    "segments": [
        {"id": "seg_1", "text": "Welcome to our course on APIs.", "visual_cue": "Intro title"},
    ],
}

scene_plan_mock = ScenePlan(
    schema_version="1.0",
    video_id="video_api_001",
    title="Understanding APIs",
    total_duration_seconds=9.2,
    scenes=[]
)

@pytest.mark.asyncio
async def test_director_evaluate():
    mock_llm_response = {
        "strengths": ["Good coverage", "Clear visuals"],
        "revision_instructions": [
            {
                "instruction_id": "llm_1",
                "severity": "minor",
                "issue_type": "layout_issue",
                "target_path": "scenes[0].layout_hint",
                "operation": "replace",
                "new_value": "centered",
                "reason": "Better alignment",
                "recommendation": "Use centered layout"
            }
        ]
    }

    mock_resp = MagicMock()
    mock_resp.choices = [MagicMock(message=MagicMock(content=json.dumps(mock_llm_response)))]
    with patch("litellm.acompletion", new_callable=AsyncMock) as mock_acompletion:
        mock_acompletion.return_value = mock_resp
        director = SceneDirector(api_key="dummy", base_url="http://fake")
        report = await director.evaluate(SAMPLE_SCRIPT, scene_plan_mock)

        assert isinstance(report, SceneQualityReport)
        assert report.overall_score >= 0
        assert report.passed is not None
        assert len(report.revision_instructions) > 0  # auto + llm
        assert "Good coverage" in report.strengths