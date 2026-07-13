from pydantic import BaseModel, Field
from typing import List, Optional

class AssetItem(BaseModel):
    """Represents a single visual asset as defined in the Stage 5 JSON contract."""
    element: str = Field(..., description="The exact text cue from Mostafa's visual_elements list")
    url: str = Field(..., description="The public-facing storage URL from Supabase")
    license: str = Field(default="open-source", description="Royalty-free or open-source clearance status")
    
    # Management Tracking Requirements
    asset_type: str = Field(default="image", description="Asset primitive format type")
    source: str = Field(default="generated", description="Origin profile: generated or searched")
    scene_reference: Optional[str] = Field(None, description="The unique scene ID this asset belongs to")

class AssetResponseContract(BaseModel):
    """The final collection contract Nada's Stage 6 Composition pipeline expects."""
    assets: List[AssetItem]