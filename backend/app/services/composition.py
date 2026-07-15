from __future__ import annotations

import base64
import mimetypes
import textwrap
from html import escape
from pathlib import Path

from backend.app.schemas.composed_scene import (
    Canvas,
    ComposedElement,
    ComposedScene,
    ElementRole,
    ElementType,
    LayoutName,
    PlannedElement,
    Position,
    ScenePlan,
    Size,
)


class CompositionService:
    """Convert a high-level ScenePlan into a static ComposedScene."""

    CANVAS_WIDTH = 1920
    CANVAS_HEIGHT = 1080
    BACKGROUND_COLOR = "#FFFFFF"

    MARGIN_X = 120
    TOP_MARGIN = 70
    BOTTOM_MARGIN = 90
    TITLE_HEIGHT = 140
    CONTENT_TOP = 250
    COLUMN_GAP = 100

    def compose_scene(
        self,
        scene_plan: ScenePlan | dict,
    ) -> ComposedScene:
        """Validate the plan, apply its layout rule, and return a scene."""

        validated_plan = ScenePlan.model_validate(scene_plan)

        canvas = Canvas(
            width=self.CANVAS_WIDTH,
            height=self.CANVAS_HEIGHT,
            background_color=self.BACKGROUND_COLOR,
        )

        layout_handlers = {
            LayoutName.TITLE_SLIDE: self._compose_title_slide,
            LayoutName.IMAGE_LEFT_TEXT_RIGHT:
                self._compose_image_left_text_right,
            LayoutName.TEXT_LEFT_IMAGE_RIGHT:
                self._compose_text_left_image_right,
        }

        handler = layout_handlers[validated_plan.layout]
        composed_elements = handler(validated_plan, canvas)

        scene_start, scene_end = self._timing_for_segments(
            scene_plan=validated_plan,
            segment_ids=validated_plan.script_segment_ids,
        )

        return ComposedScene(
            scene_id=validated_plan.scene_id,
            layout=validated_plan.layout,
            canvas=canvas,
            script_segment_ids=validated_plan.script_segment_ids,
            elements=composed_elements,
            start_time_seconds=scene_start,
            end_time_seconds=scene_end,
        )

    def _compose_title_slide(
        self,
        scene_plan: ScenePlan,
        canvas: Canvas,
    ) -> list[ComposedElement]:
        """Compose a title slide with an optional centered visual."""

        title = self._require_single_role(
            scene_plan,
            ElementRole.TITLE,
        )

        main_visual = self._optional_single_role(
            scene_plan,
            ElementRole.MAIN_VISUAL,
        )

        elements = [
            self._build_element(
                planned=title,
                position=Position(x=220, y=110),
                size=Size(width=1480, height=190),
                layer=2,
                scene_plan=scene_plan,
            )
        ]

        if main_visual is not None:
            visual_width = 1000
            visual_height = 560

            elements.append(
                self._build_element(
                    planned=main_visual,
                    position=Position(
                        x=(canvas.width - visual_width) / 2,
                        y=370,
                    ),
                    size=Size(
                        width=visual_width,
                        height=visual_height,
                    ),
                    layer=1,
                    scene_plan=scene_plan,
                )
            )

        return elements

    def _compose_image_left_text_right(
        self,
        scene_plan: ScenePlan,
        canvas: Canvas,
    ) -> list[ComposedElement]:
        """Compose a title, visual on the left, and text on the right."""

        return self._compose_two_column_layout(
            scene_plan=scene_plan,
            canvas=canvas,
            visual_on_left=True,
        )

    def _compose_text_left_image_right(
        self,
        scene_plan: ScenePlan,
        canvas: Canvas,
    ) -> list[ComposedElement]:
        """Compose a title, text on the left, and visual on the right."""

        return self._compose_two_column_layout(
            scene_plan=scene_plan,
            canvas=canvas,
            visual_on_left=False,
        )

    def _compose_two_column_layout(
        self,
        *,
        scene_plan: ScenePlan,
        canvas: Canvas,
        visual_on_left: bool,
    ) -> list[ComposedElement]:
        """Calculate a reusable two-column layout."""

        title = self._require_single_role(
            scene_plan,
            ElementRole.TITLE,
        )
        body = self._require_single_role(
            scene_plan,
            ElementRole.BODY,
        )
        main_visual = self._require_single_role(
            scene_plan,
            ElementRole.MAIN_VISUAL,
        )

        content_width = (
            canvas.width
            - (2 * self.MARGIN_X)
            - self.COLUMN_GAP
        )
        column_width = content_width / 2

        content_height = (
            canvas.height
            - self.CONTENT_TOP
            - self.BOTTOM_MARGIN
        )

        left_x = self.MARGIN_X
        right_x = (
            self.MARGIN_X
            + column_width
            + self.COLUMN_GAP
        )

        visual_x = left_x if visual_on_left else right_x
        body_x = right_x if visual_on_left else left_x

        return [
            self._build_element(
                planned=title,
                position=Position(
                    x=self.MARGIN_X,
                    y=self.TOP_MARGIN,
                ),
                size=Size(
                    width=canvas.width - (2 * self.MARGIN_X),
                    height=self.TITLE_HEIGHT,
                ),
                layer=3,
                scene_plan=scene_plan,
            ),
            self._build_element(
                planned=main_visual,
                position=Position(
                    x=visual_x,
                    y=self.CONTENT_TOP,
                ),
                size=Size(
                    width=column_width,
                    height=content_height,
                ),
                layer=1,
                scene_plan=scene_plan,
            ),
            self._build_element(
                planned=body,
                position=Position(
                    x=body_x,
                    y=self.CONTENT_TOP,
                ),
                size=Size(
                    width=column_width,
                    height=content_height,
                ),
                layer=2,
                scene_plan=scene_plan,
            ),
        ]

    def _build_element(
        self,
        *,
        planned: PlannedElement,
        position: Position,
        size: Size,
        layer: int,
        scene_plan: ScenePlan,
    ) -> ComposedElement:
        """Combine planner data with calculated geometry."""

        start_time, end_time = self._timing_for_segments(
            scene_plan=scene_plan,
            segment_ids=scene_plan.script_segment_ids,
        )

        return ComposedElement(
            element_id=planned.element_id,
            element_type=planned.element_type,
            role=planned.role,
            position=position,
            size=size,
            layer=layer,
            text=planned.text,
            asset_url=planned.asset_url,
            alt_text=planned.alt_text,
            script_segment_ids=scene_plan.script_segment_ids,
            start_time_seconds=start_time,
            end_time_seconds=end_time,
        )

    def _require_single_role(
        self,
        scene_plan: ScenePlan,
        role: ElementRole,
    ) -> PlannedElement:
        """Return exactly one element with the requested role."""

        matching = [
            element
            for element in scene_plan.elements
            if element.role == role
        ]

        if len(matching) != 1:
            raise ValueError(
                f"Layout '{scene_plan.layout.value}' requires exactly "
                f"one '{role.value}' element; found {len(matching)}."
            )

        return matching[0]

    def _optional_single_role(
        self,
        scene_plan: ScenePlan,
        role: ElementRole,
    ) -> PlannedElement | None:
        """Return zero or one element with the requested role."""

        matching = [
            element
            for element in scene_plan.elements
            if element.role == role
        ]

        if len(matching) > 1:
            raise ValueError(
                f"Layout '{scene_plan.layout.value}' allows at most one "
                f"'{role.value}' element; found {len(matching)}."
            )

        return matching[0] if matching else None

    def _timing_for_segments(
        self,
        *,
        scene_plan: ScenePlan,
        segment_ids: list[str],
    ) -> tuple[float | None, float | None]:
        """Carry optional timing already mapped to script segments."""

        matching = [
            timing
            for timing in scene_plan.timing
            if timing.script_segment_id in segment_ids
        ]

        starts = [
            timing.start_time_seconds
            for timing in matching
            if timing.start_time_seconds is not None
        ]

        ends = [
            timing.end_time_seconds
            for timing in matching
            if timing.end_time_seconds is not None
        ]

        return (
            min(starts) if starts else None,
            max(ends) if ends else None,
        )

    def render_svg(self, scene: ComposedScene) -> str:
        """Create visible SVG evidence with text wrapping and real images."""

        parts = [
            (
                f'<svg xmlns="http://www.w3.org/2000/svg" '
                f'xmlns:xlink="http://www.w3.org/1999/xlink" '
                f'width="{scene.canvas.width}" '
                f'height="{scene.canvas.height}" '
                f'viewBox="0 0 {scene.canvas.width} {scene.canvas.height}">'
            ),
            (
                f'<rect width="100%" height="100%" '
                f'fill="{escape(scene.canvas.background_color)}"/>'
            ),
        ]

        for element in sorted(
            scene.elements,
            key=lambda item: item.layer,
        ):
            x = element.position.x
            y = element.position.y
            width = element.size.width
            height = element.size.height

            # Draw the element container.
            parts.append(
                (
                    f'<rect x="{x}" y="{y}" '
                    f'width="{width}" height="{height}" '
                    f'fill="#F4F6F8" stroke="#606770" '
                    f'stroke-width="3" rx="18"/>'
                )
            )

            # Render text elements with wrapping and multiline support.
            if element.element_type == ElementType.TEXT:
                label = (element.text or "").replace("\\n", "\n")

                font_size = (
                    58
                    if element.role == ElementRole.TITLE
                    else 32
                )

                text_x = x + 30
                text_y = y + 55
                line_height = font_size + 14
                text_area_bottom = y + height - 25

                max_chars = max(
                    10,
                    int((width - 60) / (font_size * 0.55)),
                )

                parts.append(
                    (
                        f'<text font-family="Arial" '
                        f'font-size="{font_size}" '
                        f'fill="#111827">'
                    )
                )

                current_y = text_y

                for paragraph in label.split("\n"):
                    wrapped_lines = textwrap.wrap(
                        paragraph,
                        width=max_chars,
                        break_long_words=False,
                        break_on_hyphens=False,
                    )

                    if not wrapped_lines:
                        current_y += line_height
                        continue

                    for line in wrapped_lines:
                        if current_y > text_area_bottom:
                            break

                        parts.append(
                            (
                                f'<tspan x="{text_x}" '
                                f'y="{current_y}">'
                                f'{escape(line)}'
                                f'</tspan>'
                            )
                        )

                        current_y += line_height

                parts.append("</text>")

            # Render actual image, diagram, icon, or SVG assets.
            else:
                asset_href = self._resolve_asset_href(
                    element.asset_url or ""
                )

                if asset_href is not None:
                    safe_href = escape(asset_href, quote=True)
                    parts.append(
                        (
                            f'<image '
                            f'href="{safe_href}" '
                            f'xlink:href="{safe_href}" '
                            f'x="{x + 70}" '
                            f'y="{y + 70}" '
                            f'width="{width - 140}" '
                            f'height="{height - 140}" '
                            f'preserveAspectRatio="xMidYMid meet"/>'
                        )
                    )
                else:
                    # Visible fallback when the local asset cannot be found.
                    fallback = escape(
                        element.alt_text
                        or element.asset_url
                        or "Asset could not be loaded"
                    )
                    parts.append(
                        (
                            f'<text x="{x + 30}" y="{y + 60}" '
                            f'font-family="Arial" font-size="28" '
                            f'fill="#B91C1C">{fallback}</text>'
                        )
                    )

        parts.append("</svg>")
        return "\n".join(parts)


    def _resolve_asset_href(self, asset_url: str) -> str | None:
        """Return a browser-safe asset reference for the SVG preview.

        Remote URLs and existing data URIs are preserved. Local files are
        embedded as Base64 data URIs so browsers cannot block or lose them.
        """

        normalized = asset_url.strip()
        if not normalized:
            return None

        if normalized.startswith(("http://", "https://", "data:")):
            return normalized

        if normalized.startswith("file://"):
            try:
                local_path = Path(normalized.removeprefix("file:///"))
            except ValueError:
                return None
        else:
            local_path = Path(normalized)

        if not local_path.is_absolute():
            local_path = (Path.cwd() / local_path).resolve()

        if not local_path.exists() or not local_path.is_file():
            return None

        mime_type, _ = mimetypes.guess_type(local_path.name)
        mime_type = mime_type or "application/octet-stream"
        encoded = base64.b64encode(local_path.read_bytes()).decode("ascii")

        return f"data:{mime_type};base64,{encoded}"

    def save_svg(
        self,
        scene: ComposedScene,
        output_path: str | Path,
    ) -> Path:
        """Save the generated SVG preview to a file."""

        path = Path(output_path)
        path.write_text(
            self.render_svg(scene),
            encoding="utf-8",
        )

        return path