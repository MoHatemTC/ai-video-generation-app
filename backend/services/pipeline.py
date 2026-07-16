"""
Pipeline orchestrator: runs stages in sequence, persisting status + every
intermediate artifact to the `videos` row after each stage (PRD 7.11 /
architecture.md "Job Management"). Each stage's failure is caught and
recorded on the row as FAILED + error_message instead of crashing the
worker, matching the "each stage handles failures independently" NFR.
"""
import logging
import os

from sqlalchemy.orm import Session

from backend.models.db_models import Video, VideoStatus
from backend.models.scene import ScenePlan
from backend.models.script import VideoScriptBlueprint
from backend.models.timeline import AssetManifest, TimestampMap
from backend.services import animation, assets, audio, captions, composition, planner, render, transcript

logger = logging.getLogger(__name__)

STORAGE_DIR = os.getenv("STORAGE_DIR", "./storage")


def _set_status(db: Session, video: Video, status: VideoStatus):
    video.status = status
    db.commit()
    db.refresh(video)


def _job_dir(video_id: str) -> str:
    path = os.path.join(STORAGE_DIR, video_id)
    os.makedirs(path, exist_ok=True)
    return path


def run_script_stage(db: Session, video: Video) -> VideoScriptBlueprint:
    """Stage 1: instruction -> script. Stops here for human review (PRD 6.2)."""
    _set_status(db, video, VideoStatus.SCRIPT)
    script = transcript.generate_segmented_script(
        instruction=video.instruction,
        tone=video.tone,
        audience=video.audience,
        length_minutes=video.length_minutes,
    )
    video.script_json = script.model_dump_json()
    _set_status(db, video, VideoStatus.AWAITING_REVIEW)
    return script


def run_rest_of_pipeline(db: Session, video: Video):
    """Stages 2-8: scene plan -> ... -> final render. Called after script approval."""
    try:
        job_dir = _job_dir(video.id)
        script = VideoScriptBlueprint.model_validate_json(video.script_json)

        _set_status(db, video, VideoStatus.PLANNING)
        scene_plan = planner.plan_scenes(script)
        video.scene_plan_json = scene_plan.model_dump_json()
        db.commit()

        _set_status(db, video, VideoStatus.AUDIO)
        audio_path = audio.generate_voiceover(script, job_dir)
        video.audio_path = audio_path
        db.commit()

        _set_status(db, video, VideoStatus.ALIGNMENT)
        timestamp_map = animation_align(script, audio_path)
        video.timestamps_json = timestamp_map.model_dump_json()
        db.commit()

        srt_path = captions.generate_srt(script, timestamp_map, os.path.join(job_dir, "captions.srt"))
        video.captions_path = srt_path

        _set_status(db, video, VideoStatus.ASSETS)
        asset_manifest = assets.resolve_assets(scene_plan, os.path.join(job_dir, "assets"))
        video.assets_json = asset_manifest.model_dump_json()
        db.commit()

        _set_status(db, video, VideoStatus.COMPOSITION)
        composed = composition.compose_scenes(scene_plan, asset_manifest)
        video.composition_json = _to_json(composed)
        db.commit()

        _set_status(db, video, VideoStatus.ANIMATION)
        animated = animation.sync_animation(composed, timestamp_map)
        video.animation_json = _to_json(animated)
        db.commit()

        _set_status(db, video, VideoStatus.RENDERING)
        output_path = os.path.join(job_dir, "final_video.mp4")
        render.render_video(animated, audio_path, srt_path, output_path)
        video.output_path = output_path

        _set_status(db, video, VideoStatus.COMPLETED)
    except Exception as exc:
        logger.exception("Pipeline failed for video %s", video.id)
        video.status = VideoStatus.FAILED
        video.error_message = str(exc)
        db.commit()
        raise


def animation_align(script, audio_path) -> TimestampMap:
    from backend.services import alignment
    return alignment.align_audio_to_script(script, audio_path)


def _to_json(obj: dict) -> str:
    import json
    return json.dumps(obj)
