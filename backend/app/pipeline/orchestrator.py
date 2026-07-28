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
from backend.app.agents.planner import ScenePlanner

from backend.app.config.model_config import get_planner_config

logger = logging.getLogger(__name__)

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
        #################################################################################################
        # --- STAGE 2: Scene Planner (Mostafa's Real Code) ---
        current_stage = "planner"
        supabase.table("videos").update({"status": "planning_scenes"}).eq("id", job_id).execute()
        
        # 1. Instantiate the agent first!
        planner_agent = ScenePlanner(
            model_name=get_planner_config()["model_name"],
            api_key=get_planner_config()["api_key"],
            base_url=get_planner_config()["base_url"]
        )
        
        # 2. Now await the scene planning
        scene_plan_pydantic = await planner_agent.plan_scenes(script_dict)
        
        # 3. Convert to dict and save
        scene_data_dict = scene_plan_pydantic.model_dump()
        supabase.table("videos").update({"scene_data": scene_data_dict}).eq("id", job_id).execute()
        logger.info(f"[{job_id}] Stage 2 Complete!")

        # --- STAGE 3: Audio Generation ---
        supabase.table("videos").update({"status": "generating_audio"}).eq("id", job_id).execute()
        tts_provider = GeminiTTSProvider()
        full_script_text = " ".join([seg.narrator_text for seg in script_data.segments])
        audio_bytes = await tts_provider.generate_speech(full_script_text)
        
        audio_path = f"data/{job_id}.wav"
        os.makedirs("data", exist_ok=True)
        with open(audio_path, "wb") as f:
            f.write(audio_bytes)
            
        supabase.table("videos").update({
            "audio_metadata": {"audio_file_path": audio_path}
        }).eq("id", job_id).execute()

        # STAGE 4: Alignment / WhisperX (Osama)
        current_stage = "alignment"
        supabase.table("videos").update({"status": "aligning_timestamps"}).eq("id", job_id).execute()
        
        aligner = AlignmentService()
        audio_track = AudioTrack(audio_id=job_id, audio_path=audio_path, language="en")
        
        # CORRECTED: Use to_thread to handle synchronous heavy processing
        timestamp_data = await asyncio.to_thread(
            aligner.align, 
            script=script_data, 
            audio_track=audio_track, 
            video_id=job_id
        )
        
        timestamp_dict = timestamp_data.model_dump() if hasattr(timestamp_data, 'model_dump') else timestamp_data
        supabase.table("videos").update({"timestamp_data": timestamp_dict}).eq("id", job_id).execute()
        logger.info(f"[{job_id}] Stage 4 Complete!")
        #################################################################################################
        # --- STAGE 5: Assets (Omar El Daly) ---
        current_stage = "assets"
        supabase.table("videos").update({"status": "fetching_assets"}).eq("id", job_id).execute()
        logger.info(f"[{job_id}] Running Stage 5: Asset Service...")
        
        # FIX: Pass the dictionary (scene_data_dict), NOT the Pydantic object!
        asset_data = await process_scene_elements(scene_data_dict)
        
        supabase.table("videos").update({"asset_data": asset_data}).eq("id", job_id).execute()
        logger.info(f"[{job_id}] Stage 5 Complete!")
        #################################################################################################
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