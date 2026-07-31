import os
import logging
import uuid
from fastapi import APIRouter, BackgroundTasks, HTTPException
from supabase import create_client, Client
from dotenv import load_dotenv

from backend.app.pipeline.orchestrator import process_video_job
from backend.app.schemas.video import VideoRequest, JobResponse

logger = logging.getLogger(__name__)

load_dotenv()
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise RuntimeError("CRITICAL ERROR: SUPABASE_URL and SUPABASE_KEY must be set in your .env file.")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
router = APIRouter()

@router.post("/api/generate", response_model=JobResponse)
async def generate_video(request: VideoRequest, background_tasks: BackgroundTasks):
    try:
        insert_payload = {
            "prompt": request.prompt,
            "status": "pending"
        }
        if request.user_id:
            insert_payload["user_id"] = request.user_id
            
        db_response = supabase.table("videos").insert(insert_payload).execute()
        records = db_response.data
        if not isinstance(records, list) or len(records) == 0 or not isinstance(records[0], dict):
            raise ValueError("Failed to insert video record into database. Empty response received.")
            
        job_id = str(records[0].get("id", ""))
        background_tasks.add_task(process_video_job, job_id, request.prompt, supabase)
        
        return {
            "message": "Video generation job started!",
            "job_id": job_id,
            "status": "pending"
        }
        
    except Exception as e:
        logger.error(f"Failed to start video generation: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="An internal server error occurred while processing your request.")

@router.get("/api/status/{job_id}")
async def get_status(job_id: str):
    try:
        uuid.UUID(job_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid job_id format. Must be a valid UUID.")
        
    try:
        response = supabase.table("videos").select("status, video_url, error_message").eq("id", job_id).execute()
        
        if not response.data:
            raise HTTPException(status_code=404, detail="Job not found")
            
        return response.data[0]
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch status for job {job_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="An internal server error occurred while fetching the status.")

@router.get("/api/data/{job_id}/{stage_column}")
async def get_stage_data(job_id: str, stage_column: str):
    try:
        uuid.UUID(job_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid job_id format.")
        
    allowed_columns = [
        "script_data", "scene_data", "audio_metadata", "timestamp_data", 
        "asset_data", "composition_data", "animation_data"
    ]
    
    if stage_column not in allowed_columns:
        raise HTTPException(status_code=400, detail="Invalid data column requested.")
        
    try:
        response = supabase.table("videos").select(stage_column).eq("id", job_id).execute()
        if not response.data:
            raise HTTPException(status_code=404, detail="Job not found")
            
        return response.data[0]
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch {stage_column} for job {job_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Error fetching stage data.")