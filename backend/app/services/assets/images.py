import os
import uuid
import logging
import json
import asyncio
import re
import urllib.parse
import urllib.request

from datetime import datetime, timezone
from typing import List, Dict, Any
from dotenv import load_dotenv
from crewai import Agent, Task, Crew, LLM
from backend.app.schemas.asset import AssetItem

# Pydantic V2 Migration warnings are expected from CrewAI and can be ignored for now.
logger = logging.getLogger(__name__)

load_dotenv()

# --- Quality Evaluation Constants ---
REQUIRED_STYLE_KEYWORDS = ["flat 2d", "illustration"]
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
        """
        Attempts to initialize and return a LiteLLM client, falling back to Google Gemini.
        Provides detailed logging for each step.
        """
        # 1. Attempt to use the primary Sprints.ai LiteLLM server
        litellm_api_key = os.getenv("LITELLM_API_KEY")
        litellm_api_base = os.getenv("LITELLM_API_BASE")
        if litellm_api_key and litellm_api_base:
            logger.info("Attempting to connect to Sprints.ai LiteLLM server...")
            try:
                # 'openai/' instructs CrewAI to send OpenAI format to base_url
                # 'gemini/gemini-2.5-flash' satisfies proxy 'gemini/*' team permission
                llm = LLM(
                    model="openai/gemini/gemini-2.5-flash",                    base_url=litellm_api_base,
                )
                logger.info("✅ Successfully connected to Sprints.ai LiteLLM server.")
                return llm
            except Exception as e:
                logger.warning(f"⚠️ Failed to connect to Sprints.ai LiteLLM server: {e}")

        # 2. Fallback to direct Google Gemini
        gemini_api_key = os.getenv("GEMINI_API_KEY")
        if gemini_api_key:
            logger.info("Attempting to connect to Google Gemini...")
            try:
                llm = LLM(
                    model="gemini/gemini-2.5-flash",                )
                logger.info("✅ Successfully connected to Google Gemini.")
                return llm
            except Exception as e:
                logger.warning(f"⚠️ Failed to connect to Google Gemini: {e}")

        # 3. If all else fails, return None
        logger.error("❌ CRITICAL: Could not establish a connection to any LLM. Prompt optimization will be skipped.")
        return None

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
            **-Original Cue:**  
                "{cue}"
                Based on the original cue, generate a single, optimized prompt string that strictly adheres to all quality criteria. The output must be only the prompt string itself.
"""

        negative_prompts = ", ".join(FORBIDDEN_PROMPT_KEYWORDS)
        return template.format(negative_prompts=negative_prompts, cue=cue)

    def _build_fallback_prompt(self, cue: str) -> str:
        """
        Builds a high-quality, fallback prompt with mandatory guardrails.
        """
        # Mandatory guardrails to ensure high-quality, consistent output
        guardrails = "flat 2d vector illustration, clean lines, educational, isolated background, no text, no shadows"
        
        # Combine the user's cue with the mandatory guardrails
        enhanced_prompt = f"{guardrails}, {cue}"
        
        logger.info(f"Built high-quality fallback prompt: \"{enhanced_prompt}\"")
        return enhanced_prompt

    def _evaluate_prompt_quality(self, prompt: str) -> bool:
        """
        Performs a simple quality check on the generated prompt.
        """
        prompt_lower = prompt.lower()
        if not all(keyword in prompt_lower for keyword in REQUIRED_STYLE_KEYWORDS):
            logger.warning(f"Quality check failed: Prompt is missing required style keywords: {REQUIRED_STYLE_KEYWORDS}")
            return False
        if any(keyword in prompt_lower for keyword in FORBIDDEN_PROMPT_KEYWORDS):
            logger.warning(f"Quality check failed: Prompt contains forbidden keywords: {FORBIDDEN_PROMPT_KEYWORDS}")
            return False
        return True

    async def resolve_visual_cue(
        self, cue: str, scene_id: str, cue_id: str, asset_id: str, video_id: str, supabase_client: Any = None
    ) -> AssetItem:
        # Pull the model string from the .env file, default to openrouter/free
        model_string = os.getenv("OPENROUTER_MODEL", "openrouter/free")
        llm_client = self._get_llm_client()


        # If we could not get a valid LLM client, do not attempt to run the crew.
        # Go straight to the fallback prompt. This prevents downstream errors.
        if not llm_client:
            optimized_prompt = self._build_fallback_prompt(cue)
        else:
            try:
                # Build an agent/crew using the successfully connected LLM client.
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

                loop = asyncio.get_running_loop()
                result = await loop.run_in_executor(None, my_crew.kickoff)
                refined_prompt = str(result).strip() if result else ""

                # Perform automated quality evaluation. If it fails, fall back to a safer prompt.
                if refined_prompt and self._evaluate_prompt_quality(refined_prompt):
                    optimized_prompt = refined_prompt
                else:
                    if refined_prompt:
                        logger.warning(
                            f"Refined prompt '{refined_prompt}' failed quality check. Reverting to basic prompt for cue: '{cue}'"
                        )
                    optimized_prompt = self._build_fallback_prompt(cue)

            except Exception as e:
                logger.warning(f"Asset refinement task failed ({e}). Reverting to basic prompt.")
                optimized_prompt = self._build_fallback_prompt(cue)

        # Construct Pollinations image URL from the final optimized prompt
        try:
            design_director = Agent(
                role="Educational Visual Design Director",
                goal="Refine simple and loose textual visual cues into highly detailed, clean image prompts.",
                backstory="You are an expert visual layout designer at Sprints Video Studio.",
                verbose=False,
                allow_delegation=False,
                llm=model_string
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
            optimized_prompt = f"Illustration showing: {cue}"

        # Construct Pollinations image URL from the final optimized prompt
        try:
            image_url = f"https://image.pollinations.ai/prompt/{urllib.parse.quote(optimized_prompt)}?width=1280&height=720&model=flux&nologo=true"
        except Exception:
            image_url = f"https://image.pollinations.ai/prompt/{urllib.parse.quote(str(optimized_prompt))}?width=1280&height=720&model=flux&nologo=true"

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

                supabase_client.storage.from_("assets").upload(
                    storage_key,
                    file_bytes,
                    {"content-type": "image/png", "upsert": "true"},
                )

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
            element=cue,
            prompt_used=optimized_prompt,
            resolution="1920x1080",
            aspect_ratio="16:9"
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
        visual_elements = scene.get("visual_cues") or scene.get("visual_elements") or []

        for element in visual_elements:

            element_type = element.get("element_type")
            # Skip pure text elements unless they provide an explicit asset_id
            if element_type == "text" and "asset_id" not in element:
                continue

            asset_id = element.get("asset_id") or f"asset_{asset_index}"
            cue_text = element.get("description", element.get("text", ""))
            cue_id = element.get("cue_id") or f"cue_{asset_index}"

            task = service.resolve_visual_cue(
                cue=cue_text,
                scene_id=scene_id,
                cue_id=cue_id,
                asset_id=asset_id,
                video_id=video_id,
                supabase_client=supabase_client
            )
            tasks.append(task)

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