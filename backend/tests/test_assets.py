import pytest
from unittest.mock import patch, MagicMock
from app.services.assets.images import process_scene_elements

pytestmark = pytest.mark.asyncio(loop_scope="function")

@pytest.mark.asyncio
@patch("app.services.assets.images.Crew.kickoff")
async def test_process_scene_elements_success(mock_kickoff):
    mock_result = MagicMock()
    mock_result.raw = "An ultra-detailed digital illustration."
    mock_kickoff.return_value = mock_result

    mock_scene_data = {
        "video_id": "video_test_123",
        "scenes": [
            {
                "scene_id": "scene_1",
                "visual_elements": [{"cue_id": "cue_1", "description": "Test", "asset_id": "image_1"}]
            }
        ]
    }

    result = await process_scene_elements(mock_scene_data)
    
    # Assert metadata aliases map correctly
    assert result["video_id"] == "video_test_123"
    assert len(result["assets"]) == 1
    assert result["assets"][0]["scene_id"] == "scene_1"

@pytest.mark.asyncio
@patch("app.services.assets.images.Crew.kickoff")
async def test_process_scene_elements_fallback_on_failure(mock_kickoff):
    mock_kickoff.side_effect = Exception("Mock LLM error")
    mock_scene_data = {
        "video_id": "video_test_fallback",
        "scenes": [{"scene_id": "scene_2", "visual_elements": [{"cue_id": "cue_2", "asset_id": "image_2"}]}]
    }

    result = await process_scene_elements(mock_scene_data)
    assert result["assets"][0]["asset_id"] == "image_2"