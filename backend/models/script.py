from pydantic import BaseModel, Field
from typing import List

class ScriptSegment(BaseModel):
    segment_id: int = Field(..., description="Unique sequential ID for the segment starting from 1")
    text: str = Field(..., description="The spoken narration text for this specific segment")
    visual_cues: str = Field(..., description="Detailed visual and directorial cues for rendering")
    duration_seconds: int = Field(..., description="Estimated duration of the narration in seconds")

class VideoScriptBlueprint(BaseModel):
    title: str = Field(..., description="Proposed catchy title for the video")
    target_audience: str = Field(..., description="Target audience level")
    estimated_total_duration: int = Field(..., description="Total accumulated duration in seconds")
    segments: List[ScriptSegment] = Field(..., description="Structured list of video segments")