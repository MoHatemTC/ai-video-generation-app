"""
Unit tests for Sprint 4 Task 4: Enhanced Animated HTML Video Generation.
Validates:
1. Intro background music HTML audio tag insertion.
2. Intro TTS suppression and background music autoplay JS engine logic.
3. SVG embedding interface (.svg-embed-slot and data-author="Omar Khaled").
4. Emoji prohibition check across templates and output.
5. Renderer compatibility prompt rules in html_code_writer.
"""

import pytest
from pathlib import Path
from backend.app.pipeline.render.render_custom import generate_video_html
from backend.app.pipeline.render.html_code_writer import _build_writer_prompt

@pytest.fixture
def sample_scene_plan():
    return {
        "video_id": "test_sprint4_v1",
        "title": "Object-Oriented Programming Principles",
        "total_duration_seconds": 26.2,
        "scenes": [
            {
                "scene_id": "scene_1",
                "text": "Welcome to Object-Oriented Programming. Let's break down the four core pillars.",
                "subtitle": "Welcome to OOP",
                "layout_hint": "title-card",
                "template": "intro",
                "hold_ms": 13200,
                "visual_cues": [
                    {
                        "cue_id": "cue_intro",
                        "description": "OOP Overview Hero",
                        "asset_url": "https://api.iconify.design/lucide/box.svg?color=%230ea5e9"
                    }
                ]
            },
            {
                "scene_id": "scene_2",
                "text": "Before we dive in, let's preview the four pillars we'll cover.",
                "subtitle": "The Four Pillars",
                "layout_hint": "cards",
                "template": "content_b",
                "hold_ms": 13000,
                "visual_cues": [
                    {
                        "cue_id": "cue_pillars",
                        "description": "4 Pillars Overview",
                        "asset_url": "https://api.iconify.design/lucide/layers.svg?color=%230ea5e9"
                    }
                ]
            },
            {
                "scene_id": "scene_3",
                "text": "In summary, these pillars make software modular and scalable.",
                "subtitle": "Summary",
                "layout_hint": "outro-checklist",
                "template": "outro",
                "hold_ms": 8000,
                "visual_cues": [
                    {
                        "cue_id": "cue_recap",
                        "description": "Recap item",
                        "content": "Modular and scalable architecture"
                    }
                ]
            }
        ]
    }


def test_intro_bg_music_tag(sample_scene_plan):
    """Verify that <audio id="intro-bg-music"...> tag is rendered immediately inside #video-frame."""
    html = generate_video_html(sample_scene_plan)
    assert '<audio id="intro-bg-music" src="assets/intro_music.mp3" preload="auto"></audio>' in html
    assert html.index('<div id="video-frame">') < html.index('<audio id="intro-bg-music"')


def test_js_engine_tts_suppression_and_audio(sample_scene_plan):
    """Verify JS runtime engine contains intro audio autoplay and speech suppression logic."""
    html = generate_video_html(sample_scene_plan)
    assert "bgAudio = document.getElementById(\"intro-bg-music\")" in html or 'bgAudio = document.getElementById("intro-bg-music")' in html
    assert "if(isIntro)" in html
    assert "bgAudio.play()" in html
    assert "bgAudio.pause()" in html


def test_svg_embed_slot_interface(sample_scene_plan):
    """Verify that .svg-embed-slot containers with Omar Khaled metadata are present in generated HTML."""
    html = generate_video_html(sample_scene_plan)
    assert 'class="svg-embed-slot"' in html
    assert 'data-author="Omar Khaled"' in html
    assert '<!-- OMAR_KHALED_SVG_START -->' in html
    assert '<!-- OMAR_KHALED_SVG_END -->' in html


