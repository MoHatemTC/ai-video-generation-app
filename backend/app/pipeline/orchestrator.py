import asyncio
import logging
import os
import uuid
from typing import Dict, Any, Optional
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


def _safe_db_update(supabase_client: Optional[Client], table: str, payload: dict, job_id: str):
    """Safely perform DB updates if Supabase client is available."""
    if supabase_client:
        try:
            supabase_client.table(table).update(payload).eq("id", job_id).execute()
        except Exception as err:
            logger.warning(f"[{job_id}] DB update failed (non-critical): {err}")


async def process_video_job(
    prompt: str,
    job_id: Optional[str] = None,
    supabase_client: Optional[Client] = None
) -> Dict[str, Any]:
    # Auto-generate job_id if not supplied
    job_id = job_id or str(uuid.uuid4())

    current_stage = "init"
    result_payload: Dict[str, Any] = {
        "job_id": job_id,
        "status": "pending",
        "script_data": None,
        "scene_data": None,
        "audio_metadata": None,
        "timestamp_data": None,
        "asset_data": None,
        "video_url": None,
        "error_message": None
    }

    try:
        logger.info(f"Starting pipeline for Job: {job_id}")

        # STAGE 1: Script Generation
        current_stage = "script_generation"
        _safe_db_update(supabase_client, "videos", {"status": "generating_script"}, job_id)
        logger.info(f"[{job_id}] Running Stage 1: Script Agent...")

        script_data = await generate_script(prompt)
        if hasattr(script_data, 'model_dump'):
            script_dict: dict[str, Any] = script_data.model_dump()
        else:
            script_dict = dict(script_data)
        script_dict["video_id"] = job_id
        result_payload["script_data"] = script_dict
        _safe_db_update(supabase_client, "videos", {"script_data": script_dict}, job_id)
        logger.info(f"[{job_id}] Stage 1 Complete!")

        # STAGE 2: Scene Planner & Director
        current_stage = "planner"
        _safe_db_update(supabase_client, "videos", {"status": "planning_scenes"}, job_id)

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

        scene_plan_pydantic = await planner_agent.plan_scenes(script_dict)

        logger.info(f"[{job_id}] Evaluating scene plan quality...")
        quality_report = await director_agent.evaluate(script_dict, scene_plan_pydantic)

        if not quality_report.passed:
            logger.info(f"[{job_id}] Quality check failed (Score: {quality_report.overall_score}). Revising...")
            scene_plan_pydantic = await planner_agent.revise_scenes(
                script_dict, scene_plan_pydantic, quality_report
            )
            logger.info(f"[{job_id}] Revision complete.")
        else:
            logger.info(f"[{job_id}] Quality check passed (Score: {quality_report.overall_score})!")

        scene_data_dict = scene_plan_pydantic.model_dump()
        result_payload["scene_data"] = scene_data_dict
        _safe_db_update(supabase_client, "videos", {"scene_data": scene_data_dict}, job_id)
        logger.info(f"[{job_id}] Stage 2 Complete!")

        # STAGE 3: Audio Generation
        current_stage = "audio"
        _safe_db_update(supabase_client, "videos", {"status": "generating_audio"}, job_id)

        audio_metadata = await generate_voiceover(
            script_data=script_dict,
            supabase_client=supabase_client
        )

        audio_path: str = str(audio_metadata.get("local_path") or audio_metadata.get("audio_file_path") or "")
        result_payload["audio_metadata"] = audio_metadata
        _safe_db_update(supabase_client, "videos", {"audio_metadata": audio_metadata}, job_id)
        logger.info(f"[{job_id}] Stage 3 Complete!")

        # STAGE 4: Alignment / WhisperX
        current_stage = "alignment"
        _safe_db_update(supabase_client, "videos", {"status": "aligning_timestamps"}, job_id)

        aligner = AlignmentService()
        audio_track = AudioTrack(audio_id=job_id, audio_path=audio_path, language="en")

        timestamp_data = await asyncio.to_thread(
            aligner.align,
            script=script_data,
            audio_track=audio_track,
            video_id=job_id
        )

        if hasattr(timestamp_data, 'model_dump'):
            timestamp_dict: dict[str, Any] = timestamp_data.model_dump()
        else:
            timestamp_dict = dict(timestamp_data)
        result_payload["timestamp_data"] = timestamp_dict
        _safe_db_update(supabase_client, "videos", {"timestamp_data": timestamp_dict}, job_id)
        logger.info(f"[{job_id}] Stage 4 Complete!")

        # STAGE 5: Assets
        current_stage = "assets"
        _safe_db_update(supabase_client, "videos", {"status": "fetching_assets"}, job_id)
        logger.info(f"[{job_id}] Running Stage 5: Asset Service...")

        asset_data = await process_scene_elements(scene_data_dict, supabase_client=supabase_client)
        result_payload["asset_data"] = asset_data
        _safe_db_update(supabase_client, "videos", {"asset_data": asset_data}, job_id)
        logger.info(f"[{job_id}] Stage 5 Complete!")

        # STAGE 6: Render Engine
        current_stage = "render"
        _safe_db_update(supabase_client, "videos", {"status": "rendering"}, job_id)
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
        result_payload["video_url"] = video_url
        result_payload["status"] = "completed"
        logger.info(f"[{job_id}] Stage 6 Complete!")

        _safe_db_update(supabase_client, "videos", {
            "status": "completed",
            "video_url": video_url
        }, job_id)

        logger.info(f"Job {job_id} successfully completed!")
        return result_payload

    except Exception as e:
        error_message = f"[{current_stage}] {str(e)}"
        logger.error(f"Pipeline Failed for Job {job_id}: {error_message}", exc_info=True)
        result_payload["status"] = "failed"
        result_payload["error_message"] = error_message
        _safe_db_update(supabase_client, "videos", {
            "status": "failed",
            "error_message": error_message
        }, job_id)
        return result_payload
