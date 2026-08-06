import pytest
import sys
import os

# This is a workaround to fix the ModuleNotFoundError.
# It adds the project's root directory to the Python path
# so that the test runner can find the 'backend' module.
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from backend.app.services.assets.images import AssetService
from backend.app.schemas.asset import AssetItem

@pytest.mark.asyncio
async def test_svg_writer_agent_produces_valid_svg():
    """
    Tests that the AssetService, using the new SVG Writer Agent,
    can generate a valid SVG asset from a simple visual cue.
    """
    # 1. Initialize the AssetService
    asset_service = AssetService()

    # 2. Define a test case
    cue = "a friendly robot waving hello"
    scene_id = "scene_01"
    cue_id = "cue_01"
    asset_id = "asset_01"
    video_id = "video_01"

    # 3. Call the resolver to generate the SVG asset
    # We pass supabase_client=None as we are not testing the upload logic
    generated_asset = await asset_service.resolve_visual_cue(
        cue=cue,
        scene_id=scene_id,
        cue_id=cue_id,
        asset_id=asset_id,
        video_id=video_id,
        supabase_client=None
    )

    # 4. Assert the results
    assert isinstance(generated_asset, AssetItem), "The service should return an AssetItem"
    assert generated_asset.asset_type == "svg", "The asset type should be 'svg'"
    assert generated_asset.resolution == "vector", "The resolution should be 'vector'"
    
    # The generated SVG code is stored in the 'prompt' field
    svg_code = generated_asset.prompt
    assert svg_code is not None, "The SVG code should not be null"
    assert svg_code.strip().startswith("<svg"), "The output should start with an <svg> tag"
    assert svg_code.strip().endswith("</svg>"), "The output should end with an </svg> tag"
    assert "LLM not available" not in svg_code, "The LLM should be available and used"
    assert "SVG generation failed" not in svg_code, "The SVG generation should not fail"