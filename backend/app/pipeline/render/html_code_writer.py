"""
HTML Code Writer Agent — populates static Jinja2 templates using CrewAI + Gemini.

Given a scene object, its assigned template HTML fragment, and resolved asset URLs,
the agent decides the best placement of assets within the template structure and
returns a populated HTML fragment ready for merging.

Falls back to direct Jinja2 rendering if the LLM call fails (templates are already
Jinja2-compatible, so pure rendering always works).
"""

import os
import json
import logging
import asyncio
from pathlib import Path
from dotenv import load_dotenv
from jinja2 import Template

logger = logging.getLogger(__name__)

THIS_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = THIS_DIR.parents[3]  # ai-video-generation-app/
load_dotenv(PROJECT_ROOT / ".env")   # Load root .env first (GEMINI_API_KEY)
load_dotenv(THIS_DIR / ".env", override=False)  # Then local overrides

try:
    from crewai import Agent, Task, Crew, Process, LLM
    HAS_CREWAI = True
except ImportError:
    HAS_CREWAI = False


def normalize_model_name(raw_name: str) -> str:
    """Normalize user configured model name for CrewAI Google Gemini integration."""
    if not raw_name:
        return "gemini/gemini-pro-latest"
    clean = raw_name.strip()
    if clean.startswith("gemini/") or clean.startswith("google/"):
        return clean
    return f"gemini/{clean.lower().replace(' ', '-')}"


# ─── PROMPT BUILDER ───────────────────────────────────────────────────────────

def _build_writer_prompt(scene: dict, template_html: str, plan_context: dict) -> str:
    """Build the agent prompt for populating a single scene template adhering to Playwright renderer guardrails."""
    return f"""
You are the `html_code_writer` agent. Your objective is to populate self-contained HTML scene fragments for automated headless video capture via Playwright.

═══════════════════════════════════════════
SPRINT 4 TASK 4 SPECIFICATIONS & COMPATIBILITY
═══════════════════════════════════════════

1. INTRO BG MUSIC & TTS SUPPRESSION:
   - The intro scene (`data-template="intro"`) plays `#intro-bg-music` automatically.
   - TTS narration is suppressed during intro scene. Narration resumes automatically on Scene 2+.

2. SVG EMBEDDING INTERFACE (OMAR KHALED INTEGRATION):
   - Wrap visual/concept vector assets in `.svg-embed-slot` containers:
     `<div class="svg-embed-slot" data-svg-id="concept_name" data-author="Omar Khaled">`
     `  <!-- OMAR_KHALED_SVG_START -->`
     `  <svg class="concept-svg float" viewBox="0 0 300 300" fill="none" aria-label="Visual">`
     `    ...`
     `  </svg>`
     `  <!-- OMAR_KHALED_SVG_END -->`
     `</div>`
   - Use CSS root color variables inside SVGs (`var(--c1)`, `var(--c2)`, `var(--c3)`, `var(--text)`, `var(--bg)`).

3. MANDATORY RENDERER COMPATIBILITY RULES:
   - CSS ANIMATIONS ONLY: Use CSS `@keyframes` and transitions exclusively. Prohibited: SMIL (`<animate>`), manual `requestAnimationFrame`, GSAP, or Anime.js.
   - SVG TRANSFORM SAFETY: NEVER place a CSS animated transform directly on an SVG element with static `transform="translate(...)"`. Use double-nested `<g>` tags: outer `<g transform="...">` static position, inner `<g class="...">` for CSS animation target.
   - EMOJI PROHIBITION: Do NOT use raw emoji characters inside SVG or HTML `<text>` nodes. Use vector shapes/icons instead.
   - NO VIEWPORT BACKDROP-FILTER: Do not use viewport-wide `backdrop-filter` effects.
   - INSTANT SCENE CUTS: Hard scene transitions without multi-hundred-millisecond crossfades.
   - ANIMATION RESET CATEGORIZATION:
     • Continuous loops: `.float`, `.float-reverse`, `.pulse-soft`
     • One-shot entrances: `.fade-up`, `.pop-in`, `.slide-in-left`, `.slide-in-right`, `.scale-in`

═══════════════════════════════════════════
TEMPLATE POPULATION RULES
═══════════════════════════════════════════

1. DO NOT change the layout structure, CSS classes, or animation classes in the template.
2. DO NOT invent new HTML elements or CSS. Work strictly within the template.
3. DO NOT remove any elements from the template.
4. Replace ALL Jinja2 placeholders ({{{{ }}}}, {{% %}}) with the actual data values.
5. For asset images, use the EXACT `asset_url` from the scene data. DO NOT invent URLs.
6. Every image/icon tag MUST keep its animation class (float, float-reverse, pulse-soft).
7. Output ONLY the raw HTML fragment. No markdown, no code blocks, no explanation.

═══════════════════════════════════════════
SCENE DATA
═══════════════════════════════════════════

Scene ID: {scene.get('scene_id', 'unknown')}
Text (narration): {scene.get('text', '')}
Subtitle: {scene.get('subtitle', '')}
Layout Hint: {scene.get('layout_hint', '')}
Template: {scene.get('template', '')}

Visual Cues:
{json.dumps(scene.get('visual_cues', []), indent=2, ensure_ascii=False)}

═══════════════════════════════════════════
PLAN CONTEXT
═══════════════════════════════════════════

Title: {plan_context.get('title', 'Explainer Video')}

═══════════════════════════════════════════
TEMPLATE TO POPULATE
═══════════════════════════════════════════

{template_html}

═══════════════════════════════════════════
OUTPUT
═══════════════════════════════════════════

Return the fully populated HTML fragment with all Jinja2 placeholders replaced
by actual values from the scene data. Output ONLY raw HTML.
"""



