"""Run the Composition service and generate static SVG review previews.

Run from the repository root, where the ``backend`` directory is present:

    python run_composition.py samples/input-scene_plan.json \
        samples/input-assets.json samples/input-alignment.json
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from backend.app.services.composition import CompositionService
from backend.app.services.svg_preview_renderer import SvgPreviewRenderer


def load_json(path: Path) -> dict[str, Any]:
    """Read a JSON object from *path* and raise a clear error if it is invalid."""
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as error:
        raise ValueError(f"Input file was not found: {path}") from error
    except json.JSONDecodeError as error:
        raise ValueError(f"Input file is not valid JSON: {path}") from error
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a top-level JSON object.")
    return payload


def main() -> None:
    """Compose the three stage inputs and save JSON plus SVG review files."""
    parser = argparse.ArgumentParser(
        description="Compose scene, asset, and alignment JSON into output JSON and SVG previews."
    )
    parser.add_argument("scene_json", type=Path, help="Scene Planner JSON input.")
    parser.add_argument("asset_json", type=Path, help="Asset Service JSON input.")
    parser.add_argument("alignment_json", type=Path, help="Alignment JSON input.")
    parser.add_argument(
        "--output", type=Path, default=Path("composition_output.json"),
        help="Path for the renderer-ready JSON output.",
    )
    parser.add_argument(
        "--svg-dir", type=Path, default=Path("svg_previews"),
        help="Directory in which one static SVG preview is written per scene.",
    )
    args = parser.parse_args()

    output = CompositionService().compose_video(
        scene_data=load_json(args.scene_json),
        asset_data=load_json(args.asset_json),
        timestamp_data=load_json(args.alignment_json),
    )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(output.model_dump(mode="json"), indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"Composition JSON: {args.output.resolve()}")

    for path in SvgPreviewRenderer().render_video(output, args.svg_dir):
        print(f"SVG preview: {path.resolve()}")


if __name__ == "__main__":
    main()
