from typing import Optional
from pydantic import BaseModel, Field

from backend.models.db_models import VideoStatus


class VideoCreateRequest(BaseModel):
    instruction: str = Field(..., min_length=3, description="e.g. 'I want a video about photosynthesis'")
    tone: str = "professional"
    audience: str = "general"
    length_minutes: float = 1.0


class VideoStatusResponse(BaseModel):
    id: str
    status: VideoStatus
    stage_detail: Optional[str] = None
    error_message: Optional[str] = None
    output_url: Optional[str] = None

    class Config:
        from_attributes = True


class ScriptReviewRequest(BaseModel):
    """Human-in-the-loop review (PRD 6.2): user may edit the script JSON before render continues."""
    approved_script_json: str
