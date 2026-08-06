"""
Sprint 4 — SVG Writer Agent Unit Tests
=======================================
Tests are fully mocked (no live API calls required) to ensure deterministic,
offline-runnable coverage of both the happy path and the failure/fallback path.

Run with:
    python -m pytest backend/tests/test_svg_generation.py -v
"""

import pytest
from unittest.mock import patch, MagicMock

from backend.app.services.assets.images import AssetService
from backend.app.schemas.asset import AssetItem


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

VALID_SVG = (
    '<svg width="1280" height="720" viewBox="0 0 1280 720" '
    'xmlns="http://www.w3.org/2000/svg">'
    "<defs><style>.robot{animation:wave 1s infinite;}"
    "@keyframes wave{0%{transform:rotate(0deg);}100%{transform:rotate(15deg);}}"
    "</style></defs>"
    '<rect width="1280" height="720" fill="#1a1a2e"/>'
    '<circle cx="640" cy="360" r="80" fill="#e94560" class="robot"/>'
    "</svg>"
)

FENCED_SVG = f"```svg\n{VALID_SVG}\n```"


# ---------------------------------------------------------------------------
# Happy-path tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@patch("backend.app.services.assets.images.Crew")
@patch("backend.app.services.assets.images.AssetService._get_llm_client")
async def test_svg_writer_produces_valid_asset(mock_get_llm, MockCrew):
    """
    Core contract: given a visual cue, AssetService.resolve_visual_cue()
    must return an AssetItem with type='svg', resolution='vector', and
    a prompt field that contains a valid SVG block.
    """
    # Arrange — mock the LLM client so no API call is made
    mock_get_llm.return_value = MagicMock()

    # Mock Crew so kickoff() returns the valid SVG string
    mock_crew_instance = MockCrew.return_value
    mock_kickoff_result = MagicMock()
    mock_kickoff_result.__str__ = lambda self: VALID_SVG
    mock_crew_instance.kickoff.return_value = mock_kickoff_result

    service = AssetService()

    # Act
    asset = await service.resolve_visual_cue(
        cue="a friendly robot waving hello",
        scene_id="scene_01",
        cue_id="cue_01",
        asset_id="asset_01",
        video_id="video_01",
        supabase_client=None,
    )

    # Assert schema contract
    assert isinstance(asset, AssetItem), "resolve_visual_cue must return an AssetItem"
    assert asset.asset_type == "svg", "asset_type must be 'svg'"
    assert asset.resolution == "vector", "resolution must be 'vector'"
    assert asset.source == "generated-svg"

    # Assert SVG validity
    svg_code = asset.prompt
    assert svg_code is not None, "prompt (svg code) must not be None"
    assert svg_code.strip().startswith("<svg"), "output must start with <svg"
    assert svg_code.strip().endswith("</svg>"), "output must end with </svg>"
    assert "LLM not available" not in svg_code
    assert "SVG generation failed" not in svg_code


@pytest.mark.asyncio
@patch("backend.app.services.assets.images.Crew")
@patch("backend.app.services.assets.images.AssetService._get_llm_client")
async def test_svg_writer_strips_markdown_fences(mock_get_llm, MockCrew):
    """
    Some LLMs wrap the SVG in markdown fences (```svg ... ```) despite being
    told not to. The service must strip these before validation so a valid
    SVG inside fences is still accepted.
    """
    mock_get_llm.return_value = MagicMock()

    # Return SVG wrapped in markdown fences
    mock_crew_instance = MockCrew.return_value
    mock_kickoff_result = MagicMock()
    mock_kickoff_result.__str__ = lambda self: FENCED_SVG
    mock_crew_instance.kickoff.return_value = mock_kickoff_result

    service = AssetService()
    asset = await service.resolve_visual_cue(
        cue="a padlock representing security",
        scene_id="scene_02",
        cue_id="cue_02",
        asset_id="asset_02",
        video_id="video_01",
        supabase_client=None,
    )

    svg_code = asset.prompt
    assert svg_code.strip().startswith("<svg"), (
        "Fenced SVG should be unwrapped before storage"
    )
    assert "```" not in svg_code, "Markdown fences must be stripped from final output"


