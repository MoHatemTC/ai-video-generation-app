import os
import asyncio
import logging
from supabase import Client

# --- THE HEALTHY INTEGRATIONS ---
from backend.app.services.script_agent import generate_script
from backend.app.schemas.script import VideoScriptBlueprint
from backend.app.services.tts_provider import MockTTSProvider
from backend.app.services.alignment import AlignmentService
from backend.app.schemas.timestamps import AudioTrack

# --- PLUGGING IN OMAR EL DALY'S CODE ---
from backend.app.services.assets.images import process_scene_elements

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

# --- DUMMY PLACEHOLDERS (Replace these as teammates finish) ---

def run_planner_crew_sync(script_data: dict) -> dict:
    # Updated to pass a fake image request so Omar's code actually triggers!
    return {
        "schema_version": "1.0", 
        "scenes": [
            {
                "scene_id": "scene_1",
                "visual_elements": [{"element_type": "image", "description": "A futuristic computer server"}]
            }
        ]
    }

def run_composition_crew_sync(scene_data: dict, asset_data: dict, timestamp_data: dict) -> dict:
    return {"scenes": []}

def run_animation_crew_sync(composed_data: dict) -> dict:
    return {"status": "animation_map_ready"}

def run_render_crew_sync(animation_data: dict, audio_data: dict) -> str:
    return "https://storage.example/video.mp4"

# --- THE MAIN BRAIN ---

async def process_video_job(job_id: str, prompt: str, supabase: Client):
    current_stage = "init"
    
    try:
        logger.info(f"Starting pipeline for Job: {job_id}")

        # STAGE 1: Script Generation (INTEGRATED)
        current_stage = "script_generation"
        supabase.table("videos").update({"status": "generating_script"}).eq("id", job_id).execute()
        logger.info(f"[{job_id}] Running Stage 1: Script Agent...")
        
        script_data: VideoScriptBlueprint = await generate_script(prompt)
        supabase.table("videos").update({"script_data": script_data.model_dump()}).eq("id", job_id).execute()
        logger.info(f"[{job_id}] Stage 1 Complete!")

        # STAGE 2: Scene Planner (WAITING FOR MOSTAFA)
        current_stage = "planner"
        supabase.table("videos").update({"status": "planning_scenes"}).eq("id", job_id).execute()
        scene_data = await asyncio.to_thread(run_planner_crew_sync, script_data)
        supabase.table("videos").update({"scene_data": scene_data}).eq("id", job_id).execute()

        # STAGE 3: Voiceover / TTS (INTEGRATED)
        current_stage = "voiceover"
        supabase.table("videos").update({"status": "generating_audio"}).eq("id", job_id).execute()
        logger.info(f"[{job_id}] Running Stage 3: Audio Generation...")
        
        script_dict = script_data.model_dump()
        full_text = " ".join([seg["narrator_text"] for seg in script_dict["segments"]])
        
        tts_provider = MockTTSProvider()
        audio_bytes = await tts_provider.generate_speech(text=full_text)
        
        audio_path = os.path.join(os.getcwd(), "data", f"{job_id}.wav")
        os.makedirs(os.path.dirname(audio_path), exist_ok=True)
        with open(audio_path, "wb") as f:
            f.write(audio_bytes)
            
        audio_data = {"audio_path": audio_path}
        supabase.table("videos").update({"audio_metadata": audio_data}).eq("id", job_id).execute()
        logger.info(f"[{job_id}] Stage 3 Complete!")

        # STAGE 4: Alignment / WhisperX (INTEGRATED)
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

        # STAGE 5: Assets (INTEGRATED - OMAR EL DALY)
        current_stage = "assets"
        supabase.table("videos").update({"status": "fetching_assets"}).eq("id", job_id).execute()
        logger.info(f"[{job_id}] Running Stage 5: Asset Service...")
        
        # Calling Omar El Daly's real function! 
        # Since he wrote it as an async function, we MUST await it directly. Do NOT use to_thread.
        asset_data = await process_scene_elements(scene_data)
        
        supabase.table("videos").update({"asset_data": asset_data}).eq("id", job_id).execute()
        logger.info(f"[{job_id}] Stage 5 Complete!")

        # STAGE 6: Composition (WAITING FOR NADA)
        current_stage = "composition"
        supabase.table("videos").update({"status": "composing_scenes"}).eq("id", job_id).execute()
        comp_data = await asyncio.to_thread(run_composition_crew_sync, scene_data, asset_data, timestamp_data)
        supabase.table("videos").update({"composition_data": comp_data}).eq("id", job_id).execute()
        
        # STAGE 7: Animation (WAITING FOR YOUSSEF)
        current_stage = "animation"
        supabase.table("videos").update({"status": "animating"}).eq("id", job_id).execute()
        anim_data = await asyncio.to_thread(run_animation_crew_sync, comp_data)
        supabase.table("videos").update({"animation_data": anim_data}).eq("id", job_id).execute()

        # STAGE 8: Render Engine (WAITING FOR YOUSSEF)
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
        error_message = f"[{current_stage}] {str(e)}"
        logger.error(f"Pipeline Failed for Job {job_id}: {error_message}")
        supabase.table("videos").update({
            "status": "failed", 
            "error_message": error_message
        }).eq("id", job_id).execute()