import os
import uuid
import logging
import json
import asyncio
import re
from datetime import datetime, timezone
from typing import Dict, Any
from dotenv import load_dotenv
from crewai import Agent, Task, Crew, LLM
from backend.app.schemas.asset import AssetItem

# Pydantic V2 Migration warnings are expected from CrewAI and can be ignored for now.
# The UserWarning about 'model_name' is also from a dependency and not a blocker.

logger = logging.getLogger(__name__)

load_dotenv()

# --- Quality Evaluation Constants ---
# Keywords that MUST be in the prompt for style adherence.
REQUIRED_STYLE_KEYWORDS = ["flat 2d", "illustration"]
# Keywords that SHOULD NOT be in the prompt.
FORBIDDEN_PROMPT_KEYWORDS = ["text", "gradients", "shadows", "watermarks", "3d", "photo", "photorealistic", "blurry", "low-resolution"]
# ---

class AssetService:
    def __init__(self):
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

            if not api_key or not api_base:
                raise ValueError(
                    "LiteLLM credentials are missing. Set LITELLM_API_KEY and "
                    "LITELLM_API_BASE or LITELLM_BASE_URL."
                )

            # CrewAI delegates through LiteLLM. We keep the model name configurable so it
            # matches whichever Sprints LiteLLM endpoint is currently active.
            return LLM(
                model=model_name,
                api_key=api_key,
                base_url=api_base,
            )
        except (ImportError, ValueError) as e:
            logger.warning(f"Could not initialize LiteLLM client ({e}). Using a fallback LLM for CrewAI.")
            return LLM(model="openai/fake", api_key="fake")

    def _build_fallback_prompt(self, cue: str) -> str:
        """Generate a deterministic prompt when remote refinement is unavailable."""
        return f"flat 2d illustration, {cue}, no text, no shadows"

    def _evaluate_prompt_quality(self, prompt: str) -> bool:
        """
        Performs automated checks on the generated prompt to ensure it meets quality standards.
        Returns True if quality is good, False otherwise.
        """
        prompt_lower = prompt.lower()
        
        # 1. Check for required style keywords
        style_adherence = all(keyword in prompt_lower for keyword in REQUIRED_STYLE_KEYWORDS)
        if not style_adherence:
            logger.warning(f"Quality Warning: Prompt is missing required style keywords. Prompt: '{prompt}'")
            return False

        # 2. Check for forbidden keywords, ignoring them if they are part of a "no <keyword>" or similar phrase.
        for keyword in FORBIDDEN_PROMPT_KEYWORDS:
            # This regex looks for the keyword as a whole word (\b), but only if it's NOT preceded by common negation words.
            pattern = rf"(?<!\bno\s)(?<!\bwithout\s)(?<!\bavoid\s)\b{re.escape(keyword)}\b"
            if re.search(pattern, prompt_lower):
                logger.warning(f"Quality Warning: Prompt contains forbidden keyword '{keyword}'. Prompt: '{prompt}'")
                return False
            
        logger.info("Quality Check Passed: Prompt adheres to defined style and negative constraints.")
        return True

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
            "aspect_ratio": asset.aspect_ratio,
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
                # The cue is in the 'description' field, aligning with tests and documentation.
                cue = element.get("description", "No cue provided")
                asset_id = element.get("asset_id", f"asset_{asset_index}")
                cue_id = element.get("cue_id", f"cue_{asset_index}")
                tasks.append(service.resolve_visual_cue(cue, scene_id, cue_id, asset_id, video_id))
                asset_index += 1

    processed_assets = await asyncio.gather(*tasks)
    
    # Format the output to match the downstream contract for the Animation Engine.
    # See: backend/app/services/assets/README.md
    output_assets = [{
        "asset_id": asset.asset_id, "url": asset.url, "type": asset.asset_type,
        "license": asset.asset_license, "source": asset.source
    } for asset in processed_assets]

    return {"video_id": video_id, "assets": output_assets}
