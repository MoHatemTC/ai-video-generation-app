from backend.models.scene import Scene, ScenePlan, VisualElement
from backend.models.timeline import Asset, AssetManifest
from backend.services import composition


def test_compose_scenes_places_all_elements_within_canvas():
    scene_plan = ScenePlan(scenes=[
        Scene(scene_id=1, layout="split", elements=[
            VisualElement(element_id="e1", concept="a", asset_type="svg", appear_at_word="a"),
            VisualElement(element_id="e2", concept="b", asset_type="svg", appear_at_word="b"),
        ])
    ])
    manifest = AssetManifest(assets=[
        Asset(element_id="e1", asset_type="svg", source="generated", file_path="/tmp/e1.png"),
        Asset(element_id="e2", asset_type="svg", source="generated", file_path="/tmp/e2.png"),
    ])

    composed = composition.compose_scenes(scene_plan, manifest)

    assert composed["canvas_w"] == 1280 and composed["canvas_h"] == 720
    scene = composed["scenes"][0]
    assert len(scene["elements"]) == 2
    for el in scene["elements"]:
        assert 0 <= el["x"] <= composed["canvas_w"] - el["w"]
        assert 0 <= el["y"] <= composed["canvas_h"] - el["h"]
