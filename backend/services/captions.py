"""
Generate SRT captions from the segment-level timestamps (PRD 7.9 / 9 -
Accessibility: "generate captions/subtitles from the timestamped transcript").
"""
import os

from backend.models.script import VideoScriptBlueprint
from backend.models.timeline import TimestampMap


def _srt_time(seconds: float) -> str:
    ms = int(round(seconds * 1000))
    h, ms = divmod(ms, 3600_000)
    m, ms = divmod(ms, 60_000)
    s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def generate_srt(script: VideoScriptBlueprint, timestamp_map: TimestampMap, output_path: str) -> str:
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    text_by_id = {seg.segment_id: seg.text for seg in script.segments}
    lines = []
    for i, seg_ts in enumerate(timestamp_map.segments, start=1):
        text = text_by_id.get(seg_ts.segment_id, "")
        lines.append(str(i))
        lines.append(f"{_srt_time(seg_ts.start)} --> {_srt_time(seg_ts.end)}")
        lines.append(text)
        lines.append("")
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    return output_path
