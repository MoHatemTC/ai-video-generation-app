import asyncio
import json
import os
from dotenv import load_dotenv

load_dotenv()
os.environ.setdefault("ASSET_REMOTE_LLM_ENABLED", "0")

from backend.app.services.assets.images import AssetService

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
    generated_assets = []
    for item in visual_cues:
        print(f"Processing cue: '{item['cue']}'...")
        asset = await service.resolve_visual_cue(
            cue=item["cue"],
            scene_id=item["scene_id"],
            cue_id=item["cue_id"],
            asset_id=item["asset_id"],
            video_id=video_id
        )
        generated_assets.append(asset)
        print(f"✅ Generated Prompt: {asset.prompt}\n")

    print(
        f"🎉 Pipeline run complete! Generated {len(generated_assets)} assets and saved them to "
        "data/supabase_asset_metadata.json"
    )

if __name__ == "__main__":
    # This is the crucial change: It clears the file before writing new data.
    output_file = "data/supabase_asset_metadata.json"
    with open(output_file, "w") as f:
        json.dump([], f)
        
    # Now, run the main function which will append to the now-empty file
    # (Note: The AssetService itself appends, so we clear it here first)
    asyncio.run(main())