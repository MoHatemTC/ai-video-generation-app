"""
SVG Generator Agent — Generates unique, concept-tailored inline SVGs per scene.

Uses CrewAI + Gemini LLM to analyze each scene's narration, layout hint,
and visual cues, returning high-quality, compliant inline SVG code for every scene.
"""

import os
import json
import logging
import asyncio
import concurrent.futures
from typing import Any, Dict, List, Optional
from pathlib import Path
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

THIS_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = THIS_DIR.parents[3]
load_dotenv(PROJECT_ROOT / ".env")
load_dotenv(THIS_DIR / ".env", override=False)

try:
    from crewai import Agent, Task, Crew, Process, LLM
    HAS_CREWAI = True
except ImportError:
    HAS_CREWAI = False


def _get_llm_instance():
    """Get a valid CrewAI LLM instance using the project model configuration."""
    if "PYTEST_CURRENT_TEST" in os.environ or os.getenv("FAST_SVG_MODE") == "1":
        return None

    api_key = os.getenv("LITELLM_API_KEY") or os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    litellm_base = os.getenv("LITELLM_BASE_URL", "https://learner-os.sprints.ai/litellm/v1")
    if not api_key or api_key.startswith("your_") or "key_here" in api_key or not HAS_CREWAI:
        return None

    os.environ["OPENAI_API_KEY"] = api_key
    os.environ["OPENAI_API_BASE"] = litellm_base

    from backend.app.config.model_config import get_planner_config
    config = get_planner_config()
    model_name = config.get("model_name", "openai/gemini/gemini-3.5-flash-lite")
    
    try:
        return LLM(
            model=model_name,
            api_key=config.get("api_key", api_key),
            base_url=config.get("base_url", litellm_base),
            temperature=0.2
        )
    except Exception as e:
        logger.warning(f"[SVG AGENT] Could not initialize LLM: {e}")
        return None


