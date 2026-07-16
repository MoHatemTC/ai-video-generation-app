"""
Video job routes (PRD 7.10 - Web App & Job Management).

Flow:
  POST   /videos              -> create job, run script stage, return job (status=awaiting_review)
  GET    /videos/{id}         -> poll status + stage detail
  POST   /videos/{id}/approve -> user approves the script; background task runs stages 2-8
  GET    /videos/{id}/download-> stream the final mp4 once status == completed
"""
import json
import os

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from backend.db import get_db
from backend.models.db_models import Video, VideoStatus
from backend.models.video import ScriptReviewRequest, VideoCreateRequest, VideoStatusResponse
from backend.services import pipeline

router = APIRouter(prefix="/videos", tags=["videos"])


@router.post("", response_model=VideoStatusResponse, status_code=201)
async def create_video(payload: VideoCreateRequest, db: Session = Depends(get_db)):
    video = Video(
        instruction=payload.instruction,
        tone=payload.tone,
        audience=payload.audience,
        length_minutes=payload.length_minutes,
        status=VideoStatus.QUEUED,
    )
    db.add(video)
    db.commit()
    db.refresh(video)

    try:
        pipeline.run_script_stage(db, video)
    except Exception as exc:
        video.status = VideoStatus.FAILED
        video.error_message = str(exc)
        db.commit()

    return _to_status_response(video)


@router.get("/{video_id}", response_model=VideoStatusResponse)
async def get_video_status(video_id: str, db: Session = Depends(get_db)):
    video = db.get(Video, video_id)
    if not video:
        raise HTTPException(status_code=404, detail="Video job not found")
    return _to_status_response(video)


@router.get("/{video_id}/script")
async def get_video_script(video_id: str, db: Session = Depends(get_db)):
    """Lets the frontend show the script for human review before rendering (PRD 6.2)."""
    video = db.get(Video, video_id)
    if not video:
        raise HTTPException(status_code=404, detail="Video job not found")
    if not video.script_json:
        raise HTTPException(status_code=409, detail="Script not generated yet")
    return json.loads(video.script_json)


@router.post("/{video_id}/approve", response_model=VideoStatusResponse)
async def approve_script(
    video_id: str,
    background_tasks: BackgroundTasks,
    payload: ScriptReviewRequest | None = None,
    db: Session = Depends(get_db),
):
    video = db.get(Video, video_id)
    if not video:
        raise HTTPException(status_code=404, detail="Video job not found")
    if video.status != VideoStatus.AWAITING_REVIEW:
        raise HTTPException(status_code=409, detail=f"Video is in status '{video.status}', not awaiting review")

    if payload and payload.approved_script_json:
        video.script_json = payload.approved_script_json  # user edited the script (PRD 6.2)
        db.commit()

    background_tasks.add_task(_run_rest_in_new_session, video_id)
    video.status = VideoStatus.PLANNING
    db.commit()
    db.refresh(video)
    return _to_status_response(video)


@router.get("/{video_id}/download")
async def download_video(video_id: str, db: Session = Depends(get_db)):
    video = db.get(Video, video_id)
    if not video:
        raise HTTPException(status_code=404, detail="Video job not found")
    if video.status != VideoStatus.COMPLETED or not video.output_path or not os.path.exists(video.output_path):
        raise HTTPException(status_code=409, detail="Video is not ready for download yet")
    return FileResponse(video.output_path, media_type="video/mp4", filename=f"{video_id}.mp4")


def _run_rest_in_new_session(video_id: str):
    """Background tasks need their own DB session (the request-scoped one is closed by then)."""
    from backend.db import SessionLocal

    db = SessionLocal()
    try:
        video = db.get(Video, video_id)
        if video:
            pipeline.run_rest_of_pipeline(db, video)
    finally:
        db.close()


def _to_status_response(video: Video) -> VideoStatusResponse:
    output_url = f"/videos/{video.id}/download" if video.status == VideoStatus.COMPLETED else None
    return VideoStatusResponse(
        id=video.id,
        status=video.status,
        stage_detail=video.status.value,
        error_message=video.error_message,
        output_url=output_url,
    )
