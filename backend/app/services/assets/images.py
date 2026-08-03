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

def _get_refinement_llm():
    """Build a valid CrewAI LLM instance matching the application configuration."""
    api_key = os.getenv("LITELLM_API_KEY") or os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    litellm_base = os.getenv("LITELLM_BASE_URL", "https://learner-os.sprints.ai/litellm/v1")
    if api_key and not api_key.startswith("your_") and "key_here" not in api_key:
        os.environ["OPENAI_API_KEY"] = api_key
        os.environ["OPENAI_API_BASE"] = litellm_base
        from backend.app.config.model_config import format_model_for_litellm_proxy
        raw_model = os.getenv("MODEL_NAME", "gemini/gemini-2.0-flash")
        model_name = format_model_for_litellm_proxy(raw_model)
        try:
            from crewai import LLM
            return LLM(model=model_name, api_key=api_key, base_url=litellm_base, temperature=0.2)
        except Exception:
            pass

    openrouter_key = os.getenv("OPENROUTER_API_KEY")
    if openrouter_key and not openrouter_key.startswith("your_"):
        openrouter_base = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
        openrouter_model = os.getenv("OPENROUTER_MODEL", "openrouter/free")
        try:
            from crewai import LLM
            return LLM(model=openrouter_model, api_key=openrouter_key, base_url=openrouter_base, temperature=0.2)
        except Exception:
            pass
    return None


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
        llm = _get_refinement_llm()
        if llm:
            try:
                design_director = Agent(
                    role="Educational Visual Design Director",
                    goal="Refine simple and loose textual visual cues into highly detailed, clean image prompts.",
                    backstory="You are an expert visual layout designer at Sprints Video Studio.",
                    verbose=False,
                    allow_delegation=False,
                    llm=llm
                )

                refinement_task = Task(
                    description=f"Refine this cue into an image generator prompt: '{cue}'",
                    expected_output="A single optimized prompt string.",
                    agent=design_director
                )

                my_crew = Crew(agents=[design_director], tasks=[refinement_task])
                
                loop = asyncio.get_running_loop()
                result = await loop.run_in_executor(None, my_crew.kickoff)
                optimized_prompt = str(getattr(result, "raw", result)).strip()
                
            except Exception as e:
                logger.warning(f"Asset refinement task failed ({e}). Reverting to raw element fallback.")
                optimized_prompt = f"Illustration showing: {cue}"
        else:
            optimized_prompt = f"Illustration showing: {cue}"

        # Live Pollinations URL
        image_url = f"https://image.pollinations.ai/prompt/{urllib.parse.quote(optimized_prompt)}"

        # If Supabase client is provided, download the pollinations image and upload it to Supabase Storage!
        if supabase_client is not None:
            try:
                loop = asyncio.get_running_loop()
                file_bytes = None
                max_retries = 3

                for attempt in range(max_retries):
                    try:
                        req = urllib.request.Request(
                            image_url,
                            headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
                        )
                        def fetch_bytes():
                            with urllib.request.urlopen(req, timeout=12) as response:
                                return response.read()
                        
                        logger.info(f"Downloading generated image from Pollinations for asset {asset_id} (attempt {attempt + 1})...")
                        file_bytes = await loop.run_in_executor(None, fetch_bytes)
                        break
                    except Exception as http_err:
                        err_str = str(http_err)
                        if ("429" in err_str or "timed out" in err_str) and attempt < max_retries - 1:
                            wait_time = (attempt + 1) * 3
                            logger.warning(f"Rate limited / timed out downloading {asset_id} from Pollinations. Retrying in {wait_time}s...")
                            await asyncio.sleep(wait_time)
                        else:
                            logger.warning(f"Pollinations download skipped for {asset_id}: {http_err}")
                            break

                if file_bytes:
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
                logger.warning(f"Failed to upload image {asset_id} to Supabase. Falling back to direct URL. Error: {upload_err}")

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

    # Semaphore to avoid bursting 15+ concurrent requests to Pollinations/LLM (HTTP 429 prevention)
    semaphore = asyncio.Semaphore(2)

    async def sem_resolve(cue: str, scene_id: str, cue_id: str, asset_id: str):
        async with semaphore:
            return await service.resolve_visual_cue(
                cue=cue,
                scene_id=scene_id,
                cue_id=cue_id,
                asset_id=asset_id,
                video_id=video_id,
                supabase_client=supabase_client
            )

    for scene in scenes:
        scene_id = scene.get("scene_id", "")
        cues_or_elements = scene.get("visual_cues") or scene.get("visual_elements") or []

        for element in cues_or_elements:
            element_type = element.get("element_type")
            if element_type != "text" or "asset_id" in element:
                fallback_id = f"image_{asset_index}"
                asset_id = element.get("asset_id") or fallback_id
                
                task = sem_resolve(
                    cue=element.get("description", element.get("text", "")),
                    scene_id=scene_id,
                    cue_id=element.get("cue_id", ""),
                    asset_id=asset_id
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