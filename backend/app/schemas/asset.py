from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional

class AssetItem(BaseModel):
    """
    Standardized visual asset representing a flat item structure
    for Stage 6 Composition engine compatibility.
    """
    model_config = ConfigDict(populate_by_name=True)

    asset_id: str = Field(
        ..., 
        description="Unique sequential identifier for the asset (e.g., image_1)"
    )
    scene_reference: str = Field(
        ..., 
        alias="scene_id", 
        description="Must match scene_id across pipelines"
    )
    cue_reference: str = Field(
        ..., 
        alias="cue_id", 
        description="Identical to cue_id from Stage 1/2 Scene Planner"
    )
    asset_type: str = Field(
        default="image", 
        alias="type", 
        description="Target asset format type"
    )
    url: str = Field(
        ..., 
        description="Fully qualified storage URL"
    )
    prompt: str = Field(
        ..., 
        alias="description", 
        description="The detailed design description used to render the visual"
    )
    source: str = Field(
        default="generated", 
        description="System asset origin profile"
    )
    asset_license: str = Field(
        default="open-source", 
        alias="license", 
        description="License classification metadata"
    )
    element: Optional[str] = Field(
        None, 
        description="Preserved raw textual cue for verification"
    )


class AssetResponseContract(BaseModel):
    """
    The final schema delivery wrapper expected by Nada's Stage 6 pipeline.
    """
    model_config = ConfigDict(populate_by_name=True)

    schema_version: str = Field(
        default="1.0", 
        description="Metadata schema parsing version"
    )
    video_id: str = Field(
        ..., 
        description="Identical to video_id across all pipeline stages"
    )
    assets: List[AssetItem] = Field(
        ..., 
        alias="assets", 
        description="Flat collection of resolved visual assets"
    )