from pydantic import BaseModel, Field
from typing import List

class ScriptSegment(BaseModel):
    segment_id: int = Field(..., description="The chronological order of the segment (1, 2, 3...)")
    narrator_text: str = Field(..., description="The actual words the AI voice will speak")
    visual_cue: str = Field(..., description="Instructions for the image/video generator (e.g., 'A cinematic wide shot of a futuristic city')")

class VideoScriptBlueprint(BaseModel):
    title: str = Field(..., description="A catchy title for the video")
    target_audience: str = Field(..., description="The intended audience for the video")
    estimated_total_duration: int = Field(..., description="Estimated length in seconds")
    segments: List[ScriptSegment] = Field(..., description="The chronological list of scenes in the video")