# ---------------------------------------------------------------------------
# Fallback / failure-path tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@patch("backend.app.services.assets.images.Crew")
@patch("backend.app.services.assets.images.AssetService._get_llm_client")
async def test_svg_writer_fallback_on_llm_exception(mock_get_llm, MockCrew):
    """
    If the CrewAI kickoff raises an exception, the service must catch it and
    return a placeholder error SVG rather than propagating the exception.
    The placeholder must still be valid SVG (starts with <svg, ends with </svg>).
    """
    mock_get_llm.return_value = MagicMock()

    mock_crew_instance = MockCrew.return_value
    mock_crew_instance.kickoff.side_effect = Exception("Simulated LLM API failure")

    service = AssetService()
    asset = await service.resolve_visual_cue(
        cue="a detailed oil painting of a renaissance castle",
        scene_id="scene_03",
        cue_id="cue_03",
        asset_id="asset_03",
        video_id="video_01",
        supabase_client=None,
    )

    # Service must still return a valid AssetItem
    assert isinstance(asset, AssetItem)

    # The placeholder SVG must be well-formed
    svg_code = asset.prompt
    assert svg_code is not None
    assert svg_code.strip().startswith("<svg"), "Fallback must still produce an <svg> block"

    # The error message embedded by register_asset_in_storage confirms the fallback path
    # (the generation-failure placeholder doesn't start with <svg so storage replaces it
    # with an error SVG — either way the result starts with <svg)
    assert asset.asset_type == "svg"


@pytest.mark.asyncio
@patch("backend.app.services.assets.images.Crew")
@patch("backend.app.services.assets.images.AssetService._get_llm_client")
async def test_svg_writer_fallback_on_non_svg_output(mock_get_llm, MockCrew):
    """
    If the LLM returns text that is NOT a valid SVG block (e.g. a plain
    description), the service must raise ValueError internally and fall back
    to the error placeholder. The returned asset must still be an AssetItem.
    """
    mock_get_llm.return_value = MagicMock()

    mock_crew_instance = MockCrew.return_value
    mock_kickoff_result = MagicMock()
    # Return something that is clearly not SVG
    mock_kickoff_result.__str__ = lambda self: "Here is a flat 2D illustration of a robot."
    mock_crew_instance.kickoff.return_value = mock_kickoff_result

    service = AssetService()
    asset = await service.resolve_visual_cue(
        cue="a gear icon representing settings",
        scene_id="scene_04",
        cue_id="cue_04",
        asset_id="asset_04",
        video_id="video_01",
        supabase_client=None,
    )

    assert isinstance(asset, AssetItem)
    # Whatever placeholder was stored, it must be wrapped in <svg> by register_asset_in_storage
    assert asset.prompt.strip().startswith("<svg")


@pytest.mark.asyncio
@patch("backend.app.services.assets.images.AssetService._get_llm_client")
async def test_svg_writer_fallback_when_no_llm_available(mock_get_llm):
    """
    If _get_llm_client returns None (no API keys configured), the service
    must immediately return a placeholder SVG — no CrewAI call, no crash.
    """
    mock_get_llm.return_value = None  # Simulate missing API key

    service = AssetService()
    asset = await service.resolve_visual_cue(
        cue="a cloud with an upload arrow",
        scene_id="scene_05",
        cue_id="cue_05",
        asset_id="asset_05",
        video_id="video_01",
        supabase_client=None,
    )

    assert isinstance(asset, AssetItem)
    # The no-LLM placeholder is stored directly in `prompt` before register_asset_in_storage
    # register_asset_in_storage will replace it if it doesn't start with <svg,
    # so the stored value is always SVG-wrapped
    assert asset.prompt.strip().startswith("<svg")
    assert asset.asset_type == "svg"