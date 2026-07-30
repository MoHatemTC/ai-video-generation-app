import os
import json
import logging
import re
from openai import AsyncOpenAI
from backend.app.schemas.script import VideoScriptBlueprint, ScriptSegment

logger = logging.getLogger(__name__)

async def generate_script(prompt: str) -> VideoScriptBlueprint:
    """
    Generates a script using OpenRouter's free tier auto-router.
    Includes a fallback in case the free model truncates the JSON.
    """
    api_key = os.getenv("OPENROUTER_API_KEY")
    base_url = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
    model_name = os.getenv("OPENROUTER_MODEL", "openrouter/free").strip()
    
    if not api_key:
        raise ValueError("OPENROUTER_API_KEY environment variable is missing.")

    client = AsyncOpenAI(
        api_key=api_key.strip(),
        base_url=base_url.strip()
    )

    system_prompt = (
        "You are an expert educational scriptwriter. "
        "Write a short, structured e-learning script for the provided topic. "
        "Keep it brief to avoid token limits. "
        "You MUST return ONLY a raw JSON object matching this schema: "
        "{\"title\": \"string\", \"target_audience\": \"string\", \"estimated_total_duration\": int, "
        "\"segments\": [{\"segment_id\": int, \"narrator_text\": \"string\", \"visual_cue\": \"string\"}]}"
    )

    try:
        response = await client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Topic: {prompt}"}
            ],
            temperature=0.7
        )
        
        raw_content = response.choices[0].message.content.strip()
            
        # JSON Extractor Magnet
        json_match = re.search(r'\{.*\}', raw_content, re.DOTALL)
        clean_json = json_match.group(0) if json_match else raw_content
            
        return VideoScriptBlueprint.model_validate_json(clean_json)
        
    except Exception as e:
        logger.warning(f"AI truncated the JSON or failed ({str(e)}). Reverting to fallback script.")
        
        # If the free AI breaks, we use this fallback to keep the pipeline alive!
        return VideoScriptBlueprint(
            title=f"Introduction to {prompt}",
            target_audience="Beginners",
            estimated_total_duration=30,
            segments=[
                ScriptSegment(
                    segment_id=1, 
                    narrator_text=f"Welcome to this quick lesson on {prompt}.", 
                    visual_cue="Introductory title screen with bold text."
                ),
                ScriptSegment(
                    segment_id=2, 
                    narrator_text="Let's explore the main concepts and how they work in the real world.", 
                    visual_cue="An engaging, colorful diagram explaining the topic."
                )
            ]
        )