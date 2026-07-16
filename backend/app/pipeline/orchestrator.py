import asyncio
import logging
from supabase import Client

logger = logging.getLogger(__name__)

# --- Dummy AI Contract Functions (No CrewAI dependencies here!) ---
def run_transcript_crew_sync(prompt: str) -> dict:
    return {"title": "Generated Topic", "segments": [{"id": "seg_1", "text": prompt, "visual_cue": "Intro"}]}

def run_planner_crew_sync(script_data: dict) -> dict:
    return {"schema_version": "1.0", "scenes": [{"scene_id": "scene_1"}]}

def run_voiceover_crew_sync(script_data: dict) -> dict:
    return {"audio_path": "/tmp/audio.wav"}

def run_alignment_crew_sync(audio_data: dict, script_data: dict) -> dict:
    return {"word_timestamps": []}

def run_asset_crew_sync(scene_data: dict) -> dict:
    return {"assets": []}

def run_composition_crew_sync(scene_data: dict, asset_data: dict, timestamp_data: dict) -> dict:
    return {"scenes": []}

def run_animation_crew_sync(composed_data: dict) -> dict:
    return {"status": "animation_map_ready"}

def run_render_crew_sync(animation_data: dict, audio_data: dict) -> str:
    return "https://storage.example/video.mp4"


async def process_video_job(job_id: str, prompt: str, supabase: Client):
    """
    Decoupled, contract-driven stage sequencing.
    Every single stage is executed in a background thread to prevent blocking.
    """
    # Track the current stage so we can log exactly where a failure happens!
    current_stage = "init"
    
    try:
        logger.info(f"Starting pipeline for Job: {job_id}")

        # STAGE 1: Transcript 
        current_stage = "transcript"
        supabase.table("videos").update({"status": "generating_script"}).eq("id", job_id).execute()
        script_data = await asyncio.to_thread(run_transcript_crew_sync, prompt)
        supabase.table("videos").update({"script_data": script_data}).eq("id", job_id).execute()

        # STAGE 2: Planner 
        current_stage = "planner"
        supabase.table("videos").update({"status": "planning_scenes"}).eq("id", job_id).execute()
        scene_data = await asyncio.to_thread(run_planner_crew_sync, script_data)
        supabase.table("videos").update({"scene_data": scene_data}).eq("id", job_id).execute()

        # STAGE 3: Voiceover
        current_stage = "voiceover"
        supabase.table("videos").update({"status": "generating_audio"}).eq("id", job_id).execute()
        audio_data = await asyncio.to_thread(run_voiceover_crew_sync, script_data)
        supabase.table("videos").update({"audio_metadata": audio_data}).eq("id", job_id).execute()

        # STAGE 4: Alignment 
        current_stage = "alignment"
        supabase.table("videos").update({"status": "aligning_timestamps"}).eq("id", job_id).execute()
        timestamp_data = await asyncio.to_thread(run_alignment_crew_sync, audio_data, script_data)
        supabase.table("videos").update({"timestamp_data": timestamp_data}).eq("id", job_id).execute()

        # STAGE 5: Assets
        current_stage = "assets"
        supabase.table("videos").update({"status": "fetching_assets"}).eq("id", job_id).execute()
        asset_data = await asyncio.to_thread(run_asset_crew_sync, scene_data)
        supabase.table("videos").update({"asset_data": asset_data}).eq("id", job_id).execute()

        # STAGE 6: Composition 
        current_stage = "composition"
        supabase.table("videos").update({"status": "composing_scenes"}).eq("id", job_id).execute()
        comp_data = await asyncio.to_thread(run_composition_crew_sync, scene_data, asset_data, timestamp_data)
        supabase.table("videos").update({"composition_data": comp_data}).eq("id", job_id).execute()
        
        # STAGE 7: Animation
        current_stage = "animation"
        supabase.table("videos").update({"status": "animating"}).eq("id", job_id).execute()
        anim_data = await asyncio.to_thread(run_animation_crew_sync, comp_data)
        supabase.table("videos").update({"animation_data": anim_data}).eq("id", job_id).execute()

        # STAGE 8: Render
        current_stage = "render"
        supabase.table("videos").update({"status": "rendering"}).eq("id", job_id).execute()
        video_url = await asyncio.to_thread(run_render_crew_sync, anim_data, audio_data)
        
        # COMPLETION
        supabase.table("videos").update({
            "status": "completed",
            "video_url": video_url
        }).eq("id", job_id).execute()
        logger.info(f"Job {job_id} successfully completed!")

    except Exception as e:
        # THE FIX: We inject the current_stage into the error message!
        error_message = f"[{current_stage}] {str(e)}"
        
        logger.error(f"Pipeline Failed for Job {job_id}: {error_message}")
        supabase.table("videos").update({
            "status": "failed", 
            "error_message": error_message
        }).eq("id", job_id).execute()