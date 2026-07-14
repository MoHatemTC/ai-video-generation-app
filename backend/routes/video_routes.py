from fastapi import APIRouter, BackgroundTasks, HTTPException
from supabase import create_client, Client
import os
from dotenv import load_dotenv

# We updated these imports to match your manager's requested folder structure!
from backend.app.pipeline.orchestrator import process_video_job
from backend.app.schemas.video import VideoRequest

load_dotenv()
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# Initialize DB connection for routes
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Use APIRouter instead of FastAPI app directly
router = APIRouter()

# ── No duplicate VideoRequest here — using the one from schemas.video ──


@router.post("/api/generate")
async def generate_video(request: VideoRequest, background_tasks: BackgroundTasks):
    try:
        # 1. Create a new record in Supabase
        db_response = supabase.table("videos").insert({
            "prompt": request.prompt,
            "status": "pending"
        }).execute()
        
        # 2. Get the auto-generated ID
        job_id = db_response.data[0]['id']
        
        # 3. Tell FastAPI to run the heavy AI process in the background
        background_tasks.add_task(process_video_job, job_id, request.prompt, supabase)
        
        # 4. Reply to the user immediately
        return {
            "message": "Video generation job started!",
            "job_id": job_id,
            "status": "pending"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Map pipeline status values to a human-readable stage number for the frontend
_STATUS_TO_STAGE = {
    "pending":               {"stage": 0, "label": "Queued"},
    "generating_script":     {"stage": 1, "label": "Generating script"},
    "planning_scenes":       {"stage": 2, "label": "Planning scenes"},
    "generating_audio":      {"stage": 3, "label": "Generating voiceover"},
    "aligning_timestamps":   {"stage": 4, "label": "Aligning timestamps"},
    "fetching_assets":       {"stage": 5, "label": "Fetching assets"},
    "composing_scenes":      {"stage": 6, "label": "Composing scenes"},
    "animating":             {"stage": 7, "label": "Animating"},
    "rendering":             {"stage": 8, "label": "Rendering video"},
    "completed":             {"stage": 9, "label": "Completed"},
    "failed":                {"stage": -1, "label": "Failed"},
}


@router.get("/api/status/{job_id}")
async def get_status(job_id: str):
    response = supabase.table("videos").select(
        "status, video_url, error_message"
    ).eq("id", job_id).execute()
    
    if not response.data:
        raise HTTPException(status_code=404, detail="Job not found")
    
    row = response.data[0]
    stage_info = _STATUS_TO_STAGE.get(
        row["status"], {"stage": -1, "label": row["status"]}
    )

    return {
        "status": row["status"],
        "video_url": row.get("video_url"),
        "error_message": row.get("error_message"),
        "current_stage": stage_info["stage"],
        "current_stage_label": stage_info["label"],
        "total_stages": 9,
    }