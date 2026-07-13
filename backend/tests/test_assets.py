import pytest
from backend.app.services.assets.images import AssetService
from backend.app.schemas.asset import AssetResponseContract

@pytest.mark.asyncio
async def test_asset_lane_flow_and_contract():
    """Validates that a sample list of visual elements generates a correct contract payload."""
    service = AssetService()
    mock_scene_id = "scene_abc_123"
    mock_visual_elements = ["Icon of a computer server"]
    
    # Execute the processing slice
    output = await service.process_scene_elements(mock_visual_elements, mock_scene_id)
    
    # Assertions to guarantee validation success
    assert isinstance(output, AssetResponseContract)
    assert len(output.assets) == 1
    assert output.assets[0].element == "Icon of a computer server"
    assert "supabase" in output.assets[0].url
    assert output.assets[0].license == "open-source"