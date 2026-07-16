import os

from backend.models.script import ScriptSegment, VideoScriptBlueprint
from backend.models.timeline import SegmentTimestamp, TimestampMap
from backend.services import captions


def test_generate_srt_writes_valid_format(tmp_path):
    script = VideoScriptBlueprint(
        title="T", target_audience="general", estimated_total_duration=4,
        segments=[ScriptSegment(segment_id=1, text="Hello world", visual_cues="", duration_seconds=4)],
    )
    ts_map = TimestampMap(total_duration=4.0, segments=[
        SegmentTimestamp(segment_id=1, start=0.0, end=4.0, words=[])
    ])

    out_path = str(tmp_path / "captions.srt")
    result_path = captions.generate_srt(script, ts_map, out_path)

    assert os.path.exists(result_path)
    content = open(result_path, encoding="utf-8").read()
    assert "1\n00:00:00,000 --> 00:00:04,000\nHello world" in content
