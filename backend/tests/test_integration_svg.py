"""
Sprint 4 — SVG Writer Agent: Integration Test
=============================================
This is a LIVE end-to-end test that calls the real LLM API.

It simulates realistic scene-planner output (the format produced by Mostafa Bahy's
ScenePlanner), feeds it through process_scene_elements(), and validates that each
returned SVG asset satisfies the guardrail contract.

Prerequisites:
  - GEMINI_API_KEY or (LITELLM_API_KEY + LITELLM_API_BASE) set in your .env

Run with:
  python -m pytest backend/tests/test_integration_svg.py -v -s --tb=short

Or run directly (no pytest needed):
  python backend/tests/test_integration_svg.py
"""

import asyncio
import json
import os
import re
import sys

# Make sure the project root is on the path when run directly
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

import pytest
from backend.app.services.assets.images import process_scene_elements
from backend.app.schemas.asset import AssetItem

# ---------------------------------------------------------------------------
# Realistic mock of Mostafa Bahy's scene-planner output
# (mirrors the dict shape that process_scene_elements consumes)
# ---------------------------------------------------------------------------

SAMPLE_SCENE_PAYLOAD = {
    "video_id": "integration_test_video_001",
    "scenes": [
        {
            "scene_id": "scene_01",
            "text": "Let's talk about how encryption keeps your data safe.",
            "visual_cues": [
                {
                    "cue_id": "cue_01a",
                    "asset_id": "asset_01a",
                    "description": "A flat vector illustration of a padlock with a keyhole",
                    "element_type": "svg",
                    "linked_segment_id": "seg_01",
                    "appearance_trigger": {"type": "segment_start"},
                    "preferred_region": "center",
                    "importance": "primary",
                },
                {
                    "cue_id": "cue_01b",
                    "asset_id": "asset_01b",
                    "description": "A binary stream of zeros and ones flowing through a shield icon",
                    "element_type": "svg",
                    "linked_segment_id": "seg_01",
                    "appearance_trigger": {"type": "segment_end"},
                    "preferred_region": "right",
                    "importance": "secondary",
                },
            ],
        },
        {
            "scene_id": "scene_02",
            "text": "Think of it like a restaurant kitchen — only the chef knows the recipe.",
            "visual_cues": [
                {
                    "cue_id": "cue_02a",
                    "asset_id": "asset_02a",
                    "description": "A friendly cartoon chef standing in a kitchen holding a recipe card",
                    "element_type": "svg",
                    "linked_segment_id": "seg_02",
                    "appearance_trigger": {"type": "segment_start"},
                    "preferred_region": "center",
                    "importance": "primary",
                }
            ],
        },
        {
            "scene_id": "scene_03",
            "text": "Robots are changing how we build software.",
            "visual_cues": [
                {
                    "cue_id": "cue_03a",
                    "asset_id": "asset_03a",
                    "description": "A friendly robot waving hello",
                    "element_type": "svg",
                    "linked_segment_id": "seg_03",
                    "appearance_trigger": {"type": "segment_start"},
                    "preferred_region": "center",
                    "importance": "primary",
                }
            ],
        },
    ],
}

# ---------------------------------------------------------------------------
# SVG Guardrail Validators
# ---------------------------------------------------------------------------

FORBIDDEN_PATTERNS = [
    (r"<script", "Contains <script> tag (JavaScript forbidden)"),
    (r"\bon\w+=", "Contains inline event handler (on*= attribute)"),
    (r"<image\b", "Contains <image> tag (raster images forbidden)"),
    (r"<foreignObject\b", "Contains <foreignObject> tag (forbidden)"),
    (r"<animate\b", "Contains SMIL <animate> (use CSS animations only)"),
    (r"<animateTransform\b", "Contains SMIL <animateTransform> (use CSS animations only)"),
    (r"<animateMotion\b", "Contains SMIL <animateMotion> (use CSS animations only)"),
    (r"data:image/", "Contains base64-encoded raster image (forbidden)"),
]

