from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from backend.models.script import VideoScriptBlueprint
from backend.services.transcript import generate_segmented_script

router = APIRouter()

class IntakeRequest(BaseModel):
    instruction: str
    tone: str = "professional"
    audience: str = "general"
    length_minutes: float = 1.0

@router.post("/intake", response_model=VideoScriptBlueprint)
async def process_video_intake(request: IntakeRequest):
    try:
        blueprint = generate_segmented_script(
            instruction=request.instruction,
            tone=request.tone,
            audience=request.audience,
            length_minutes=request.length_minutes
        )
        return blueprint
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Pipeline integration error: {str(e)}")