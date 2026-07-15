from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel
from supabase import create_client, Client
import os
import logging
from dotenv import load_dotenv

# We updated these imports to match your manager's requested folder structure!
from backend.app.pipeline.orchestrator import process_video_job
from backend.app.schemas.video import VideoRequest

# Set up logging for error handling
logger = logging.getLogger(__name__)

load_dotenv()
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# Safety Guard: Ensure env variables exist before starting the app (Point 3)
if not SUPABASE_URL or not SUPABASE_KEY:
    raise RuntimeError("CRITICAL ERROR: SUPABASE_URL and SUPABASE_KEY must be set in your .env file.")

# Initialize DB connection for routes
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Use APIRouter instead of FastAPI app directly
router = APIRouter()

@router.post("/api/generate")
async def generate_video(request: VideoRequest, background_tasks: BackgroundTasks):
    try:
        # 1. Create a new record in Supabase (Added user_id mapping - Point 6)
        insert_payload = {
            "prompt": request.prompt,
            "status": "pending"
        }
        if request.user_id:
            insert_payload["user_id"] = request.user_id
            
        db_response = supabase.table("videos").insert(insert_payload).execute()
        
        # 2. Safety check: Confirm we got a row back before accessing data (Point 2)
        if not db_response.data or len(db_response.data) == 0:
            raise ValueError("Failed to insert video record into database. Empty response received.")
            
        # 3. Get the auto-generated ID
        job_id = db_response.data[0]['id']
        
        # 4. Tell FastAPI to run the heavy AI process in the background
        background_tasks.add_task(process_video_job, job_id, request.prompt, supabase)
        
        # 5. Reply to the user immediately
        return {
            "message": "Video generation job started!",
            "job_id": job_id,
            "status": "pending"
        }
        
    except Exception as e:
        # Log internal details to terminal, return generic message to user (Point 4)
        logger.error(f"Failed to start video generation: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="An internal server error occurred while processing your request.")

@router.get("/api/status/{job_id}")
async def get_status(job_id: str):
    response = supabase.table("videos").select("status, video_url, error_message").eq("id", job_id).execute()
    
    if not response.data:
        raise HTTPException(status_code=404, detail="Job not found")
        
    return response.data[0]