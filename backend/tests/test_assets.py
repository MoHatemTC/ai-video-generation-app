import os

from backend.models.scene import Scene, ScenePlan, VisualElement
from backend.services import assets


def test_resolve_assets_falls_back_to_procedural_svg_without_api_key(tmp_path):
    scene_plan = ScenePlan(scenes=[
        Scene(scene_id=1, layout="image_focus", elements=[
            VisualElement(element_id="e1", concept="photosynthesis", asset_type="image",
                          appear_at_word="photosynthesis"),
            VisualElement(element_id="e2", concept="sunlight", asset_type="icon", appear_at_word="sunlight"),
        ])
    ])

    manifest = assets.resolve_assets(scene_plan, str(tmp_path))

    assert len(manifest.assets) == 2
    for asset in manifest.assets:
        assert os.path.exists(asset.file_path)
        assert asset.file_path.endswith(".png")
        assert asset.license == "generated-procedural"  # no API key in test env -> fallback path
