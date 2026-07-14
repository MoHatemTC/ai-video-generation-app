"""
Animation & Sync Engine: attach an absolute appear_time (seconds) to each
composed element, driven by the transcript's word-level timestamps
(PRD 7.8) -- this is the product's defining feature: elements appear on
screen exactly when the instructor's voice mentions them.
"""
from backend.models.timeline import TimestampMap


def _find_word_start(segment_words, appear_at_word: str, fallback: float) -> float:
    if not appear_at_word:
        return fallback
    needle = appear_at_word.strip().lower().split()[0] if appear_at_word.strip() else ""
    for w in segment_words:
        if needle and needle in w.word.lower():
            return w.start
    return fallback


def sync_animation(composed: dict, timestamp_map: TimestampMap) -> dict:
    timestamps_by_scene = {s.segment_id: s for s in timestamp_map.segments}

    for scene in composed["scenes"]:
        seg_ts = timestamps_by_scene.get(scene["scene_id"])
        scene_start = seg_ts.start if seg_ts else 0.0
        scene_end = seg_ts.end if seg_ts else scene_start + 3.0
        scene["start"] = scene_start
        scene["end"] = scene_end

        for element in scene["elements"]:
            words = seg_ts.words if seg_ts else []
            element["appear_time"] = round(
                _find_word_start(words, element.get("appear_at_word", ""), fallback=scene_start), 2
            )

    composed["total_duration"] = timestamp_map.total_duration
    return composed
