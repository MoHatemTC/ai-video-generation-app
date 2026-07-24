import pytest
from unittest.mock import patch, AsyncMock
from backend.app.services.assets.images import process_scene_elements, AssetService
from backend.app.schemas.asset import AssetItem

@pytest.mark.asyncio
@patch('backend.app.services.assets.images.AssetService')
async def test_process_scene_elements_success(MockAssetService):
    """
    Test that process_scene_elements correctly calls the asset service,
    processes the results, and handles success.
    This test now mocks the entire AssetService to isolate the test
    to just the process_scene_elements function's logic.
    """
    # 1. Configure the mock AssetService instance
    mock_service_instance = MockAssetService.return_value

    # 2. Create a mock asset object that our mock service will return.
    # This simulates a successful response from the service.
    mock_asset = AssetItem(
        asset_id="image_1",
        scene_reference="scene_1",
        cue_reference="cue_1",
        asset_type="image",
        url="http://fake.url/image.png",
        prompt="An ultra-detailed digital illustration.",
        source="generated",
        asset_license="open-source",
        element="A cat sitting on a mat"
    )
    
    # 3. Configure the mock's method to be an awaitable async function
    # that returns our predefined mock asset.
    mock_service_instance.resolve_visual_cue = AsyncMock(return_value=mock_asset)

    # 4. Define the input data for the function we are testing
    mock_scene_data = {
        "video_id": "video_test_123",
        "scenes": [
            {
                "scene_id": "scene_1",
                "visual_elements": [{"cue_id": "cue_1", "description": "A cat sitting on a mat", "asset_id": "image_1"}]
            }
        ]
    }

    # 5. Call the function under test
    result = await process_scene_elements(mock_scene_data)

    # 6. Assertions to verify behavior
    # Was the AssetService class instantiated?
    MockAssetService.assert_called_once()
    
    # Was the resolve_visual_cue method called with the correct arguments?
    mock_service_instance.resolve_visual_cue.assert_awaited_once_with(
        cue="A cat sitting on a mat",
        scene_id="scene_1",
        cue_id="cue_1",
        asset_id="image_1",
        video_id="video_test_123"
    )

    # Is the final result structured correctly based on the mock asset?
    assert result["video_id"] == "video_test_123"
    assert len(result["assets"]) == 1
    assert result["assets"][0]["asset_id"] == "image_1"
    assert result["assets"][0]["url"] == "http://fake.url/image.png"


@pytest.mark.asyncio
@patch('backend.app.services.assets.images.AssetService')
async def test_process_scene_elements_handles_no_elements(MockAssetService):
    """
    Test that the function handles cases with no visual elements gracefully
    and doesn't attempt to process anything.
    """
    # Get the mock instance that will be created
    mock_service_instance = MockAssetService.return_value
    
    mock_scene_data = {
        "video_id": "video_test_no_elements",
        "scenes": [
            {
                "scene_id": "scene_1",
                "visual_elements": [] # NOTE: This is empty
            }
        ]
    }

    result = await process_scene_elements(mock_scene_data)

    # Assert that the service's resolve method was NOT called
    mock_service_instance.resolve_visual_cue.assert_not_called()

    # Assert that the result is an empty list of assets
    assert result["video_id"] == "video_test_no_elements"
    assert len(result["assets"]) == 0


class TestAssetServiceQualityEvaluation:
    """
    Unit tests for the internal _evaluate_prompt_quality method of AssetService.
    These tests are synchronous and do not require mocking.
    """
    def setup_method(self):
        """
        Create an instance of the AssetService before each test.
        """
        self.service = AssetService()

    def test_evaluate_prompt_quality_good_prompt_with_negation(self):
        """
        Test that a high-quality prompt with negative constraints (e.g., "no shadow") passes.
        """
        good_prompt = "A flat 2d illustration of a robot, centered, clean lines, no shadow, no text."
        assert self.service._evaluate_prompt_quality(good_prompt) is True

    def test_evaluate_prompt_quality_with_forbidden_keyword(self):
        """
        Test that a prompt containing a forbidden keyword (e.g., 'photorealistic') fails.
        """
        bad_prompt = "A photorealistic illustration of a robot."
        assert self.service._evaluate_prompt_quality(bad_prompt) is False

    def test_evaluate_prompt_quality_missing_required_keyword(self):
        """
        Test that a prompt missing a required style keyword (e.g., 'illustration') fails.
        """
        bad_prompt = "A flat 2d drawing of a robot."
        assert self.service._evaluate_prompt_quality(bad_prompt) is False
        
    def test_evaluate_prompt_quality_with_standalone_forbidden_keyword(self):
        """
        Test that a prompt with a standalone forbidden keyword fails, even if a negative constraint is present.
        """
        bad_prompt = "A flat 2d illustration of a robot with text, but no shadow."
        assert self.service._evaluate_prompt_quality(bad_prompt) is False

    def test_evaluate_prompt_quality_with_blurry_keyword(self):
        """
        Test that a prompt containing the forbidden keyword 'blurry' fails.
        """
        bad_prompt = "A flat 2d illustration of a robot, blurry background."
        assert self.service._evaluate_prompt_quality(bad_prompt) is False

    def test_evaluate_prompt_quality_with_low_resolution_keyword(self):
        """
        Test that a prompt containing the forbidden keyword 'low-resolution' fails.
        """
        bad_prompt = "A flat 2d illustration of a robot, low-resolution."
        assert self.service._evaluate_prompt_quality(bad_prompt) is False

@pytest.mark.asyncio
async def test_resolve_visual_cue_fallback_on_quality_fail():
    """
    Test that resolve_visual_cue reverts to a safe, basic prompt
    when the LLM-refined prompt fails the quality check.
    """
    # 1. Instantiate the service
    service = AssetService()
    
    # 2. Define the input cue
    test_cue = "a robot learning"
    
    # 3. Patch the Crew.kickoff method to return a low-quality prompt
    with patch('backend.app.services.assets.images.Crew.kickoff') as mock_kickoff:
        # This prompt will fail the quality check because it contains "photorealistic"
        # and is missing "illustration".
        mock_kickoff.return_value = "a photorealistic photo of a robot learning"
        
        # 4. Call the method under test
        result_asset = await service.resolve_visual_cue(
            cue=test_cue,
            scene_id="test_scene",
            cue_id="test_cue",
            asset_id="test_asset",
            video_id="test_video"
        )
        
        # 5. Assertions: The service should have reverted to the basic fallback prompt.
        expected_fallback_prompt = f"flat 2d illustration, {test_cue}, no text, no shadows"
        assert result_asset.prompt == expected_fallback_prompt
        assert result_asset.prompt_used == expected_fallback_prompt