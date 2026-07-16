"""Create static SVG review files from a composition-stage JSON payload.

This optional utility deliberately does not animate scenes or alter the
composition contract.  It helps reviewers inspect element placement, layering,
and resolved asset references before the animation/render stage begins.
"""

from __future__ import annotations

import argparse
import json
import textwrap
from html import escape
from pathlib import Path
from urllib.parse import urlparse

from backend.app.schemas.composed_scene import (
    ComposedElement,
    ComposedScene,
    CompositionOutput,
    ElementType,
)


class SvgPreviewRenderer:
    """Render one static SVG review file for every composed scene."""

    def render_video(
        self,
        composition: CompositionOutput | dict,
        output_directory: str | Path,
    ) -> list[Path]:
        """Validate *composition* and save ``<scene_id>.svg`` preview files."""
        output = CompositionOutput.model_validate(composition)
        directory = Path(output_directory)
        directory.mkdir(parents=True, exist_ok=True)

        paths: list[Path] = []
        for scene in output.composed_layout.scenes:
            path = directory / f"{scene.scene_id}.svg"
            path.write_text(self.render_scene(scene), encoding="utf-8")
            paths.append(path)
        return paths

    def render_scene(self, scene: ComposedScene) -> str:
        """Return a static SVG representation of a single composed scene."""
        canvas = scene.canvas
        parts = [
            '<?xml version="1.0" encoding="UTF-8"?>',
            (
                f'<svg xmlns="http://www.w3.org/2000/svg" '
                f'xmlns:xlink="http://www.w3.org/1999/xlink" '
                f'width="{canvas.width}" height="{canvas.height}" '
                f'viewBox="0 0 {canvas.width} {canvas.height}">'
            ),
            f'<rect width="100%" height="100%" fill="{escape(canvas.background_color)}"/>',
        ]
        for element in sorted(scene.elements, key=lambda item: item.layer):
            parts.extend(self._render_element(element))
        parts.append("</svg>")
        return "\n".join(parts)

    def _render_element(self, element: ComposedElement) -> list[str]:
        x, y = element.position.x, element.position.y
        width, height = element.size.width, element.size.height
        parts = [
            '<g>',
            (
                f'<rect x="{x}" y="{y}" width="{width}" height="{height}" '
                'fill="#F4F6F8" stroke="#606770" stroke-width="3" rx="18"/>'
            ),
        ]
        if element.element_type == ElementType.TEXT:
            parts.extend(self._render_text(element))
        else:
            parts.extend(self._render_asset(element))
        parts.append("</g>")
        return parts

    @staticmethod
    def _render_text(element: ComposedElement) -> list[str]:
        x, y = element.position.x, element.position.y
        width, height = element.size.width, element.size.height
        font_size = 54 if height <= 200 else 34
        line_height = font_size + 14
        max_characters = max(10, int((width - 60) / (font_size * 0.55)))
        max_y = y + height - 25
        current_y = y + 60
        parts = [f'<text font-family="Arial, sans-serif" font-size="{font_size}" fill="#111827">']

        for paragraph in (element.content or "").split("\n"):
            for line in textwrap.wrap(
                paragraph, width=max_characters, break_long_words=False,
                break_on_hyphens=False,
            ) or [""]:
                if current_y > max_y:
                    break
                parts.append(f'<tspan x="{x + 30}" y="{current_y}">{escape(line)}</tspan>')
                current_y += line_height
        parts.append("</text>")
        return parts

    @staticmethod
    def _render_asset(element: ComposedElement) -> list[str]:
        x, y = element.position.x, element.position.y
        width, height = element.size.width, element.size.height
        href = escape(element.asset_url or "", quote=True)
        if urlparse(element.asset_url or "").scheme in {"http", "https", "data"}:
            return [
                (
                    f'<image href="{href}" xlink:href="{href}" x="{x + 35}" y="{y + 35}" '
                    f'width="{width - 70}" height="{height - 70}" '
                    'preserveAspectRatio="xMidYMid meet"/>'
                )
            ]
        # Local paths are intentionally shown as labels: a browser resolves paths
        # relative to the SVG file, which is unreliable after files are moved.
        label = escape(element.asset_url or "Asset unavailable")
        return [
            f'<text x="{x + 35}" y="{y + 70}" font-family="Arial, sans-serif" font-size="28" fill="#374151">{label}</text>',
            f'<text x="{x + 35}" y="{y + 115}" font-family="Arial, sans-serif" font-size="22" fill="#6B7280">{escape(element.element_type.value)}</text>',
        ]


def main() -> None:
    """Run the preview renderer from the command line."""
    parser = argparse.ArgumentParser(description="Create static SVG previews from composition JSON.")
    parser.add_argument("composition_json", type=Path, help="JSON created by CompositionService.")
    parser.add_argument("--output-dir", type=Path, default=Path("svg_previews"))
    args = parser.parse_args()

    try:
        payload = json.loads(args.composition_json.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise ValueError(f"{args.composition_json} is not valid JSON.") from error

    paths = SvgPreviewRenderer().render_video(payload, args.output_dir)
    for path in paths:
        print(f"SVG preview: {path.resolve()}")


if __name__ == "__main__":
    main()
