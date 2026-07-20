import os
import asyncio
import logging
from supabase import Client

from backend.app.services.script_agent import generate_script
from backend.app.schemas.script import VideoScriptBlueprint
from backend.app.services.tts_provider import MockTTSProvider  # Mahdy's function
from backend.app.services.alignment import AlignmentService   # Osama's class 
from backend.app.schemas.timestamps import AudioTrack         # Osama's required audio schema


logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

# --- Dummy AI Contract Functions (No CrewAI dependencies here!) ---

def run_planner_crew_sync(script_data: dict) -> dict:
    return {"schema_version": "1.0", "scenes": [{"scene_id": "scene_1"}]}

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

        # =====================================================================================
        # STAGE 1: Script Generation
        current_stage = "script_generation"
        supabase.table("videos").update({"status": "generating_script"}).eq("id", job_id).execute()
        
        logger.info(f"[{job_id}] Running Stage 1: Script Agent...")
        # Call the LiteLLM agent you just built
        script_data: VideoScriptBlueprint = await generate_script(prompt)
        
        # Save the validated JSON output directly into the Supabase JSONB column
        supabase.table("videos").update({"script_data": script_data.model_dump()}).eq("id", job_id).execute()
        logger.info(f"[{job_id}] Stage 1 Complete!")

        # =====================================================================================
        # STAGE 2: Planner 
        current_stage = "planner"
        supabase.table("videos").update({"status": "planning_scenes"}).eq("id", job_id).execute()
        scene_data = await asyncio.to_thread(run_planner_crew_sync, script_data)
        supabase.table("videos").update({"scene_data": scene_data}).eq("id", job_id).execute()

        # =====================================================================================
        # STAGE 3: Voiceover (TTS)
        current_stage = "voiceover"
        supabase.table("videos").update({"status": "generating_audio"}).eq("id", job_id).execute()
        
        logger.info(f"[{job_id}] Running Stage 3: Mock Audio Generation...")
        
        script_dict = script_data.model_dump()
        full_text = " ".join([seg["narrator_text"] for seg in script_dict["segments"]])
        
        # Use Mahdy's Mock Provider so we don't need a Gemini API Key!
        tts_provider = MockTTSProvider()
        audio_bytes = await tts_provider.generate_speech(text=full_text)
        
        audio_path = os.path.join(os.getcwd(), "data", f"{job_id}.wav")
        os.makedirs(os.path.dirname(audio_path), exist_ok=True)
        
        with open(audio_path, "wb") as f:
            f.write(audio_bytes)
            
        audio_data = {"audio_path": audio_path}
        supabase.table("videos").update({"audio_metadata": audio_data}).eq("id", job_id).execute()
        logger.info(f"[{job_id}] Stage 3 Complete! Mock audio saved to {audio_path}")

        # =====================================================================================
        # STAGE 4: Alignment (WhisperX)
        current_stage = "alignment"
        supabase.table("videos").update({"status": "aligning_timestamps"}).eq("id", job_id).execute()
        
        logger.info(f"[{job_id}] Running Stage 4: WhisperX Alignment...")
        aligner = AlignmentService()
        
        # 1. Create the AudioTrack object that Osama's code strictly requires
        audio_track = AudioTrack(
            audio_id=job_id,
            audio_path=audio_path,
            language="en"
        )
        
        # 2. Pass the script, the AudioTrack object, and the job_id exactly as Osama defined it
        timestamp_data = await asyncio.to_thread(
            aligner.align, 
            script=script_data, 
            audio_track=audio_track, 
            video_id=job_id
        )
        
        # Save the returned timestamps to the database
        timestamp_dict = timestamp_data.model_dump() if hasattr(timestamp_data, 'model_dump') else timestamp_data
        supabase.table("videos").update({"timestamp_data": timestamp_dict}).eq("id", job_id).execute()
        logger.info(f"[{job_id}] Stage 4 Complete!")

        # =====================================================================================
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
        # We inject the current_stage into the error message!
        error_message = f"[{current_stage}] {str(e)}"
        
        logger.error(f"Pipeline Failed for Job {job_id}: {error_message}")
        supabase.table("videos").update({
            "status": "failed", 
            "error_message": error_message
        }).eq("id", job_id).execute()