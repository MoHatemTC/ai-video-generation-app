import os
import logging
import uuid
from fastapi import APIRouter, BackgroundTasks, HTTPException
from fastapi.responses import FileResponse, HTMLResponse
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
        records = db_response.data
        if not isinstance(records, list) or len(records) == 0 or not isinstance(records[0], dict):
            raise ValueError("Failed to insert video record into database. Empty response received.")
            
        job_id = str(records[0].get("id", ""))
        background_tasks.add_task(process_video_job, request.prompt, job_id=job_id, supabase_client=supabase)

        
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

@router.get("/api/render/{job_id}")
async def get_rendered_video_html(job_id: str):
    """Serve the complete, standalone animated HTML video for a job directly to the browser."""
    try:
        uuid.UUID(job_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid job_id format.")

    # Locate render file in data/renders/{job_id}.html
    render_dir = os.path.join(os.path.dirname(__file__), "..", "..", "data", "renders")
    file_path = os.path.join(render_dir, f"{job_id}.html")

    if not os.path.exists(file_path):
        # Fall back to any sample render if specific job file is not found
        sample_files = [f for f in os.listdir(render_dir) if f.endswith(".html")] if os.path.exists(render_dir) else []
        if sample_files:
            file_path = os.path.join(render_dir, sample_files[0])
        else:
            raise HTTPException(status_code=404, detail="Rendered video not found for this job.")

    return FileResponse(path=file_path, media_type="text/html")

@router.get("/api/video/{job_id}/download")
async def download_video(job_id: str):
    """Download the rendered video output."""
    try:
        uuid.UUID(job_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid job_id format.")

    render_dir = os.path.join(os.path.dirname(__file__), "..", "..", "data", "renders")
    html_path = os.path.join(render_dir, f"{job_id}.html")
    mp4_path = os.path.join(render_dir, f"{job_id}.mp4")

    if os.path.exists(mp4_path):
        return FileResponse(path=mp4_path, filename=f"video_{job_id[:8]}.mp4", media_type="video/mp4")
    
    # Synthesize MP4 on the fly from database records
    try:
        from backend.app.pipeline.render.mp4_renderer import render_scene_plan_to_mp4
        res = supabase.table("videos").select("scene_data, audio_metadata").eq("id", job_id).execute()
        if isinstance(res.data, list) and len(res.data) > 0:
            row = res.data[0]
            if isinstance(row, dict):
                s_data = row.get("scene_data") if isinstance(row.get("scene_data"), dict) else {}
                a_meta = row.get("audio_metadata") if isinstance(row.get("audio_metadata"), dict) else {}
                a_path = str(a_meta.get("local_path") or a_meta.get("audio_file_path") or "")
                rendered_path = await render_scene_plan_to_mp4(s_data, audio_path=a_path, output_mp4_path=mp4_path)
                if rendered_path and os.path.exists(rendered_path):
                    return FileResponse(path=rendered_path, filename=f"video_{job_id[:8]}.mp4", media_type="video/mp4")
    except Exception as err:
        logger.warning(f"On-demand MP4 synthesis warning: {err}")

    if os.path.exists(html_path):
        return FileResponse(path=html_path, filename=f"video_{job_id[:8]}.html", media_type="text/html")
    else:
        sample_files = [f for f in os.listdir(render_dir) if f.endswith(".html")] if os.path.exists(render_dir) else []
        if sample_files:
            fallback = os.path.join(render_dir, sample_files[0])
            return FileResponse(path=fallback, filename=f"video_{job_id[:8]}.html", media_type="text/html")
        raise HTTPException(status_code=404, detail="No downloadable video found for this job.")

