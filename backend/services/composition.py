"""
Scene Composition: assemble each scene's assets into a slide layout (PRD 7.7).

Positions elements on a fixed 1280x720 canvas using a small set of reusable
layout rules keyed by element count (PRD 7.7's "small set of reusable slide
templates"). Returns a plain dict tree (not a DB/pydantic model) because this
is purely an intermediate structure consumed by the animation stage next.
"""
from backend.models.scene import ScenePlan
from backend.models.timeline import AssetManifest

CANVAS_W, CANVAS_H = 1280, 720
_ELEMENT_SIZE = 320


def _positions_for(n: int) -> list[tuple[int, int]]:
    """Top-left (x, y) box origins for 1..3 elements on the canvas."""
    cy = (CANVAS_H - _ELEMENT_SIZE) // 2
    if n <= 1:
        return [((CANVAS_W - _ELEMENT_SIZE) // 2, cy)]
    if n == 2:
        gap = 60
        total_w = _ELEMENT_SIZE * 2 + gap
        x0 = (CANVAS_W - total_w) // 2
        return [(x0, cy), (x0 + _ELEMENT_SIZE + gap, cy)]
    # 3+: simple horizontal row, evenly spaced, clipped to canvas width
    gap = 40
    total_w = _ELEMENT_SIZE * 3 + gap * 2
    x0 = max(20, (CANVAS_W - total_w) // 2)
    return [(x0 + i * (_ELEMENT_SIZE + gap), cy) for i in range(3)]


def compose_scenes(scene_plan: ScenePlan, asset_manifest: AssetManifest) -> dict:
    assets_by_id = {a.element_id: a for a in asset_manifest.assets}
    composed_scenes = []

    for scene in scene_plan.scenes:
        positions = _positions_for(len(scene.elements))
        placed = []
        for element, (x, y) in zip(scene.elements, positions):
            asset = assets_by_id.get(element.element_id)
            if not asset:
                continue
            placed.append(
                {
                    "element_id": element.element_id,
                    "appear_at_word": element.appear_at_word,
                    "file_path": asset.file_path,
                    "x": x,
                    "y": y,
                    "w": _ELEMENT_SIZE,
                    "h": _ELEMENT_SIZE,
                }
            )
        composed_scenes.append(
            {
                "scene_id": scene.scene_id,
                "layout": scene.layout,
                "elements": placed,
            }
        )

    return {"canvas_w": CANVAS_W, "canvas_h": CANVAS_H, "scenes": composed_scenes}
