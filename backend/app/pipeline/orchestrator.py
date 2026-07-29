import os
import asyncio
import logging
from supabase import create_client

# --- THE HEALTHY INTEGRATIONS ---
from backend.app.services.script_agent import generate_script
from backend.app.schemas.script import VideoScriptBlueprint
from backend.app.services.tts_provider import MockTTSProvider
from backend.app.services.alignment import AlignmentService
from backend.app.schemas.timestamps import AudioTrack

# --- PLUGGING IN OMAR EL DALY'S CODE ---
from backend.app.services.assets.images import process_scene_elements
from backend.app.pipeline.render.render_custom import generate_video_html

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

# --- DUMMY PLACEHOLDERS (Replace these as teammates finish) ---

def run_planner_crew_sync(script_data: dict) -> dict:
    return {
        "schema_version": "1.0",
        "video_id": "demo_job_id",
        "title": "AI Video Explainer",
        "total_duration_seconds": 30.0,
        "scenes": [
            {
                "scene_id": "scene_1",
                "text": "Welcome to our AI video generation platform.",
                "script_segment_ids": ["seg_1"],
                "layout_hint": "title-card",
                "visual_cues": [
                    {
                        "cue_id": "cue_1",
                        "description": "A futuristic computer server",
                        "element_type": "image",
                        "asset_id": "image_1",
                        "linked_segment_id": "seg_1",
                        "appearance_trigger": {"type": "segment_start"},
                        "preferred_region": "center",
                        "importance": "primary",
                        "trigger_time_seconds": 0.0
                    }
                ]
            }
        ]
    }

def run_composition_crew_sync(scene_data: dict, asset_data: dict, timestamp_data: dict) -> dict:
    return {"scenes": []}

def run_animation_crew_sync(composed_data: dict) -> dict:
    return {"status": "animation_map_ready"}

def run_render_crew_sync(scene_data: dict, asset_data: dict) -> str:
    rendered_html = generate_video_html(scene_data, asset_data)
    output_dir = os.path.join(os.getcwd(), "data", "renders")
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, "rendered_output.html")
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(rendered_html)
    return output_path

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

        # STAGE 8: Render Engine
        current_stage = "render"
        supabase.table("videos").update({"status": "rendering"}).eq("id", job_id).execute()
        video_url = await asyncio.to_thread(run_render_crew_sync, scene_data, asset_data)
        
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


if __name__ == "__main__":
    from dotenv import load_dotenv
    import sys

    load_dotenv()

    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_KEY")

    prompt = sys.argv[1] if len(sys.argv) > 1 else "How black holes work in space"

    if not supabase_url or not supabase_key:
        logger.error("SUPABASE_URL and SUPABASE_KEY must be set in your .env file.")
        sys.exit(1)

    supabase_client = create_client(supabase_url, supabase_key)

    logger.info(f"Creating video job for prompt: '{prompt}'")
    insert_res = supabase_client.table("videos").insert({"prompt": prompt, "status": "pending"}).execute()

    if not insert_res.data or len(insert_res.data) == 0:
        logger.error("Failed to create video job in Supabase.")
        sys.exit(1)

    job_id = insert_res.data[0]["id"]
    logger.info(f"Job created with ID: {job_id}")

    asyncio.run(process_video_job(job_id, prompt, supabase_client))