REQUIRED_PATTERNS = [
    (r"<svg\b[^>]+width\s*=\s*[\"']1280[\"']", "Missing required width='1280'"),
    (r"<svg\b[^>]+height\s*=\s*[\"']720[\"']", "Missing required height='720'"),
    (r"@keyframes\s+\w+", "Missing CSS @keyframes animation (animations are mandatory)"),
]


def validate_svg_guardrails(svg_code: str, asset_id: str) -> list[str]:
    """
    Returns a list of violation messages. Empty list = fully compliant.
    """
    violations = []
    for pattern, message in FORBIDDEN_PATTERNS:
        if re.search(pattern, svg_code, re.IGNORECASE):
            violations.append(f"[{asset_id}] FORBIDDEN: {message}")
    for pattern, message in REQUIRED_PATTERNS:
        if not re.search(pattern, svg_code, re.IGNORECASE):
            violations.append(f"[{asset_id}] MISSING: {message}")
    return violations


# ---------------------------------------------------------------------------
# Integration Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.integration
async def test_full_pipeline_produces_svg_assets():
    """
    Full pipeline integration: realistic ScenePlanner output →
    process_scene_elements() → valid, guardrail-compliant SVG assets.

    Requires a live LLM API key (GEMINI_API_KEY or LITELLM_API_KEY).
    """
    result = await process_scene_elements(SAMPLE_SCENE_PAYLOAD, supabase_client=None)

    # --- Top-level contract checks ---
    assert "video_id" in result, "Result must contain 'video_id'"
    assert result["video_id"] == "integration_test_video_001"
    assert "assets" in result, "Result must contain 'assets'"

    assets = result["assets"]
    # We submitted 4 SVG-type visual cues across 3 scenes
    assert len(assets) == 4, (
        f"Expected 4 resolved assets, got {len(assets)}. "
        "Check that all svg-type visual_cues are processed."
    )

    print(f"\n✅ Resolved {len(assets)} assets from {len(SAMPLE_SCENE_PAYLOAD['scenes'])} scenes.")

    # --- Per-asset checks ---
    all_violations = []

    # Reload from local storage to inspect the full SVG code
    storage_path = "data/supabase_asset_metadata.json"
    stored_assets: list[dict] = []
    if os.path.exists(storage_path):
        with open(storage_path, "r", encoding="utf-8") as f:
            stored_assets = json.load(f)
        # Filter only assets from this test run
        stored_assets = [
            a for a in stored_assets
            if a.get("video_id") == "integration_test_video_001"
        ]

    for entry in stored_assets:
        asset_id = entry.get("asset_id", "unknown")
        svg_code = entry.get("prompt", "")

        print(f"\n--- {asset_id} ---")
        print(f"  Cue: {entry.get('element', '')[:60]}")
        print(f"  SVG size: {len(svg_code)} characters")

        # Basic structure
        assert svg_code.strip().startswith("<svg"), (
            f"[{asset_id}] SVG must start with <svg, got: {svg_code[:40]!r}"
        )
        assert svg_code.strip().endswith("</svg>"), (
            f"[{asset_id}] SVG must end with </svg>"
        )

        # Guardrail compliance
        violations = validate_svg_guardrails(svg_code, asset_id)
        if violations:
            for v in violations:
                print(f"  ⚠️  GUARDRAIL VIOLATION: {v}")
            all_violations.extend(violations)
        else:
            print(f"  ✅ All guardrails pass")

    # Fail if any guardrail was violated
    if all_violations:
        violation_report = "\n".join(all_violations)
        pytest.fail(
            f"\nGuardrail violations detected across {len(all_violations)} checks:\n"
            f"{violation_report}\n\n"
            "Review the svg_prompt_template.md and strengthen the relevant guardrail."
        )

    print(f"\n🎉 Integration test passed. All {len(stored_assets)} SVGs are guardrail-compliant.")


# ---------------------------------------------------------------------------
# Direct run (no pytest)
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("=" * 60)
    print("SVG Writer Agent — Live Integration Test")
    print("=" * 60)
    asyncio.run(test_full_pipeline_produces_svg_assets())