def test_no_raw_emojis_in_templates_or_output(sample_scene_plan):
    """Verify that raw emojis (like 🔒) are prohibited and absent from templates and output HTML."""
    templates_dir = Path(__file__).resolve().parents[1] / "app" / "pipeline" / "render" / "templates"
    for tmpl_file in templates_dir.glob("*.html"):
        content = tmpl_file.read_text(encoding="utf-8")
        assert "🔒" not in content, f"Raw emoji found in template: {tmpl_file.name}"
        assert "emoji" not in content or '<div class="emoji">' not in content

    html = generate_video_html(sample_scene_plan)
    assert "🔒" not in html


def test_html_writer_prompt_guardrails():
    """Verify that _build_writer_prompt includes Sprint 4 Task 4 guardrails and Omar Khaled integration."""
    scene = {"scene_id": "s1", "text": "Test narration", "template": "intro", "visual_cues": []}
    plan = {"title": "Test Plan"}
    prompt = _build_writer_prompt(scene, "<div>Test</div>", plan)

    assert "INTRO BG MUSIC & TTS SUPPRESSION" in prompt
    assert "SVG EMBEDDING INTERFACE (OMAR KHALED INTEGRATION)" in prompt
    assert ".svg-embed-slot" in prompt
    assert "EMOJI PROHIBITION" in prompt
    assert "SVG TRANSFORM SAFETY" in prompt


def test_intro_duration_and_tts_start(sample_scene_plan):
    """Verify intro scene hold duration is set to 2.5s (2500ms) and TTS narration starts on Scene 2."""
    html = generate_video_html(sample_scene_plan)
    assert "setTimeout(finish, 2500);" in html
    assert '"holdMs": 2500' in html


def test_generated_svg_placeholder_injection(sample_scene_plan):
    """Verify that #svg-container and generated_svg placeholder embeds custom SVG code when provided."""
    sample_scene_plan["scenes"][0]["generated_svg"] = '<svg id="omar-custom-intro-svg"><circle cx="20" cy="20" r="10"/></svg>'
    html = generate_video_html(sample_scene_plan)

    assert '<div id="svg-container"' in html
    assert '<svg id="omar-custom-intro-svg">' in html


def test_progress_dots_removed(sample_scene_plan):
    """Verify that top progress dots navigation (#progress) is removed from generated HTML."""
    html = generate_video_html(sample_scene_plan)
    assert '<div id="progress">' not in html
    assert '#progress .dot' not in html


def test_no_inter_scene_delay(sample_scene_plan):
    """Verify that inter-scene delay is 0ms (setTimeout(stepSequence, 0)) to eliminate silence."""
    html = generate_video_html(sample_scene_plan)
    assert 'stepTimer = setTimeout(stepSequence, 0);' in html


def test_instant_scene_cut_transition(sample_scene_plan):
    """Verify that .scene transition is set to instant cut (opacity 0.05s ease)."""
    html = generate_video_html(sample_scene_plan)
    assert 'transition:opacity 0.05s ease' in html


def test_automatic_inline_svg_generation(sample_scene_plan):
    """Verify that scenes without pre-existing generated_svg receive an inline SVG directly from scene data."""
    # Clear any explicit generated_svg
    for scene in sample_scene_plan["scenes"]:
        scene.pop("generated_svg", None)
        scene.pop("svg_code", None)

    html = generate_video_html(sample_scene_plan)
    assert '<svg class="concept-svg float"' in html
    assert 'aria-label=' in html and 'SVG' in html


def test_transcript_removed_from_top_display(sample_scene_plan):
    """Verify that full narration transcript text is not displayed in top scene titles, and transcript bar is hidden."""
    sample_scene_plan["scenes"][1]["text"] = "This is a very long narration transcript text that should never be placed in the top scene title header."
    sample_scene_plan["scenes"][1]["subtitle"] = sample_scene_plan["scenes"][1]["text"]

    html = generate_video_html(sample_scene_plan)

    # Full long narration transcript text should NOT appear inside top scene title headers
    assert '<div class="scene-title"><span>This is a very long narration transcript' not in html
    assert '.scene-narration' in html and 'display:none !important;' in html