def generate_unique_fallback_svg(scene: dict, scene_index: int = 0, total_scenes: int = 1, video_title: str = "") -> str:
    """
    Generates a unique, deterministic fallback SVG graphic specifically tailored
    to the scene's index, scene_id, template, and content.
    Guarantees no two scenes share the same visual structure.
    """
    text = (scene.get("text") or scene.get("subtitle") or "").lower()
    hint = (scene.get("layout_hint") or scene.get("template") or "").lower()
    sid = str(scene.get("scene_id", scene_index + 1))
    cues = scene.get("visual_cues", [])
    cue_desc = cues[0].get("description", "") if cues else ""

    # Unique theme selector based on scene_index % 6
    theme = scene_index % 6

    if theme == 0 or "intro" in hint or scene_index == 0:
        # Theme 0: Central Orb & Orbiting Nodes (Intro / Hero)
        return f'''<svg class="concept-svg float" viewBox="0 0 300 240" fill="none" xmlns="http://www.w3.org/2000/svg" aria-label="Scene {sid} Intro Hero SVG">
  <g transform="translate(150, 120)">
    <g class="pulse-soft">
      <circle cx="0" cy="0" r="75" fill="var(--c1, #0ea5e9)" fill-opacity="0.1" stroke="var(--c1, #0ea5e9)" stroke-width="2" stroke-dasharray="6 6"/>
      <circle cx="0" cy="0" r="50" fill="var(--c2, #06b6d4)" fill-opacity="0.2" stroke="var(--c2, #06b6d4)" stroke-width="3"/>
    </g>
    <g class="float-reverse">
      <rect x="-25" y="-25" width="50" height="50" rx="14" fill="var(--c1, #0ea5e9)" fill-opacity="0.85" transform="rotate(45)"/>
      <path d="M-10 -5 L0 10 L12 -10" stroke="#ffffff" stroke-width="4" stroke-linecap="round" stroke-linejoin="round" fill="none"/>
    </g>
    <g transform="translate(65, -45)">
      <g class="float">
        <circle cx="0" cy="0" r="16" fill="var(--c3, #38bdf8)"/>
        <path d="M-6 0 L6 0 M0 -6 L0 6" stroke="#ffffff" stroke-width="2.5" stroke-linecap="round"/>
      </g>
    </g>
    <g transform="translate(-65, 45)">
      <g class="float-reverse">
        <circle cx="0" cy="0" r="14" fill="var(--c2, #06b6d4)"/>
      </g>
    </g>
  </g>
</svg>'''

    elif theme == 1 or "card" in hint or "list" in hint:
        # Theme 1: Stacked Modular Panels
        return f'''<svg class="concept-svg float" viewBox="0 0 300 220" fill="none" xmlns="http://www.w3.org/2000/svg" aria-label="Scene {sid} Modular Panels SVG">
  <g transform="translate(150, 110)">
    <g transform="translate(-70, -45)">
      <g class="pulse-soft">
        <rect x="0" y="0" width="140" height="90" rx="16" fill="rgba(255,255,255,0.7)" stroke="var(--c1, #3b82f6)" stroke-width="2.5"/>
      </g>
    </g>
    <g transform="translate(-50, -25)">
      <g class="float">
        <rect x="0" y="0" width="100" height="50" rx="12" fill="var(--c1, #3b82f6)" fill-opacity="0.2"/>
        <path d="M15 25 L30 25 M40 25 L75 25" stroke="var(--c1, #3b82f6)" stroke-width="4" stroke-linecap="round"/>
      </g>
    </g>
    <g transform="translate(45, -35)">
      <g class="float-reverse">
        <circle cx="0" cy="0" r="20" fill="var(--c2, #8b5cf6)"/>
        <path d="M-8 0 L8 0 M0 -8 L0 8" stroke="#ffffff" stroke-width="3" stroke-linecap="round"/>
      </g>
    </g>
  </g>
</svg>'''

    elif theme == 2 or "flow" in hint or "process" in hint or "network" in text:
        # Theme 2: Connected Node Pipeline
        return f'''<svg class="concept-svg float" viewBox="0 0 300 220" fill="none" xmlns="http://www.w3.org/2000/svg" aria-label="Scene {sid} Pipeline SVG">
  <g transform="translate(150, 110)">
    <g class="pulse-soft">
      <path d="M-80 0 L80 0" stroke="var(--c1, #0ea5e9)" stroke-width="4" stroke-dasharray="8 6"/>
    </g>
    <g transform="translate(-70, 0)">
      <g class="float">
        <circle cx="0" cy="0" r="24" fill="var(--c1, #0ea5e9)"/>
        <rect x="-10" y="-10" width="20" height="20" rx="4" fill="#ffffff" fill-opacity="0.9"/>
      </g>
    </g>
    <g transform="translate(0, 0)">
      <g class="pulse-soft">
        <circle cx="0" cy="0" r="28" fill="var(--c2, #06b6d4)"/>
        <path d="M-10 -6 L10 -6 M-10 6 L10 6" stroke="#ffffff" stroke-width="3.5" stroke-linecap="round"/>
      </g>
    </g>
    <g transform="translate(70, 0)">
      <g class="float-reverse">
        <circle cx="0" cy="0" r="24" fill="var(--c3, #38bdf8)"/>
        <path d="M-6 -6 L6 6 M6 -6 L-6 6" stroke="#ffffff" stroke-width="3.5" stroke-linecap="round"/>
      </g>
    </g>
  </g>
</svg>'''

    elif theme == 3 or "risk" in hint or "security" in text or "shield" in cue_desc:
        # Theme 3: Security Shield / Core Badge
        return f'''<svg class="concept-svg float" viewBox="0 0 300 220" fill="none" xmlns="http://www.w3.org/2000/svg" aria-label="Scene {sid} Security Shield SVG">
  <g transform="translate(150, 110)">
    <g class="pulse-soft">
      <path d="M0 -55 L45 -35 V15 C45 45 0 65 0 65 C0 65 -45 45 -45 15 V-35 Z" fill="var(--c1, #10b981)" fill-opacity="0.15" stroke="var(--c1, #10b981)" stroke-width="3"/>
    </g>
    <g class="float-reverse">
      <path d="M0 -40 L32 -25 V10 C32 32 0 48 0 48 C0 48 -32 32 -32 10 V-25 Z" fill="var(--c1, #10b981)"/>
      <path d="M-10 2 L-2 10 L12 -6" stroke="#ffffff" stroke-width="4" stroke-linecap="round" stroke-linejoin="round" fill="none"/>
    </g>
  </g>
</svg>'''

    elif theme == 4 or "recap" in hint or "outro" in hint or scene_index == total_scenes - 1:
        # Theme 4: Verified Checkmark Medallion (Outro / Recap)
        return f'''<svg class="concept-svg float" viewBox="0 0 300 220" fill="none" xmlns="http://www.w3.org/2000/svg" aria-label="Scene {sid} Verified Medallion SVG">
  <g transform="translate(150, 110)">
    <g class="pulse-soft">
      <circle cx="0" cy="0" r="65" fill="var(--c1, #22c55e)" fill-opacity="0.12" stroke="var(--c1, #22c55e)" stroke-width="3"/>
    </g>
    <g class="float">
      <circle cx="0" cy="0" r="45" fill="var(--c1, #22c55e)"/>
      <path d="M-15 0 L-4 12 L18 -10" stroke="#ffffff" stroke-width="5" stroke-linecap="round" stroke-linejoin="round" fill="none"/>
    </g>
    <g transform="translate(50, -35)">
      <g class="float-reverse">
        <circle cx="0" cy="0" r="14" fill="var(--c2, #eab308)"/>
      </g>
    </g>
  </g>
</svg>'''

    else:
        # Theme 5: Dynamic Dual Orb / Concept Bridge
        return f'''<svg class="concept-svg float" viewBox="0 0 300 220" fill="none" xmlns="http://www.w3.org/2000/svg" aria-label="Scene {sid} Dual Orb SVG">
  <g transform="translate(150, 110)">
    <g class="pulse-soft">
      <rect x="-85" y="-50" width="170" height="100" rx="20" fill="rgba(255,255,255,0.7)" stroke="var(--c1, #8b5cf6)" stroke-width="2.5"/>
    </g>
    <g class="float-reverse">
      <circle cx="-35" cy="0" r="24" fill="var(--c1, #8b5cf6)" fill-opacity="0.85"/>
      <circle cx="35" cy="0" r="24" fill="var(--c2, #ec4899)" fill-opacity="0.85"/>
      <path d="M-15 0 L15 0" stroke="var(--c3, #a78bfa)" stroke-width="4" stroke-dasharray="4 4"/>
    </g>
  </g>
</svg>'''


