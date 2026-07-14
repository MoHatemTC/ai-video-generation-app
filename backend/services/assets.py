"""
Asset Collection & Generation: scene cue -> visual asset (PRD 7.6).

Every asset returned here is either AI-generated or procedurally generated --
never scraped from an unlicensed source -- so the `license` field on `Asset`
is always safe to record per the Responsible AI requirements (PRD 9).

Real DALL-E image generation is used for asset_type == "image" when an AI
provider is configured. All other asset types (diagram / icon / gif / svg /
clip), plus any image-generation failure, fall back to a procedural SVG
built from the element's concept text -- a lightweight, dependency-free
placeholder that keeps the pipeline runnable without extra paid providers.
Mermaid-rendered diagrams and real short video clips are flagged as a
follow-up integration (see docs/architecture.md ADR note) rather than faked.
"""
import hashlib
import logging
import os

import cairosvg

from backend.models.scene import ScenePlan
from backend.models.timeline import Asset, AssetManifest
from backend.services.ai_client import AIConfigError, get_openai_client

logger = logging.getLogger(__name__)

_PALETTE = ["#2563EB", "#059669", "#DC2626", "#7C3AED", "#EA580C", "#0891B2"]


def _color_for(text: str) -> str:
    idx = int(hashlib.sha1(text.encode()).hexdigest(), 16) % len(_PALETTE)
    return _PALETTE[idx]


def _procedural_svg_asset(concept: str, element_id: str, output_dir: str) -> str:
    """Build a simple, on-brand SVG card for a concept. Deterministic, no network needed."""
    color = _color_for(concept)
    label = concept if len(concept) <= 28 else concept[:25] + "..."
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="640" height="480" viewBox="0 0 640 480">
  <rect width="640" height="480" rx="24" fill="{color}" opacity="0.12"/>
  <circle cx="320" cy="190" r="90" fill="{color}"/>
  <text x="320" y="330" font-family="Arial, sans-serif" font-size="28" font-weight="600"
        fill="#111827" text-anchor="middle">{label}</text>
</svg>'''
    svg_path = os.path.join(output_dir, f"{element_id}.svg")
    png_path = os.path.join(output_dir, f"{element_id}.png")
    with open(svg_path, "w", encoding="utf-8") as f:
        f.write(svg)
    cairosvg.svg2png(url=svg_path, write_to=png_path, output_width=1280, output_height=960)
    return png_path


def _dalle_image_asset(concept: str, element_id: str, output_dir: str) -> str | None:
    try:
        client = get_openai_client()
    except AIConfigError:
        return None
    try:
        result = client.images.generate(
            model="dall-e-3",
            prompt=(
                f"Clean, flat, modern educational illustration of: {concept}. "
                "Minimal background, no text, MOOC-style slide graphic."
            ),
            size="1024x1024",
            n=1,
        )
        import base64
        image_b64 = result.data[0].b64_json
        png_path = os.path.join(output_dir, f"{element_id}.png")
        with open(png_path, "wb") as f:
            f.write(base64.b64decode(image_b64))
        return png_path
    except Exception as exc:  # provider/network/billing failure -- degrade, don't crash the job
        logger.warning("DALL-E generation failed for '%s' (%s); using procedural SVG fallback.", concept, exc)
        return None


def resolve_assets(scene_plan: ScenePlan, output_dir: str) -> AssetManifest:
    os.makedirs(output_dir, exist_ok=True)
    assets: list[Asset] = []

    for scene in scene_plan.scenes:
        for element in scene.elements:
            file_path = None
            license_tag = "generated-procedural"

            if element.asset_type == "image":
                file_path = _dalle_image_asset(element.concept, element.element_id, output_dir)
                if file_path:
                    license_tag = "generated-dalle3"

            if not file_path:
                file_path = _procedural_svg_asset(element.concept, element.element_id, output_dir)

            assets.append(
                Asset(
                    element_id=element.element_id,
                    asset_type=element.asset_type,
                    source="generated",
                    license=license_tag,
                    file_path=file_path,
                )
            )

    return AssetManifest(assets=assets)