# ─── JINJA2 FALLBACK RENDERER ─────────────────────────────────────────────────

def _render_template_jinja2(template_html: str, scene: dict, plan: dict) -> str:
    """
    Direct Jinja2 rendering — always works since templates use standard
    Jinja2 syntax with the same variable names as the scene data.
    """
    tmpl = Template(template_html)
    return tmpl.render(scene=scene, plan=plan)


# ─── MAIN AGENT FUNCTION ──────────────────────────────────────────────────────

def populate_scene_template(
    scene: dict,
    template_html: str,
    plan_context: dict,
    use_llm: bool = True,
) -> str:
    """
    Populate a static template fragment for a single scene.

    Parameters
    ----------
    scene : dict
        One scene from the ScenePlan, with visual_cues already enriched
        with ``asset_url`` fields.
    template_html : str
        The raw Jinja2 HTML template string for this scene's template type.
    plan_context : dict
        Top-level ScenePlan dict (used for ``plan.title`` etc.).
    use_llm : bool
        If True, attempt to use CrewAI + Gemini for intelligent population.
        If False (or if the LLM call fails), fall back to direct Jinja2 render.

    Returns
    -------
    str
        The fully populated HTML fragment for this scene.
    """
    import re
    import time

    # ── Try LLM-assisted population ──
    if use_llm:
        api_key = os.getenv("LITELLM_API_KEY") or os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        litellm_base = os.getenv("LITELLM_BASE_URL", "https://learner-os.sprints.ai/litellm/v1")
        if api_key and not api_key.startswith("your_") and "key_here" not in api_key and HAS_CREWAI:
            os.environ["OPENAI_API_KEY"] = api_key
            os.environ["OPENAI_API_BASE"] = litellm_base
            from backend.app.config.model_config import format_model_for_litellm_proxy
            raw_model = os.getenv("MODEL_NAME", "gemini/gemini-2.0-flash")
            model_name = format_model_for_litellm_proxy(raw_model)

            max_retries = 3
            for attempt in range(max_retries):
                try:
                    llm_kwargs = {
                        "model": model_name,
                        "api_key": api_key,
                        "base_url": litellm_base,
                        "temperature": 0.05
                    }
                    llm = LLM(**llm_kwargs)
                    writer = Agent(
                        role="HTML5 Template Population Specialist",
                        goal="Populate Jinja2 HTML templates with scene data accurately without changing layout or inventing content.",
                        backstory=(
                            "You are an expert at taking structured data and inserting it into "
                            "HTML templates precisely. You never change the template structure, "
                            "never invent assets or text, and always preserve animation classes."
                        ),
                        verbose=False,
                        allow_delegation=False,
                        llm=llm,
                    )

                    prompt = _build_writer_prompt(scene, template_html, plan_context)
                    task = Task(
                        description=prompt,
                        expected_output="A fully populated HTML fragment with all Jinja2 placeholders replaced by actual data values. Raw HTML only, no markdown.",
                        agent=writer,
                    )

                    crew = Crew(agents=[writer], tasks=[task], process=Process.sequential)
                    try:
                        import concurrent.futures
                        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                            fut = pool.submit(lambda: asyncio.run(crew.kickoff_async()))
                            result = fut.result(timeout=90)
                    except Exception as k_err:
                        logger.warning(f"CrewAI kickoff_async error: {k_err}. Using direct Jinja2 rendering.")
                        return _render_template_jinja2(template_html, scene, plan_context)
                    raw_text = getattr(result, "raw", None) or str(result)
                    html_output = str(raw_text).strip()

                    # Clean potential markdown fences and Jinja comments
                    for fence in ["```html", "```jinja2", "```jinja", "```"]:
                        if html_output.startswith(fence):
                            html_output = html_output[len(fence):]
                            break
                    if html_output.rstrip().endswith("```"):
                        html_output = html_output.rstrip()[:-3]

                    # Strip any stray Jinja comment tags {# ... #}
                    html_output = re.sub(r'\{#.*?#\}', '', html_output, flags=re.DOTALL)
                    html_output = html_output.strip()

                    if html_output and len(html_output) > 20:
                        print(f"  [HTML WRITER] LLM populated scene {scene.get('scene_id', '?')} successfully")
                        return html_output

                except Exception as err:
                    err_str = str(err)
                    # Retry on 429 rate-limit errors with exponential backoff
                    if "429" in err_str or "RESOURCE_EXHAUSTED" in err_str:
                        wait_time = 10 * (2 ** attempt)  # 10s, 20s, 40s
                        print(f"  [HTML WRITER] Rate limited on scene {scene.get('scene_id', '?')} "
                              f"(attempt {attempt + 1}/{max_retries}). Retrying in {wait_time}s...")
                        time.sleep(wait_time)
                        continue
                    print(f"  [HTML WRITER WARNING] LLM error for scene {scene.get('scene_id', '?')}: {err}")
                    break  # Non-retryable error

    # ── Fallback: direct Jinja2 rendering ──
    print(f"  [HTML WRITER] Using Jinja2 fallback for scene {scene.get('scene_id', '?')}")
    return _render_template_jinja2(template_html, scene, plan_context)
