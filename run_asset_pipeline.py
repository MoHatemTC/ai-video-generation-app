import asyncio
import json
from backend.app.services.assets.images import AssetService
from dotenv import load_dotenv

load_dotenv()

async def main():
    service = AssetService()
    
    # 3 distinct educational visual cues representing different asset needs
    visual_cues = [
        {
            "cue": "a friendly robot waving hello",
            "scene_id": "scene_1",
            "cue_id": "cue_101",
            "asset_id": "asset_img_01"
        },
        {
            "cue": "flowchart showing data moving from a client laptop to a cloud server",
            "scene_id": "scene_2",
            "cue_id": "cue_102",
            "asset_id": "asset_img_02"
        },
        {
            "cue": "a bright glowing lightbulb symbolizing an innovative idea",
            "scene_id": "scene_3",
            "cue_id": "cue_103",
            "asset_id": "asset_img_03"
        }
    ]
    
    video_id = "sprint_2_demo_video"

    print("🚀 Processing visual cues through AssetService pipeline...\n")
    for item in visual_cues:
        print(f"Processing cue: '{item['cue']}'...")
        asset = await service.resolve_visual_cue(
            cue=item["cue"],
            scene_id=item["scene_id"],
            cue_id=item["cue_id"],
            asset_id=item["asset_id"],
            video_id=video_id
        )
        print(f"✅ Generated Prompt: {asset.prompt}\n")

    print("🎉 Pipeline run complete! Outputs saved to data/supabase_asset_metadata.json")

if __name__ == "__main__":
    # This is the crucial change: It clears the file before writing new data.
    output_file = "data/supabase_asset_metadata.json"
    with open(output_file, "w") as f:
        json.dump([], f)
        
    # Now, run the main function which will append to the now-empty file
    # (Note: The AssetService itself appends, so we clear it here first)
    asyncio.run(main())