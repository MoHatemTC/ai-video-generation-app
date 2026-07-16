import os
import uuid
import logging
import json
import asyncio
from datetime import datetime, timezone
from typing import List, Dict, Any
from crewai import Agent, Task, Crew, LLM

# Standard import matching your backend package structure
from app.schemas.asset import AssetItem

logger = logging.getLogger(__name__)

class AssetService:
    def __init__(self):
        self.gemini_api_key = os.getenv("GEMINI_API_KEY", "")
        self.local_storage_db = "data/supabase_asset_metadata.json"
        os.makedirs(os.path.dirname(self.local_storage_db), exist_ok=True)
        if not os.path.exists(self.local_storage_db):
            with open(self.local_storage_db, "w") as f:
                json.dump([], f)

    def _get_llm_client(self) -> LLM:
        return LLM(model="gemini/gemini-1.5-flash", api_key=self.gemini_api_key)

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
        self, cue: str, scene_id: str, cue_id: str, asset_id: str, video_id: str
    ) -> AssetItem:
        llm_client = self._get_llm_client()

        design_director = Agent(
            role="Educational Visual Design Director",
            goal="Refine simple and loose textual visual cues into highly detailed, clean image prompts.",
            backstory="You are an expert visual layout designer at Sprints Video Studio.",
            verbose=False,
            allow_delegation=False,
            llm=llm_client
        )

        refinement_task = Task(
            description=f"Refine this cue into an image generator prompt: '{cue}'",
            expected_output="A single optimized prompt string.",
            agent=design_director
        )

        my_crew = Crew(agents=[design_director], tasks=[refinement_task])

        try:
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(None, my_crew.kickoff)
            optimized_prompt = result.raw.strip() if hasattr(result, "raw") else str(result).strip()
        except Exception as e:
            logger.error(f"Asset refinement task failed ({e}). Reverting to raw element fallback.")
            optimized_prompt = f"Illustration showing: {cue}"

        asset = AssetItem(
            asset_id=asset_id,
            scene_reference=scene_id,
            cue_reference=cue_id,
            asset_type="image",
            url=f"https://supabase-storage.local/assets/{uuid.uuid4()}.png",
            prompt=optimized_prompt,
            source="generated",
            asset_license="open-source",
            element=cue
        )

        self.register_asset_in_storage(asset, video_id)
        return asset

async def process_scene_elements(scene_data: Dict[str, Any]) -> Dict[str, Any]:
    video_id = scene_data.get("video_id", "default_video_id")
    scenes = scene_data.get("scenes", [])
    service = AssetService()
    resolved_assets = []
    asset_index = 1

    for scene in scenes:
        scene_id = scene.get("scene_id", "")
        visual_elements = scene.get("visual_elements", [])

        for element in visual_elements:
            if element.get("element_type") == "image" or "asset_id" in element:
                fallback_id = f"image_{asset_index}"
                asset_id = element.get("asset_id") or fallback_id
                
                asset = await service.resolve_visual_cue(
                    cue=element.get("description", element.get("text", "")),
                    scene_id=scene_id,
                    cue_id=element.get("cue_id", ""),
                    asset_id=asset_id,
                    video_id=video_id
                )
                asset_index += 1

                # Explicitly map the internal schema attributes to the aliases Nada's output expects
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