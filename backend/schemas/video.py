from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime

class User(BaseModel):
    id: str
    email: str
    full_name: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.now)

class Video(BaseModel):
    id: str
    prompt: str
    status: str
    user_id: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.now)
    
    # We use Dict[str, Any] to represent the JSONB columns from Supabase flexibly
    script_data: Optional[Dict[str, Any]] = None
    scene_data: Optional[Dict[str, Any]] = None
    audio_metadata: Optional[Dict[str, Any]] = None
    timestamp_data: Optional[Dict[str, Any]] = None
    asset_data: Optional[Dict[str, Any]] = None
    composition_data: Optional[Dict[str, Any]] = None
    animation_data: Optional[Dict[str, Any]] = None
    
    video_url: Optional[str] = None
    error_message: Optional[str] = None

class RenderJob(BaseModel):
    job_id: str
    video_id: str
    status: str
    error_message: Optional[str] = None

class VideoRequest(BaseModel):
    prompt: str
    user_id: Optional[str] = None

class JobResponse(BaseModel):
    message: str
    job_id: str
    status: str