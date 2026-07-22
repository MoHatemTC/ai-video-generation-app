# backend/tests/test_director.py
import pytest
import json
from unittest.mock import AsyncMock, patch, MagicMock
from app.agents.director import SceneDirector
from app.schemas.scene import ScenePlan, SceneQualityReport

# ... sample script and plan ...

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

    with patch("crewai.Crew.kickoff_async", new_callable=AsyncMock) as mock_kickoff:
        mock_kickoff.return_value = MagicMock(raw=json.dumps(mock_llm_response))
        director = SceneDirector(api_key="dummy", base_url="http://fake")
        report = await director.evaluate(SAMPLE_SCRIPT, scene_plan_mock)

        assert isinstance(report, SceneQualityReport)
        assert report.overall_score >= 0
        assert report.passed is not None
        assert len(report.revision_instructions) > 0  # auto + llm
        assert "Good coverage" in report.strengths