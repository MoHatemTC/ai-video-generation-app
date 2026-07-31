import os
import uuid
import logging
import json
import asyncio
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from typing import List, Dict, Any
from crewai import Agent, Task, Crew
from backend.app.schemas.asset import AssetItem

# Pydantic V2 Migration warnings are expected from CrewAI and can be ignored for now.
logger = logging.getLogger(__name__)

class AssetService:
    def __init__(self):
        self.local_storage_db = "data/supabase_asset_metadata.json"
        os.makedirs(os.path.dirname(self.local_storage_db), exist_ok=True)
        if not os.path.exists(self.local_storage_db):
            with open(self.local_storage_db, "w") as f:
                json.dump([], f)

    def register_asset_in_storage(self, asset: AssetItem, video_id: str) -> str:
        try:
            with open(self.local_storage_db, "r", encoding="utf-8") as f:
                db = json.load(f)
            if not isinstance(db, list):
                db = []
        except Exception:
            db = []

        asset_entry = {
            "video_id": video_id,
            "asset_id": asset.asset_id,
            "scene_id": asset.scene_reference,
            "cue_id": asset.cue_reference,
            "element": asset.element,
            "prompt": asset.prompt,
            "url": asset.url,
            "type": asset.asset_type,
            "source": asset.source,
            "license": asset.asset_license,
            "registered_at": datetime.now(timezone.utc).isoformat()
        }
        db.append(asset_entry)
        
        with open(self.local_storage_db, "w", encoding="utf-8") as f:
            json.dump(db, f, indent=4, ensure_ascii=False)
        return asset.url

    async def resolve_visual_cue(
        self, cue: str, scene_id: str, cue_id: str, asset_id: str, video_id: str, supabase_client: Any = None
    ) -> AssetItem:
        
        # Pull the model string from the .env file, default to openrouter/free
        model_string = os.getenv("OPENROUTER_MODEL", "openrouter/free")

        try:
            # MOVE AGENT CREATION INSIDE TRY/EXCEPT! 
            # If CrewAI crashes due to API keys or Pydantic, the fallback catches it.
            design_director = Agent(
                role="Educational Visual Design Director",
                goal="Refine simple and loose textual visual cues into highly detailed, clean image prompts.",
                backstory="You are an expert visual layout designer at Sprints Video Studio.",
                verbose=False,
                allow_delegation=False,
                llm=model_string  # <--- FIX: Passing string instead of LangChain object
            )

            refinement_task = Task(
                description=f"Refine this cue into an image generator prompt: '{cue}'",
                expected_output="A single optimized prompt string.",
                agent=design_director
            )

            my_crew = Crew(agents=[design_director], tasks=[refinement_task])
            
            loop = asyncio.get_running_loop()
            result = await loop.run_in_executor(None, my_crew.kickoff)
            optimized_prompt = result if isinstance(result, str) else str(result).strip()
            
        except Exception as e:
            logger.warning(f"Asset refinement task failed ({e}). Reverting to raw element fallback.")
            # Fallback gracefully keeps the pipeline alive!
            optimized_prompt = f"Illustration showing: {cue}"

        # Live Pollinations URL
        image_url = f"https://image.pollinations.ai/prompt/{urllib.parse.quote(optimized_prompt)}"

        # If Supabase client is provided, download the pollinations image and upload it to Supabase Storage!
        if supabase_client is not None:
            try:
                req = urllib.request.Request(
                    image_url,
                    headers={'User-Agent': 'Mozilla/5.0'}
                )
                loop = asyncio.get_running_loop()
                def fetch_bytes():
                    with urllib.request.urlopen(req, timeout=15) as response:
                        return response.read()
                
                logger.info(f"Downloading generated image from Pollinations for asset {asset_id}...")
                file_bytes = await loop.run_in_executor(None, fetch_bytes)

                # Store with path format: {video_id}/{asset_id}.png
                storage_key = f"{video_id}/{asset_id}.png"
                logger.info(f"Uploading image to Supabase assets bucket as {storage_key}...")
                
                # Upload to "assets" bucket
                supabase_client.storage.from_("assets").upload(
                    storage_key,
                    file_bytes,
                    {"content-type": "image/png", "upsert": "true"},
                )
                
                # Retrieve the public URL
                public_url_response = supabase_client.storage.from_("assets").get_public_url(storage_key)
                if isinstance(public_url_response, dict):
                    image_url = public_url_response.get("publicUrl") or public_url_response.get("public_url")
                else:
                    image_url = public_url_response
                logger.info(f"Image uploaded successfully! Public URL: {image_url}")
            except Exception as upload_err:
                logger.error(f"Failed to upload image {asset_id} to Supabase. Falling back to direct URL. Error: {upload_err}", exc_info=True)

        final_url = str(image_url or "")

        asset = AssetItem(
            asset_id=asset_id,
            scene_reference=scene_id,
            scene_id=scene_id,
            cue_reference=cue_id,
            cue_id=cue_id,
            asset_type="image",
            url=final_url,
            prompt=optimized_prompt,
            description=optimized_prompt,
            source="generated",
            asset_license="open-source",
            element=cue
        )

        self.register_asset_in_storage(asset, video_id)
        return asset

async def process_scene_elements(scene_data: Dict[str, Any], supabase_client: Any = None) -> Dict[str, Any]:
    video_id = scene_data.get("video_id", "default_video_id")
    scenes = scene_data.get("scenes", [])
    service = AssetService()
    tasks = []
    asset_index = 1

    for scene in scenes:
        scene_id = scene.get("scene_id", "")
        visual_cues = scene.get("visual_cues", scene.get("visual_elements", []))

        for element in visual_cues:
            element_type = element.get("element_type")
            if element_type != "text" or "asset_id" in element:
                fallback_id = f"image_{asset_index}"
                asset_id = element.get("asset_id") or fallback_id
                
                task = service.resolve_visual_cue(
                    cue=element.get("description", element.get("text", "")),
                    scene_id=scene_id,
                    cue_id=element.get("cue_id", ""),
                    asset_id=asset_id,
                    video_id=video_id,
                    supabase_client=supabase_client
                )
                tasks.append(task)
                asset_index += 1
    
    if not tasks:
        return {
            "video_id": video_id,
            "assets": []
        }

    gathered_assets = await asyncio.gather(*tasks)

    resolved_assets = []
    for asset in gathered_assets:
        resolved_assets.append({
            "asset_id": asset.asset_id,
            "scene_id": asset.scene_reference,
            "cue_id": asset.cue_reference,
            "url": asset.url,
            "type": asset.asset_type,
            "license": asset.asset_license,
            "source": asset.source
        })

    return {
        "video_id": video_id,
        "assets": resolved_assets
    }