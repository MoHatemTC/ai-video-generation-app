import os
import uuid
import logging
import json
import asyncio
import re
from datetime import datetime, timezone
from typing import List, Dict, Any
from dotenv import load_dotenv
from crewai import Agent, Task, Crew, LLM
from backend.app.schemas.asset import AssetItem

# Pydantic V2 Migration warnings are expected from CrewAI and can be ignored for now.
# The UserWarning about 'model_name' is also from a dependency and not a blocker.

logger = logging.getLogger(__name__)

load_dotenv()

# --- Quality Evaluation Constants ---
REQUIRED_STYLE_KEYWORDS = ["flat 2d", "illustration"]
FORBIDDEN_PROMPT_KEYWORDS = ["text", "gradients", "shadows", "watermarks", "3d", "photo", "photorealistic", "blurry", "low-resolution"]
# ---

class AssetService:
    def __init__(self):
        self.gemini_api_key = os.getenv("GEMINI_API_KEY", "")
        self.local_storage_db = "data/supabase_asset_metadata.json"
        os.makedirs(os.path.dirname(self.local_storage_db), exist_ok=True)
        if not os.path.exists(self.local_storage_db):
            with open(self.local_storage_db, "w") as f:
                json.dump([], f)

    def _get_llm_client(self):
        try:
            api_key = os.getenv("LITELLM_API_KEY")
            api_base = os.getenv("LITELLM_API_BASE") or os.getenv("LITELLM_BASE_URL")
            model_name = (
                os.getenv("LITELLM_MODEL")
                or os.getenv("DEFAULT_MODEL")
                or "kimi-k2.5"
            )
            if api_key and api_base:
                return LLM(
                    model=model_name,
                    api_key=api_key,
                    base_url=api_base,
                )
        except (ImportError, ValueError) as e:
            logger.warning(f"LiteLLM client unavailable ({e}). Trying other providers.")

        # Try Google Gemini via langchain connector if available and gemini key is set
        try:
            if self.gemini_api_key:
                from langchain_google_genai import ChatGoogleGenerativeAI
                return ChatGoogleGenerativeAI(model="gemini-1.5-flash", api_key=self.gemini_api_key)
        except Exception as e:
            logger.warning(f"langchain_google_genai not available ({e}).")

        # Final fallback to a lightweight fake LLM to keep CrewAI operable in tests/CI
        try:
            from langchain_community.llms.fake import FakeListLLM
            return FakeListLLM(responses=["A detailed, vibrant illustration of the cue."])
        except Exception:
            logger.warning("No external LLM connectors found. Falling back to CrewAI local fake LLM.")
            return LLM(model="openai/fake", api_key="fake")

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
            "registered_at": datetime.now(timezone.utc).isoformat(),
            "prompt_used": asset.prompt_used,
            "resolution": asset.resolution,
            "aspect_ratio": asset.aspect_ratio
        }
        db.append(asset_entry)
        
        with open(self.local_storage_db, "w", encoding="utf-8") as f:
            json.dump(db, f, indent=4, ensure_ascii=False)
        return asset.url

    def _build_prompt_template(self, cue: str) -> str:
        """Builds a standardized prompt template by loading it from an external file."""
        try:
            template_path = os.path.join(os.path.dirname(__file__), "visual_prompt_template.md")
            with open(template_path, 'r', encoding='utf-8') as f:
                template = f.read()
        except FileNotFoundError:
            logger.error("Visual prompt template file not found. Using hardcoded fallback.")
            template = """
You are a visual design expert for an educational video studio. Your task is to refine a simple visual cue into a detailed, production-ready image generation prompt.
**Quality Criteria to Enforce:**
- **Style:** Flat 2D digital illustration. Clean lines, solid colors, minimalist and professional.
- **Composition:** The main subject should be centered and clear. Avoid background clutter.
- **Negative Prompts:** The final image should NOT include any of the following: {negative_prompts}.
**Original Cue:**
"{cue}"
Based on the original cue, generate a single, optimized prompt string that strictly adheres to all quality criteria. The output must be only the prompt string itself.
"""

        negative_prompts = ", ".join(FORBIDDEN_PROMPT_KEYWORDS)
        return template.format(negative_prompts=negative_prompts, cue=cue)

    async def resolve_visual_cue(
        self, cue: str, scene_id: str, cue_id: str, asset_id: str, video_id: str
    ) -> AssetItem:
        if os.getenv("ASSET_REMOTE_LLM_ENABLED", "1").lower() in {"0", "false", "no"}:
            optimized_prompt = self._build_fallback_prompt(cue)
        else:
            llm_client = self._get_llm_client()

            design_director = Agent(
                role="Educational Visual Design Director",
                goal="Refine simple and loose textual visual cues into highly detailed, clean image prompts.",
                backstory="You are an expert visual layout designer at Sprints Video Studio.",
                verbose=False,
                allow_delegation=False,
                llm=llm_client
            )

            prompt_template = self._build_prompt_template(cue)

            refinement_task = Task(
                description=prompt_template,
                expected_output="A single, optimized prompt string ready for an image generation model.",
                agent=design_director
            )

            my_crew = Crew(agents=[design_director], tasks=[refinement_task])

            try:
                loop = asyncio.get_event_loop()
                result = await loop.run_in_executor(None, my_crew.kickoff)
                refined_prompt = str(result).strip() if result else ""

                # Perform automated quality evaluation. If it fails, fall back to a safer prompt.
                if self._evaluate_prompt_quality(refined_prompt):
                    optimized_prompt = refined_prompt
                else:
                    logger.warning(
                        f"Refined prompt '{refined_prompt}' failed quality check. "
                        f"Reverting to basic prompt for cue: '{cue}'"
                    )
                    optimized_prompt = self._build_fallback_prompt(cue)

            except Exception as e:
                logger.error(f"Asset refinement task failed ({e}). Reverting to basic prompt.")
                optimized_prompt = self._build_fallback_prompt(cue)
        asset = AssetItem(
            asset_id=asset_id,
            scene_reference=scene_id,
            cue_reference=cue_id,
            asset_type="image",
            url=f"https://supabase-storage.local/assets/{uuid.uuid4()}.png",
            prompt=optimized_prompt,
            source="generated",
            asset_license="open-source",
            element=cue,
            prompt_used=optimized_prompt,
            resolution="1920x1080",
            aspect_ratio="16:9"
        )

        self.register_asset_in_storage(asset, video_id)
        return asset

