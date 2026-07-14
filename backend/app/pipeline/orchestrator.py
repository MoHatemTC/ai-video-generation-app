import asyncio
import logging
from typing import Any, Callable
from supabase import Client
from crewai import Agent, Task, Crew, Process
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Stage retry decorator
# Each stage retries up to 3 times with exponential backoff (1s, 2s, 4s).
# This satisfies PRD §7 Must: "each stage handles failures independently
# and can retry without restarting the whole job."
# ---------------------------------------------------------------------------
STAGE_RETRY = retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    retry=retry_if_exception_type((ConnectionError, TimeoutError, OSError)),
    reraise=True,
)

# ---------------------------------------------------------------------------
# Pipeline stage functions (each team member owns one)
# ---------------------------------------------------------------------------

@STAGE_RETRY
def run_transcript_crew_sync(prompt: str) -> dict:
    """Stage 1: Ahmed's CrewAI Setup"""
    # The actual team will define their complex agents here.
    # We use a mock agent structure to represent their Crew.
    script_writer = Agent(
        role='Educational Script Writer',
        goal='Write a structured e-learning script.',
        backstory='Expert instructional designer.',
        allow_delegation=False
    )
    script_task = Task(
        description=f'Write a script for: {prompt}',
        expected_output='A JSON dictionary with "title" and "segments".',
        agent=script_writer
    )
    crew = Crew(agents=[script_writer], tasks=[script_task], process=Process.sequential)
    
    # In reality, this would be: result = crew.kickoff()
    # Returning dummy JSON to match the strict data contract
    return {
        "title": "Generated Topic",
        "segments": [{"id": "seg_1", "text": prompt, "visual_cue": "Intro screen"}]
    }

@STAGE_RETRY
def run_planner_crew_sync(script_data: dict) -> dict:
    """Stage 2: Mostafa's CrewAI Setup"""
    # Mostafa's Crew will run here and analyze the script_data
    return {
        "schema_version": "1.0",
        "video_id": "video_rag_001",
        "scenes": [{"scene_id": "scene_1", "layout_hint": "title_with_center_visual", "script_segment_ids": ["seg_1"]}]
    }

@STAGE_RETRY
def run_voiceover_crew_sync(script_data: dict) -> dict:
    """Stage 3: Mahdy's CrewAI Setup (Using a TTS tool inside the agent)"""
    return {"audio_path": "/tmp/video_001.wav", "language": "en", "duration_seconds": 4.8}

@STAGE_RETRY
def run_alignment_crew_sync(audio_data: dict, script_data: dict) -> dict:
    """Stage 4: Osama's CrewAI Setup (Using a Whisper tool inside the agent)"""
    return {"word_timestamps": [{"word_id": "word_1", "segment_id": "seg_1", "word": "hello", "start_seconds": 0.0, "end_seconds": 0.5}]}

@STAGE_RETRY
def run_asset_crew_sync(scene_data: dict) -> dict:
    """Stage 5: Eldaly's CrewAI Setup (Using image generation tools)"""
    return {"assets": [{"asset_id": "asset_1", "element_type": "diagram", "url": "https://storage.example/diagram.svg"}]}

@STAGE_RETRY
def run_composition_crew_sync(scene_data: dict, asset_data: dict, timestamp_data: dict) -> dict:
    """Stage 6: Nada's CrewAI Setup"""
    return {"schema_version": "1.0", "scenes": [{"scene_id": "scene_1", "layout": "title_with_center_visual"}], "duration_seconds": 4.8}

@STAGE_RETRY
def run_animation_crew_sync(composed_data: dict) -> dict:
    """Stage 7: Animation Engine (CrewAI triggering animation tools)"""
    return {"status": "animation_map_ready"}

@STAGE_RETRY
def run_render_crew_sync(animation_data: dict, audio_data: dict) -> str:
    """Stage 8: Youssef's CrewAI Setup (Using an FFmpeg tool to render)"""
    return "https://s3.bucket/final_educational_video.mp4"

# ---------------------------------------------------------------------------
# Ordered stage definitions — the orchestrator walks through this list.
# ---------------------------------------------------------------------------
# Each tuple: (stage_name, status_label, callable, input_builder, output_key)
# input_builder receives the full `ctx` dict and returns args for the callable.

STAGES = [
    ("transcript",   "generating_script",     run_transcript_crew_sync,   lambda ctx: (ctx["prompt"],),                                               "script_data"),
    ("planner",      "planning_scenes",       run_planner_crew_sync,      lambda ctx: (ctx["script_data"],),                                           "scene_data"),
    ("voiceover",    "generating_audio",       run_voiceover_crew_sync,    lambda ctx: (ctx["script_data"],),                                           "audio_metadata"),
    ("alignment",    "aligning_timestamps",    run_alignment_crew_sync,    lambda ctx: (ctx["audio_metadata"], ctx["script_data"]),                      "timestamp_data"),
    ("assets",       "fetching_assets",        run_asset_crew_sync,        lambda ctx: (ctx["scene_data"],),                                            "asset_data"),
    ("composition",  "composing_scenes",       run_composition_crew_sync,  lambda ctx: (ctx["scene_data"], ctx["asset_data"], ctx["timestamp_data"]),    "composition_data"),
    ("animation",    "animating",              run_animation_crew_sync,    lambda ctx: (ctx["composition_data"],),                                      "animation_data"),
    ("render",       "rendering",              run_render_crew_sync,       lambda ctx: (ctx["animation_data"], ctx["audio_metadata"]),                   "render_output"),
]


async def process_video_job(job_id: str, prompt: str, supabase: Client):
    """
    Decoupled, contract-driven stage sequencing.
    Every single stage is executed in a background thread to prevent blocking.

    Known limitation (v1): This runs inside FastAPI BackgroundTasks, which shares
    the server's thread pool. For production workloads with many concurrent renders,
    migrate to a dedicated task queue (Celery + Redis / ARQ) so the API process
    stays responsive.
    """
    ctx: dict[str, Any] = {"prompt": prompt}

    try:
        logger.info(f"Starting CrewAI pipeline for Job: {job_id}")

        for stage_name, status_label, fn, input_builder, output_key in STAGES:
            # Update status BEFORE running so the frontend can show progress
            supabase.table("videos").update({
                "status": status_label,
            }).eq("id", job_id).execute()

            # Run the (blocking) crew call in a background thread
            args = input_builder(ctx)
            result = await asyncio.to_thread(fn, *args)

            # Store the result in context for downstream stages
            ctx[output_key] = result

            # Persist intermediate output (render returns a URL string, not dict)
            if output_key != "render_output":
                supabase.table("videos").update({
                    output_key: result,
                }).eq("id", job_id).execute()

        # COMPLETION
        supabase.table("videos").update({
            "status": "completed",
            "video_url": ctx["render_output"],
        }).eq("id", job_id).execute()
        logger.info(f"Job {job_id} successfully completed!")

    except Exception as e:
        logger.error(f"Pipeline Failed for Job {job_id} at stage '{stage_name}': {e}")
        supabase.table("videos").update({
            "status": "failed",
            "error_message": f"[{stage_name}] {str(e)}",
        }).eq("id", job_id).execute()