def generate_scene_svg_with_llm(llm: Any, scene: dict, video_title: str) -> str:
    """Generate custom inline SVG string for a single scene via LLM Agent."""
    sid = scene.get("scene_id", "1")
    narration = scene.get("text") or scene.get("subtitle") or ""
    cues = scene.get("visual_cues", [])
    layout_hint = scene.get("layout_hint", "general")

    cues_summary = ", ".join([c.get("description", "") for c in cues if c.get("description")])

    prompt = f"""
You are the `SceneSVGGeneratorAgent`. Your job is to design a unique, beautiful inline SVG illustration for Scene '{sid}' of an explainer video on '{video_title}'.

Scene Narration: "{narration}"
Layout Hint: {layout_hint}
Visual Cues: {cues_summary}

MANDATORY SVG RENDERER COMPATIBILITY RULES:
1. CSS ANIMATION ONLY:
   - Use CSS keyframes / classes on elements (e.g. `class="concept-svg float"`, `class="pulse-soft"`, `class="float-reverse"`).
   - NEVER use SMIL `<animate>` or `<animateTransform>` tags inside SVG.
2. SVG TRANSFORM CONFLICT SAFETY:
   - NEVER put a CSS animation class directly on an element with a static `transform="translate(...)"`.
   - Use double-nested `<g>` tags: outer `<g transform="...">` static position, inner `<g class="...">` for animation target.
3. NO RAW EMOJI:
   - Do NOT output emoji characters in `<text>` nodes. Draw shapes/icons with SVG path/circle/rect/polygon.
4. COLOR VARIABLES:
   - Use CSS color variables: `var(--c1, #0ea5e9)`, `var(--c2, #06b6d4)`, `var(--c3, #38bdf8)`.
5. FORMAT & SIZE:
   - Must be valid `<svg viewBox="0 0 300 220" fill="none" xmlns="http://www.w3.org/2000/svg" class="concept-svg float">...</svg>`.
   - Output ONLY the raw SVG markup string. No markdown fences, no explanations.
"""
    try:
        agent = Agent(
            role="SVG Vector Illustration Specialist",
            goal="Generate elegant, unique, compliant inline SVG code for a specific explainer scene.",
            backstory="You design vector motion graphics for tech videos. You strictly follow SVG animation guardrails.",
            verbose=False,
            allow_delegation=False,
            llm=llm
        )
        task = Task(
            description=prompt,
            expected_output="A single valid <svg>...</svg> markup string with CSS class animations. Raw SVG string only.",
            agent=agent
        )
        crew = Crew(agents=[agent], tasks=[task], process=Process.sequential)
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(crew.kickoff)
            result = future.result(timeout=90)
        
        raw_text = getattr(result, "raw", None) or str(result)
        svg_code = str(raw_text).strip()

        # Clean markdown wrappers if any
        for fence in ["```xml", "```svg", "```html", "```"]:
            if svg_code.startswith(fence):
                svg_code = svg_code[len(fence):]
                break
        if svg_code.rstrip().endswith("```"):
            svg_code = svg_code.rstrip()[:-3]

        svg_code = svg_code.strip()
        if "<svg" in svg_code and "</svg>" in svg_code:
            return svg_code
        else:
            logger.warning(f"[SVG AGENT WARNING] LLM returned non-SVG output for scene {sid} (length={len(svg_code)})")
    except concurrent.futures.TimeoutError:
        logger.warning(f"[SVG AGENT WARNING] LLM SVG generation timed out for scene {sid} (90s limit)")
    except Exception as err:
        logger.warning(f"[SVG AGENT WARNING] LLM SVG generation failed for scene {sid}: {type(err).__name__}: {err}")

    return ""


