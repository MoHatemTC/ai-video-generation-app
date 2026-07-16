"""
Full pipeline integration test.

Only the two paid-API calls (LLM script generation, LLM scene planning,
TTS voiceover) are mocked -- everything else (alignment heuristic, asset
generation, composition, animation sync, SRT captions, ffmpeg render) runs
for real, producing an actual playable .mp4 on disk. This is the strongest
evidence the 8-stage pipeline is genuinely wired together end-to-end.
"""
import os
import subprocess
from unittest.mock import patch

import pytest

from backend.models.db_models import Video, VideoStatus
from backend.models.scene import Scene, ScenePlan, VisualElement
from backend.models.script import ScriptSegment, VideoScriptBlueprint
from backend.services import pipeline


def _fake_script():
    return VideoScriptBlueprint(
        title="How Plants Make Food",
        target_audience="general",
        estimated_total_duration=6,
        segments=[
            ScriptSegment(segment_id=1, text="Plants absorb sunlight to create energy",
                          visual_cues="sun icon", duration_seconds=3),
            ScriptSegment(segment_id=2, text="This process is called photosynthesis",
                          visual_cues="leaf diagram", duration_seconds=3),
        ],
    )


def _fake_scene_plan():
    return ScenePlan(scenes=[
        Scene(scene_id=1, layout="image_focus", elements=[
            VisualElement(element_id="e1", concept="sunlight", asset_type="icon", appear_at_word="sunlight"),
        ]),
        Scene(scene_id=2, layout="diagram_focus", elements=[
            VisualElement(element_id="e2", concept="photosynthesis", asset_type="diagram",
                          appear_at_word="photosynthesis"),
        ]),
    ])


def _fake_generate_voiceover(script, output_dir, voice="alloy"):
    os.makedirs(output_dir, exist_ok=True)
    out_path = os.path.join(output_dir, "voiceover.mp3")
    subprocess.run(
        ["ffmpeg", "-y", "-f", "lavfi", "-i", "anullsrc=r=44100:cl=mono", "-t", "6", out_path],
        check=True, capture_output=True,
    )
    return out_path


@pytest.mark.skipif(subprocess.run(["which", "ffmpeg"], capture_output=True).returncode != 0,
                     reason="ffmpeg not installed")
def test_full_pipeline_produces_final_video(db_session, tmp_path, monkeypatch):
    monkeypatch.setenv("STORAGE_DIR", str(tmp_path))
    monkeypatch.setattr(pipeline, "STORAGE_DIR", str(tmp_path))

    video = Video(instruction="I want a video about photosynthesis", status=VideoStatus.QUEUED)
    db_session.add(video)
    db_session.commit()
    db_session.refresh(video)

    with patch("backend.services.transcript.structured_completion", return_value=_fake_script()):
        pipeline.run_script_stage(db_session, video)

    assert video.status == VideoStatus.AWAITING_REVIEW
    assert video.script_json is not None

    with patch("backend.services.planner.structured_completion", return_value=_fake_scene_plan()), \
         patch("backend.services.audio.generate_voiceover", side_effect=_fake_generate_voiceover):
        pipeline.run_rest_of_pipeline(db_session, video)

    assert video.status == VideoStatus.COMPLETED
    assert video.output_path and os.path.exists(video.output_path)
    assert os.path.getsize(video.output_path) > 1000
    assert video.captions_path and os.path.exists(video.captions_path)

    # sanity check the final mp4 duration matches the heuristic-aligned script duration (~6s)
    probe = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of",
         "default=noprint_wrappers=1:nokey=1", video.output_path],
        capture_output=True, text=True, check=True,
    )
    duration = float(probe.stdout.strip())
    assert 4.0 <= duration <= 8.0
