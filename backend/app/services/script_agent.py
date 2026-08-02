import os
import json
import logging
import re
from openai import AsyncOpenAI
from backend.app.schemas.script import VideoScriptBlueprint, ScriptSegment

logger = logging.getLogger(__name__)

async def generate_script(user_prompt: str) -> VideoScriptBlueprint:
    litellm_key = os.getenv("LITELLM_API_KEY")
    litellm_url = os.getenv("LITELLM_BASE_URL")
    gemini_key = os.getenv("GEMINI_API_KEY")
    openrouter_key = os.getenv("OPENROUTER_API_KEY")

    api_key = None
    base_url = None
    model_name = "gemini/gemini-pro-latest"

    # Determine provider — prioritize LiteLLM proxy (Sprints company API)
    if litellm_url and "your_" not in litellm_url and litellm_key and "your_" not in litellm_key:
        api_key = litellm_key
        base_url = litellm_url
        model_name = "gemini/gemini-pro-latest"
    elif gemini_key and "your_" not in gemini_key:
        api_key = gemini_key
        base_url = "https://generativelanguage.googleapis.com/v1beta/openai/"
        model_name = "gemini-3.5-flash-lite"
    elif openrouter_key and "your_" not in openrouter_key:
        api_key = openrouter_key
        base_url = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
        model_name = os.getenv("OPENROUTER_MODEL", "openrouter/free")

    if api_key and base_url:
        try:
            client = AsyncOpenAI(
                api_key=api_key.strip(),
                base_url=base_url.strip()
            )
            
            system_prompt = """
            You are an expert educational video scriptwriter. 
            Convert the user's educational topic into a highly engaging, well-structured video script.
            You must divide the script into visual segments and narrator dialogue.
            """
            
            response = await client.beta.chat.completions.parse(
                model=model_name,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Create an educational video about: {user_prompt}"}
                ],
                response_format=VideoScriptBlueprint,
            )
            parsed = response.choices[0].message.parsed
            if parsed:
                return parsed
        except Exception as e:
            logger.warning(f"LLM API call failed ({e}). Falling back to blueprint template.")

    # Fallback template if API key is missing, invalid, or endpoint connection fails
    return VideoScriptBlueprint(
        title=f"Educational Guide: {user_prompt}",
        target_audience="General Audience",
        estimated_total_duration=30,
        segments=[
            ScriptSegment(
                segment_id=1,
                narrator_text=f"Welcome! Today we are exploring {user_prompt}.",
                visual_cue=f"A vibrant intro graphic illustrating {user_prompt}"
            ),
            ScriptSegment(
                segment_id=2,
                narrator_text=f"Understanding {user_prompt} opens up new possibilities and insights.",
                visual_cue=f"Detailed educational diagram showing key concepts of {user_prompt}"
            ),
            ScriptSegment(
                segment_id=3,
                narrator_text="Thank you for watching this quick educational overview!",
                visual_cue="Outro graphic with summary notes"
            )
        ]
    )