async def process_scene_elements(scene_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Processes scene data to resolve all visual cues into concrete assets.
    This function acts as the main entry point for the asset generation stage,
    consuming the output from the Scene Planner and producing a structured
    asset list for the downstream Animation Engine.
    """
    video_id = scene_data.get("video_id", "unspecified_video")
    scenes = scene_data.get("scenes", [])
    service = AssetService()
    tasks = []
    asset_index = 1

    for scene in scenes:
        scene_id = scene.get("scene_id", "unspecified_scene")
        visual_elements = scene.get("visual_elements", [])

        for element in visual_elements:
            # Per test_assets.py and upstream contracts, we process elements that have an asset_id.
            if element.get("element_type") == "image" or "asset_id" in element:
                cue_text = element.get("description", element.get("text", "No cue provided"))
                asset_id = element.get("asset_id") or f"asset_{asset_index}"
                cue_id = element.get("cue_id") or f"cue_{asset_index}"
                tasks.append(service.resolve_visual_cue(cue_text, scene_id, cue_id, asset_id, video_id))
                asset_index += 1

    if not tasks:
        return {"video_id": video_id, "assets": []}

    gathered_assets = await asyncio.gather(*tasks)

    # Format the output to match the downstream contract for the Animation Engine.
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

    return {"video_id": video_id, "assets": resolved_assets}
