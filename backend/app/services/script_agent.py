import logging
from backend.app.schemas.script import VideoScriptBlueprint, ScriptSegment

logger = logging.getLogger(__name__)

async def generate_script(prompt: str) -> VideoScriptBlueprint:
    """
    Generates a script using a hardcoded fallback.
    The OpenRouter call has been disabled to avoid API key errors.
    """
    logger.warning("OpenRouter is disabled by default. Reverting to fallback script.")
    
    # We use this fallback to keep the pipeline alive without needing an external AI for script generation.
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