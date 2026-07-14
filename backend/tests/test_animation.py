from backend.models.timeline import SegmentTimestamp, TimestampMap, WordTimestamp
from backend.services import animation


def test_sync_animation_finds_appear_time_for_matching_word():
    composed = {
        "canvas_w": 1280, "canvas_h": 720,
        "scenes": [
            {"scene_id": 1, "layout": "image_focus", "elements": [
                {"element_id": "e1", "appear_at_word": "sunlight", "file_path": "x.png",
                 "x": 0, "y": 0, "w": 100, "h": 100},
            ]}
        ],
    }
    timestamp_map = TimestampMap(
        total_duration=3.0,
        segments=[
            SegmentTimestamp(segment_id=1, start=0.0, end=3.0, words=[
                WordTimestamp(word="Plants", start=0.0, end=0.5),
                WordTimestamp(word="use", start=0.5, end=0.8),
                WordTimestamp(word="sunlight", start=0.8, end=1.4),
                WordTimestamp(word="daily", start=1.4, end=2.0),
            ]),
        ],
    )

    result = animation.sync_animation(composed, timestamp_map)

    element = result["scenes"][0]["elements"][0]
    assert element["appear_time"] == 0.8
    assert result["scenes"][0]["start"] == 0.0
    assert result["scenes"][0]["end"] == 3.0
    assert result["total_duration"] == 3.0


def test_sync_animation_falls_back_to_scene_start_when_word_not_found():
    composed = {
        "canvas_w": 1280, "canvas_h": 720,
        "scenes": [{"scene_id": 1, "layout": "image_focus", "elements": [
            {"element_id": "e1", "appear_at_word": "nonexistent", "file_path": "x.png",
             "x": 0, "y": 0, "w": 100, "h": 100},
        ]}],
    }
    timestamp_map = TimestampMap(total_duration=2.0, segments=[
        SegmentTimestamp(segment_id=1, start=1.5, end=2.0, words=[
            WordTimestamp(word="Hello", start=1.5, end=2.0)
        ]),
    ])

    result = animation.sync_animation(composed, timestamp_map)
    assert result["scenes"][0]["elements"][0]["appear_time"] == 1.5
