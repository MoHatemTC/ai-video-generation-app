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

# Safety Guard: Ensure env variables exist before starting the app
if not SUPABASE_URL or not SUPABASE_KEY:
    raise RuntimeError("CRITICAL ERROR: SUPABASE_URL and SUPABASE_KEY must be set in your .env file.")

# Initialize DB connection for routes
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Use APIRouter instead of FastAPI app directly
router = APIRouter()

@router.post("/api/generate", response_model=JobResponse)
async def generate_video(request: VideoRequest, background_tasks: BackgroundTasks):
    try:
        # 1. Create a new record in Supabase (Added user_id mapping)
        insert_payload = {
            "prompt": request.prompt,
            "status": "pending"
        }
        if request.user_id:
            insert_payload["user_id"] = request.user_id
            
        db_response = supabase.table("videos").insert(insert_payload).execute()
        
        # 2. Safety check: Confirm we got a row back before accessing data
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
        # Log internal details to terminal, return generic message to user
        logger.error(f"Failed to start video generation: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="An internal server error occurred while processing your request.")

@router.get("/api/status/{job_id}")
async def get_status(job_id: str):
    # 1. Validate that job_id is actually a UUID before hitting the database!
    try:
        uuid.UUID(job_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid job_id format. Must be a valid UUID.")
        
    try:
        # 2. Fetch the current status
        response = supabase.table("videos").select("status, video_url, error_message").eq("id", job_id).execute()
        
        # 3. Handle not found
        if not response.data:
            raise HTTPException(status_code=404, detail="Job not found")
            
        return response.data[0]
        
    except HTTPException:
        # Allow our custom HTTPExceptions (like the 404 above) to pass through
        raise
    except Exception as e:
        # Safely log and mask any unexpected database crashes
        logger.error(f"Failed to fetch status for job {job_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="An internal server error occurred while fetching the status.")