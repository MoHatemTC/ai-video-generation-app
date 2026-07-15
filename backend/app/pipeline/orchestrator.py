import asyncio
import logging
from supabase import Client

# Removed the crewai import so the app boots smoothly for everyone!

logger = logging.getLogger(__name__)

def run_transcript_crew_sync(prompt: str) -> dict:
    """Stage 1: Ahmed's Stage (Mocked)"""
    # Returning dummy JSON directly to match the other 7 stages
    return {
        "title": "Generated Topic",
        "segments": [{"id": "seg_1", "text": prompt, "visual_cue": "Intro screen"}]
    }

def run_planner_crew_sync(script_data: dict) -> dict:
    """Stage 2: Mostafa's CrewAI Setup"""
    # Mostafa's Crew will run here and analyze the script_data
    return {
        "schema_version": "1.0",
        "video_id": "video_rag_001",
        "scenes": [{"scene_id": "scene_1", "layout_hint": "title_with_center_visual", "script_segment_ids": ["seg_1"]}]
    }

def run_voiceover_crew_sync(script_data: dict) -> dict:
    """Stage 3: Mahdy's CrewAI Setup (Using a TTS tool inside the agent)"""
    return {"audio_path": "/tmp/video_001.wav", "language": "en", "duration_seconds": 4.8}

def run_alignment_crew_sync(audio_data: dict, script_data: dict) -> dict:
    """Stage 4: Osama's CrewAI Setup (Using a Whisper tool inside the agent)"""
    return {"word_timestamps": [{"word_id": "word_1", "segment_id": "seg_1", "word": "hello", "start_seconds": 0.0, "end_seconds": 0.5}]}

def run_asset_crew_sync(scene_data: dict) -> dict:
    """Stage 5: Eldaly's CrewAI Setup (Using image generation tools)"""
    return {"assets": [{"asset_id": "asset_1", "element_type": "diagram", "url": "https://storage.example/diagram.svg"}]}

def run_composition_crew_sync(scene_data: dict, asset_data: dict, timestamp_data: dict) -> dict:
    """Stage 6: Nada's CrewAI Setup"""
    return {"schema_version": "1.0", "scenes": [{"scene_id": "scene_1", "layout": "title_with_center_visual"}], "duration_seconds": 4.8}

def run_animation_crew_sync(composed_data: dict) -> dict:
    """Stage 7: Animation Engine (CrewAI triggering animation tools)"""
    return {"status": "animation_map_ready"}

def run_render_crew_sync(animation_data: dict, audio_data: dict) -> str:
    """Stage 8: Youssef's CrewAI Setup (Using an FFmpeg tool to render)"""
    return "https://s3.bucket/final_educational_video.mp4"

async def process_video_job(job_id: str, prompt: str, supabase: Client):
    """
    Decoupled, contract-driven stage sequencing.
    Every single stage is executed in a background thread to prevent blocking.
    """
    try:
        logger.info(f"Starting CrewAI pipeline for Job: {job_id}")

        # STAGE 1: Transcript 
        supabase.table("videos").update({"status": "generating_script"}).eq("id", job_id).execute()
        script_data = await asyncio.to_thread(run_transcript_crew_sync, prompt)
        supabase.table("videos").update({"script_data": script_data}).eq("id", job_id).execute()

        # STAGE 2: Planner 
        supabase.table("videos").update({"status": "planning_scenes"}).eq("id", job_id).execute()
        scene_data = await asyncio.to_thread(run_planner_crew_sync, script_data)
        supabase.table("videos").update({"scene_data": scene_data}).eq("id", job_id).execute()

        # STAGE 3: Voiceover
        supabase.table("videos").update({"status": "generating_audio"}).eq("id", job_id).execute()
        audio_data = await asyncio.to_thread(run_voiceover_crew_sync, script_data)
        supabase.table("videos").update({"audio_metadata": audio_data}).eq("id", job_id).execute()

        # STAGE 4: Alignment 
        supabase.table("videos").update({"status": "aligning_timestamps"}).eq("id", job_id).execute()
        timestamp_data = await asyncio.to_thread(run_alignment_crew_sync, audio_data, script_data)
        supabase.table("videos").update({"timestamp_data": timestamp_data}).eq("id", job_id).execute()

        # STAGE 5: Assets
        supabase.table("videos").update({"status": "fetching_assets"}).eq("id", job_id).execute()
        asset_data = await asyncio.to_thread(run_asset_crew_sync, scene_data)
        supabase.table("videos").update({"asset_data": asset_data}).eq("id", job_id).execute()

        # STAGE 6: Composition 
        supabase.table("videos").update({"status": "composing_scenes"}).eq("id", job_id).execute()
        comp_data = await asyncio.to_thread(run_composition_crew_sync, scene_data, asset_data, timestamp_data)
        supabase.table("videos").update({"composition_data": comp_data}).eq("id", job_id).execute()
        
        # STAGE 7: Animation
        supabase.table("videos").update({"status": "animating"}).eq("id", job_id).execute()
        anim_data = await asyncio.to_thread(run_animation_crew_sync, comp_data)
        supabase.table("videos").update({"animation_data": anim_data}).eq("id", job_id).execute()

        # STAGE 8: Render
        supabase.table("videos").update({"status": "rendering"}).eq("id", job_id).execute()
        video_url = await asyncio.to_thread(run_render_crew_sync, anim_data, audio_data)
        
        # COMPLETION
        supabase.table("videos").update({
            "status": "completed",
            "video_url": video_url
        }).eq("id", job_id).execute()
        logger.info(f"Job {job_id} successfully completed!")

    except Exception as e:
        logger.error(f"Pipeline Failed for Job {job_id}: {e}")
        supabase.table("videos").update({
            "status": "failed", 
            "error_message": str(e)
        }).eq("id", job_id).execute()