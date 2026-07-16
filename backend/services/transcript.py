"""
Transcript Generator Agent: instruction -> structured script (PRD 7.2).
"""
from backend.models.script import VideoScriptBlueprint
from backend.prompts import transcript_agent
from backend.services.ai_client import structured_completion


def generate_segmented_script(
    instruction: str, tone: str, audience: str, length_minutes: float
) -> VideoScriptBlueprint:
    """Convert a user instruction into a validated, non-hallucinated structured script blueprint."""
    return structured_completion(
        system_prompt=transcript_agent.SYSTEM_PROMPT,
        user_prompt=transcript_agent.build_user_prompt(instruction, tone, audience, length_minutes),
        response_model=VideoScriptBlueprint,
    )
