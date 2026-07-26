import asyncio
import logging
import os
from supabase import Client
import supabase

# --- THE HEALTHY INTEGRATIONS ---
from backend.app.services.script_agent import generate_script
from backend.app.services.tts_provider import GeminiTTSProvider
from backend.app.services.alignment import AlignmentService
from backend.app.schemas.timestamps import AudioTrack
from backend.app.services.assets.images import process_scene_elements


logger = logging.getLogger(__name__)

# --- DUMMY PLACEHOLDER ---
# Mostafa's Scene Planner (Still waiting for his real code)
async def run_planner_crew_sync(script_dict: dict) -> dict:
    """
    A robust mock that respects the ScenePlanBlueprint contract.
    """
    return {
    "video_id": "dummy_video_123",
        "scenes": [
            {
                "scene_id": "scene_1",
                "layout_hint": "title-card",
                "script_segments": ["s1"],
                "visual_elements": [
                {"element_type": "image", "description": "Educational diagram", "cue_id": "cue_1"}
                ]
            }
        ]
    }

# --- THE MAIN BRAIN ---
async def process_video_job(job_id: str, prompt: str, supabase: Client):
    current_stage = "init"
    
    try:
        logger.info(f"Starting pipeline for Job: {job_id}")

        # STAGE 1: Script Generation (Ahmed)
        current_stage = "script_generation"
        supabase.table("videos").update({"status": "generating_script"}).eq("id", job_id).execute()
        logger.info(f"[{job_id}] Running Stage 1: Script Agent...")
        
        script_data = await generate_script(prompt)
        # Handle both Pydantic models and raw dicts gracefully
        script_dict = script_data.model_dump() if hasattr(script_data, 'model_dump') else script_data
        supabase.table("videos").update({"script_data": script_dict}).eq("id", job_id).execute()
        logger.info(f"[{job_id}] Stage 1 Complete!")

        # STAGE 2: Scene Planner (Mostafa)
        current_stage = "planner"
        supabase.table("videos").update({"status": "planning_scenes"}).eq("id", job_id).execute()

        # Run the mock planner
        scene_data = await run_planner_crew_sync(script_dict)

        # Save the raw dictionary directly (no gatekeeper for now)
        supabase.table("videos").update({"scene_data": scene_data}).eq("id", job_id).execute()
        logger.info(f"[{job_id}] Stage 2 Complete (Mock Mode)!")

        # --- STAGE 3: Audio Generation (Mahdy / Real Gemini TTS) ---
        supabase.table("videos").update({"status": "generating_audio"}).eq("id", job_id).execute()        
        # Instantiate with your API key from .env
        tts_provider = GeminiTTSProvider()
        
        # Join Ahmed's script text
        # --- AFTER (Accessing Pydantic attributes directly) ---
        full_script_text = " ".join([seg.narrator_text for seg in script_data.segments])
        
        # Generate real audio
        audio_bytes = await tts_provider.generate_speech(full_script_text)
        
        # HANDSHAKE: Save bytes to disk so Stage 4 (WhisperX) can find it
        audio_path = f"data/{job_id}.wav"
        with open(audio_path, "wb") as f:
            f.write(audio_bytes)
            
        # Update DB with audio metadata
        supabase.table("videos").update({
            "audio_metadata": {"audio_file_path": audio_path, "duration": 0} # Duration can be updated later
        }).eq("id", job_id).execute()

        # STAGE 4: Alignment / WhisperX (Osama)
        current_stage = "alignment"
        supabase.table("videos").update({"status": "aligning_timestamps"}).eq("id", job_id).execute()
        logger.info(f"[{job_id}] Running Stage 4: WhisperX Alignment...")
        
        aligner = AlignmentService()
        audio_track = AudioTrack(audio_id=job_id, audio_path=audio_path, language="en")
        
        timestamp_data = await asyncio.to_thread(
            aligner.align, 
            script=script_data, 
            audio_track=audio_track, 
            video_id=job_id
        )
        
        timestamp_dict = timestamp_data.model_dump() if hasattr(timestamp_data, 'model_dump') else timestamp_data
        supabase.table("videos").update({"timestamp_data": timestamp_dict}).eq("id", job_id).execute()
        logger.info(f"[{job_id}] Stage 4 Complete!")

        # STAGE 5: Assets (Omar El Daly)
        current_stage = "assets"
        supabase.table("videos").update({"status": "fetching_assets"}).eq("id", job_id).execute()
        logger.info(f"[{job_id}] Running Stage 5: Asset Service...")
        
        # Now using Omar El Daly's fixed code!
        asset_data = await process_scene_elements(scene_data)
        
        supabase.table("videos").update({"asset_data": asset_data}).eq("id", job_id).execute()
        logger.info(f"[{job_id}] Stage 5 Complete!")

        # --- ARCHITECTURE PIVOT ---
        # Stages 6 (Composition), 7 (Animation), and 8 (Render) are now handled by the React Frontend!
        # We mark the backend job as fully completed here.
        
        supabase.table("videos").update({
            "status": "completed",
            # We will generate the interactive web URL on the frontend, but we can return a success flag here
            "video_url": "web_render_ready" 
        }).eq("id", job_id).execute()
        
        logger.info(f"Job {job_id} successfully prepared for Web Rendering!")

    except Exception as e:
        error_message = f"[{current_stage}] {str(e)}"
        logger.error(f"Pipeline Failed for Job {job_id}: {error_message}", exc_info=True)
        supabase.table("videos").update({
            "status": "failed", 
            "error_message": error_message
        }).eq("id", job_id).execute()