
import asyncio
from backend.app.services.assets.images import AssetService

async def main():
    """
    This script performs a live test of the AssetService to verify that it can
    successfully connect to the LiteLLM API and refine a visual cue.
    """
    print("--- Starting Live AssetService Test ---")
    
    # Initialize the service, which will load credentials from the .env file
    service = AssetService()
    
    # A sample visual cue to test with
    test_cue = "a robot learning about space"
    
    print(f"Attempting to resolve visual cue: '{test_cue}'")
    
    try:
        # We call the resolve_visual_cue method directly.
        # We can use dummy IDs for this test as they are not used by the LLM part.
        resolved_asset = await service.resolve_visual_cue(
            cue=test_cue,
            scene_id="live_test_scene",
            cue_id="live_test_cue",
            asset_id="live_test_asset",
            video_id="live_test_video"
        )
        
        print("\n--- Test Result ---")
        print("Successfully received response from LiteLLM.")
        print(f"Original Cue: {resolved_asset.element}")
        print(f"Refined Prompt: {resolved_asset.prompt}")
        print("-------------------")
        
        # Check if the prompt quality evaluation passed
        if service._evaluate_prompt_quality(resolved_asset.prompt):
            print("✅ SUCCESS: The generated prompt passed the automated quality check.")
        else:
            print("⚠️ WARNING: The generated prompt did not pass the automated quality check.")

    except Exception as e:
        print("\n--- Test FAILED ---")
        print(f"An error occurred during the live test: {e}")
        print("Please check your .env file, network connection, and the LiteLLM service status.")
        print("-------------------")

if __name__ == "__main__":
    asyncio.run(main())