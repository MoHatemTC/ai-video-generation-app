"""
Audio (Voiceover) Generation: script -> audio track (PRD 7.4).
"""
import os

from backend.models.script import VideoScriptBlueprint
from backend.services.ai_client import text_to_speech


def generate_voiceover(
    script: VideoScriptBlueprint, output_dir: str, voice: str = "alloy"
) -> str:
    """
    Generate a single voiceover track for the full script (segments concatenated
    with a short pause) and return the audio file path.
    """
    os.makedirs(output_dir, exist_ok=True)
    full_narration = "\n".join(segment.text for segment in script.segments)
    output_path = os.path.join(output_dir, "voiceover.mp3")
    return text_to_speech(text=full_narration, voice=voice, output_path=output_path)
