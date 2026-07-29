import asyncio
import logging
import os
from supabase import Client
import supabase

# --- THE HEALTHY INTEGRATIONS ---
from backend.app.services.script_agent import generate_script
from backend.app.services.audio import generate_voiceover
from backend.app.services.alignment import AlignmentService
from backend.app.schemas.timestamps import AudioTrack
from backend.app.services.assets.images import process_scene_elements
from backend.app.agents.planner import ScenePlanner
from backend.app.agents.director import SceneDirector
from backend.app.pipeline.render.render_custom import generate_video_html

from backend.app.config.model_config import get_planner_config, get_fallback_config

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
        script_dict["video_id"] = job_id
        supabase.table("videos").update({"script_data": script_dict}).eq("id", job_id).execute()
        logger.info(f"[{job_id}] Stage 1 Complete!")
        #################################################################################################
        # --- STAGE 2: Scene Planner (Mostafa's Real Code) ---
        current_stage = "planner"
        supabase.table("videos").update({"status": "planning_scenes"}).eq("id", job_id).execute()
        
        # 1. Instantiate the agents with primary and fallback configs
        primary_config = get_planner_config()
        fallback_config = get_fallback_config()
        
        planner_agent = ScenePlanner(
            model_name=primary_config["model_name"],
            api_key=primary_config["api_key"],
            base_url=primary_config["base_url"],
            fallback_config=fallback_config
        )
        
        director_agent = SceneDirector(
            model_name=primary_config["model_name"],
            api_key=primary_config["api_key"],
            base_url=primary_config["base_url"],
            fallback_config=fallback_config
        )
        
        # 2. Plan the scenes
        scene_plan_pydantic = await planner_agent.plan_scenes(script_dict)
        
        # 3. Evaluate Quality
        logger.info(f"[{job_id}] Evaluating scene plan quality...")
        quality_report = await director_agent.evaluate(script_dict, scene_plan_pydantic)
        
        # 4. Revise if failed
        if not quality_report.passed:
            logger.info(f"[{job_id}] Quality check failed (Score: {quality_report.overall_score}). Revising...")
            scene_plan_pydantic = await planner_agent.revise_scenes(
                script_dict, scene_plan_pydantic, quality_report
            )
            logger.info(f"[{job_id}] Revision complete.")
        else:
            logger.info(f"[{job_id}] Quality check passed (Score: {quality_report.overall_score})!")
        
        # 5. Convert to dict and save
        scene_data_dict = scene_plan_pydantic.model_dump()
        supabase.table("videos").update({"scene_data": scene_data_dict}).eq("id", job_id).execute()
        logger.info(f"[{job_id}] Stage 2 Complete!")

        # --- STAGE 3: Audio Generation ---
        current_stage = "audio"
        supabase.table("videos").update({"status": "generating_audio"}).eq("id", job_id).execute()
        # Use AudioService for caching and Supabase upload
        audio_metadata = await generate_voiceover(
            script_data=script_dict,
            supabase_client=supabase
        )
        
        # Keep local path reference for AlignmentService (Stage 4)
        audio_path = audio_metadata.get("local_path", audio_metadata.get("audio_file_path", ""))
        
        supabase.table("videos").update({
            "audio_metadata": audio_metadata
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
        asset_data = await process_scene_elements(scene_data_dict, supabase_client=supabase)
        
        supabase.table("videos").update({"asset_data": asset_data}).eq("id", job_id).execute()
        logger.info(f"[{job_id}] Stage 5 Complete!")
        #################################################################################################
        # --- STAGE 6: Render Engine ---
        current_stage = "render"
        supabase.table("videos").update({"status": "rendering"}).eq("id", job_id).execute()
        logger.info(f"[{job_id}] Running Stage 6: Render Engine...")

        def _render_to_html(scene_data: dict, asset_data: dict) -> str:
            rendered_html = generate_video_html(scene_data, asset_data)
            output_dir = os.path.join(os.getcwd(), "data", "renders")
            os.makedirs(output_dir, exist_ok=True)
            output_path = os.path.join(output_dir, f"{job_id}.html")
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(rendered_html)
            return output_path

        video_url = await asyncio.to_thread(_render_to_html, scene_data_dict, asset_data)
        logger.info(f"[{job_id}] Stage 6 Complete!")

        supabase.table("videos").update({
            "status": "completed",
            "video_url": video_url
        }).eq("id", job_id).execute()
        
        logger.info(f"Job {job_id} successfully completed!")

    except Exception as e:
        error_message = f"[{current_stage}] {str(e)}"
        logger.error(f"Pipeline Failed for Job {job_id}: {error_message}", exc_info=True)
        supabase.table("videos").update({
            "status": "failed", 
            "error_message": error_message
        }).eq("id", job_id).execute()