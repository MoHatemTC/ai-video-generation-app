from backend.app.schemas.composed_scene import CompositionOutput
from backend.app.services.composition import CompositionService


def valid_inputs() -> tuple[dict, dict, dict]:
    scene_plan = {
        "video_id": "video_multimedia_001",
        "scenes": [
            {"scene_id": "scene_1", "layout": "title_slide", "script_segments": ["seg_1"], "visual_elements": [
                {"cue_id": "cue_1", "description": "Opening title", "element_type": "text", "content": "Introduction to Multimedia Learning", "asset_id": None, "linked_segment_id": "seg_1", "appearance_trigger": {"type": "segment_start", "word_id": None}, "preferred_region": "center", "importance": "primary"}
            ]},
            {"scene_id": "scene_2", "layout": "image_left_text_right", "script_segments": ["seg_2"], "visual_elements": [
                {"cue_id": "cue_2", "description": "Words and visuals", "element_type": "image", "content": None, "asset_id": "asset_1", "linked_segment_id": "seg_2", "appearance_trigger": {"type": "word", "word_id": "word_5"}, "preferred_region": "left", "importance": "primary"},
                {"cue_id": "cue_3", "description": "Key points", "element_type": "text", "content": "1. Combine words and visuals\\n2. Reduce unnecessary cognitive load\\n3. Improve understanding", "asset_id": None, "linked_segment_id": "seg_2", "appearance_trigger": {"type": "segment_start", "word_id": None}, "preferred_region": "right", "importance": "secondary"}
            ]},
        ],
    }
    assets = {"video_id": "video_multimedia_001", "assets": [
        {"asset_id": "asset_1", "scene_id": "scene_2", "cue_id": "cue_2", "url": "sample_inputs/multimedia_learning.svg", "type": "image", "license": "project-generated", "source": "generated"}
    ]}
    alignment = {"video_id": "video_multimedia_001", "segment_timestamps": [
        {"segment_id": "seg_1", "start": 0.0, "end": 4.0}, {"segment_id": "seg_2", "start": 4.0, "end": 12.0}
    ], "word_timestamps": [
        {"word_id": "word_5", "segment_id": "seg_2", "word": "multimedia", "start": 4.8, "end": 5.3}
    ]}
    return scene_plan, assets, alignment


def test_composes_the_expected_renderer_contract() -> None:
    scene_plan, assets, alignment = valid_inputs()
    output = CompositionService().compose_video(scene_data=scene_plan, asset_data=assets, timestamp_data=alignment)
    assert isinstance(output, CompositionOutput)
    scenes = output.composed_layout.scenes
    assert output.video_id == "video_multimedia_001"
    assert [(scene.start, scene.end) for scene in scenes] == [(0.0, 4.0), (4.0, 12.0)]
    assert scenes[0].elements[0].model_dump(mode="json") == {
        "cue_id": "cue_1", "element_type": "text", "content": "Introduction to Multimedia Learning", "asset_id": None, "asset_url": None,
        "position": {"x": 220.0, "y": 120.0}, "size": {"width": 1480.0, "height": 180.0}, "layer": 2,
        "linked_segment_id": "seg_1", "start": 0.0, "end": 4.0,
    }
    image, text = scenes[1].elements
    assert image.start == 4.8
    assert image.asset_url == "sample_inputs/multimedia_learning.svg"
    assert image.position.x < text.position.x


def test_rejects_missing_or_wrong_assets() -> None:
    scene_plan, assets, alignment = valid_inputs()
    assets["assets"] = []
    try:
        CompositionService().compose_video(scene_data=scene_plan, asset_data=assets, timestamp_data=alignment)
    except ValueError as error:
        assert "Missing asset" in str(error)
    else:
        raise AssertionError("Expected missing assets to be rejected")


def test_rejects_an_invalid_word_trigger() -> None:
    scene_plan, assets, alignment = valid_inputs()
    scene_plan["scenes"][1]["visual_elements"][0]["appearance_trigger"]["word_id"] = "unknown_word"
    try:
        CompositionService().compose_video(scene_data=scene_plan, asset_data=assets, timestamp_data=alignment)
    except ValueError as error:
        assert "unknown_word" in str(error)
    else:
        raise AssertionError("Expected unknown word timing to be rejected")
