from typing import List
from pydantic import BaseModel, Field


class WordTimestamp(BaseModel):
    word: str
    start: float = Field(..., description="Start time in seconds from the beginning of the audio track")
    end: float = Field(..., description="End time in seconds")


class SegmentTimestamp(BaseModel):
    segment_id: int
    start: float
    end: float
    words: List[WordTimestamp] = Field(default_factory=list)


class TimestampMap(BaseModel):
    segments: List[SegmentTimestamp]
    total_duration: float


class Asset(BaseModel):
    element_id: str = Field(..., description="Matches VisualElement.element_id from the scene plan")
    asset_type: str
    source: str = Field(..., description="'generated' or 'library'")
    license: str = Field(default="generated-cc0", description="License tag for Responsible-AI tracking (PRD 9)")
    file_path: str = Field(..., description="Path to the generated asset on disk")


class AssetManifest(BaseModel):
    assets: List[Asset]
