"""
Animation & Sync Engine: attach an absolute appear_time (seconds) to each
composed element, driven by the transcript's word-level timestamps.
"""

from backend.models.timeline import TimestampMap


def _find_word_start(segment_words, appear_at_word: str, fallback: float) -> float:
    if not appear_at_word:
        return fallback

    needle = appear_at_word.strip().lower().split()[0]

    for word in segment_words:
        if needle and needle in word.word.lower():
            return word.start

    return fallback


def sync_animation(composed: dict, timestamp_map: TimestampMap) -> dict:
    timestamps_by_scene = {
        segment.segment_id: segment
        for segment in timestamp_map.segments
    }

    for scene in composed["scenes"]:
        seg_ts = timestamps_by_scene.get(scene["scene_id"])

        scene_start = seg_ts.start if seg_ts else 0.0
        scene_end = seg_ts.end if seg_ts else scene_start + 3.0

        scene["start"] = scene_start
        scene["end"] = scene_end

        for element in scene["elements"]:
            words = seg_ts.words if seg_ts else []

            element["appear_time"] = round(
                _find_word_start(
                    words,
                    element.get("appear_at_word", ""),
                    fallback=scene_start,
                ),
                2,
            )

    composed["total_duration"] = timestamp_map.total_duration

    return composed


def create_animation_map(
    composition_data: dict,
    timestamp_map: TimestampMap,
) -> dict:
    """
    Wrapper used by the backend orchestrator.
    """

    animation_metadata = sync_animation(
        composition_data,
        timestamp_map,
    )

    return {
        "status": "animation_map_ready",
        "animation_metadata": animation_metadata,
        "composed_layout": animation_metadata,
    }