from backend.models.script import ScriptSegment, VideoScriptBlueprint
from backend.services import alignment


def _fake_script():
    return VideoScriptBlueprint(
        title="T", target_audience="general", estimated_total_duration=10,
        segments=[
            ScriptSegment(segment_id=1, text="Water boils at high temperature",
                          visual_cues="steam", duration_seconds=4),
            ScriptSegment(segment_id=2, text="This is a physical change",
                          visual_cues="molecules", duration_seconds=4),
        ],
    )


def test_heuristic_alignment_without_api_key_still_produces_timestamps():
    # No OPENAI_API_KEY / no audio_path -> must fall back gracefully, not crash.
    result = alignment.align_audio_to_script(_fake_script(), audio_path=None)

    assert len(result.segments) == 2
    assert result.segments[0].start == 0.0
    assert result.segments[0].end == 4.0
    assert result.segments[1].start == 4.0
    assert result.total_duration == 8.0
    # words within a segment carry increasing start times
    words = result.segments[0].words
    assert words[0].word == "Water"
    assert words[0].start < words[-1].start