def generate_scene_svgs_for_plan(scene_plan_dict: dict) -> dict:
    """
    Main entrypoint: returns a dict mapping scene_id -> unique inline SVG code string.
    Generates a unique SVG for EVERY scene in the scene plan.
    """
    scenes = scene_plan_dict.get("scenes", [])
    video_title = scene_plan_dict.get("title", "Explainer Video")

    svg_results = {}
    llm = _get_llm_instance()
    total_scenes = len(scenes)

    if llm:
        print(f"[SVG AGENT] Generating unique SVGs for all {total_scenes} scenes (LLM active: {getattr(llm, 'model', 'unknown')})...")
    else:
        print(f"[SVG AGENT] Generating unique SVGs for all {total_scenes} scenes (deterministic fallback, no LLM)...")

    for idx, scene in enumerate(scenes):
        sid = str(scene.get("scene_id", idx + 1))
        existing = scene.get("generated_svg") or scene.get("svg_code") or scene.get("svg")

        if existing and isinstance(existing, str) and "<svg" in existing:
            svg_results[sid] = existing
            continue

        svg_code = ""
        if llm:
            try:
                svg_code = generate_scene_svg_with_llm(llm, scene, video_title)
            except Exception as e:
                logger.warning(f"[SVG AGENT] LLM SVG call error for scene {sid}: {type(e).__name__}: {e}")

            # Small delay between LLM calls to avoid rate limiting
            if idx < total_scenes - 1:
                import time
                time.sleep(1)

        if not svg_code or "<svg" not in svg_code:
            svg_code = generate_unique_fallback_svg(scene, scene_index=idx, total_scenes=total_scenes, video_title=video_title)

        svg_results[sid] = svg_code
        print(f"  [SVG AGENT] Generated SVG for scene {sid} (length: {len(svg_code)} chars)")

    return svg_results
