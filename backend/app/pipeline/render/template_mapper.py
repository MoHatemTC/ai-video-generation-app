"""
Rule-based template mapper: assigns a `template` field to each scene
based on its `layout_hint` value.

Mapping rules:
    "title-card"       → "intro"
    "outro-checklist"  → "outro"
    "cards"            → "content_b"
    everything else    → "content_a"

Edge-case defaults:
    • First scene with no layout_hint → "intro"
    • Last  scene with no layout_hint → "outro"
    • Unknown hints                   → "content_a"
"""

import json
from typing import Dict

# Canonical mapping from layout_hint → template name
_HINT_TO_TEMPLATE: Dict[str, str] = {
    "title-card": "intro",
    "outro-checklist": "outro",
    "cards": "content_b",
    # All diagram / generic content hints → content_a
    "risk-diagram": "content_a",
    "tunnel-diagram": "content_a",
    "flow-diagram": "content_a",
}

_DEFAULT_TEMPLATE = "content_a"


def assign_templates(scene_plan: dict) -> dict:
    """
    Mutates *scene_plan* in place, adding a ``template`` field to every
    scene that doesn't already have one.

    Parameters
    ----------
    scene_plan : dict
        A ScenePlan dictionary (must contain a ``scenes`` list).

    Returns
    -------
    dict
        The same *scene_plan* dict (mutated), for chaining convenience.
    """
    scenes = scene_plan.get("scenes", [])
    total = len(scenes)

    for idx, scene in enumerate(scenes):
        # Skip if template was already assigned (e.g. by the scene planner)
        if scene.get("template"):
            continue

        hint = (scene.get("layout_hint") or "").strip().lower()

        if hint in _HINT_TO_TEMPLATE:
            scene["template"] = _HINT_TO_TEMPLATE[hint]
        elif idx == 0:
            # First scene without a recognized hint → default intro
            scene["template"] = "intro"
        elif idx == total - 1:
            # Last scene without a recognized hint → default outro
            scene["template"] = "outro"
        else:
            scene["template"] = _DEFAULT_TEMPLATE

    return scene_plan


# ---------------------------------------------------------------------------
# Quick self-test
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import sys
    from pathlib import Path

    if len(sys.argv) > 1:
        path = Path(sys.argv[1])
    else:
        path = Path(__file__).resolve().parent / "docker_scene_plan.json"

    with open(path, "r", encoding="utf-8") as f:
        plan = json.load(f)

    assign_templates(plan)

    for s in plan["scenes"]:
        print(f"  scene {s['scene_id']:>2}  layout_hint={s.get('layout_hint',''):20s}  → template={s['template']}")
