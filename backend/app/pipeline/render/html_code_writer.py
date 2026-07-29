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
from pathlib import Path
from dotenv import load_dotenv
from jinja2 import Template

THIS_DIR = Path(__file__).resolve().parent
load_dotenv(THIS_DIR / ".env")

try:
    from crewai import Agent, Task, Crew, Process, LLM
    HAS_CREWAI = True
except ImportError:
    HAS_CREWAI = False


def normalize_model_name(raw_name: str) -> str:
    """Normalize user configured model name for CrewAI Google Gemini integration."""
    if not raw_name:
        return "gemini/gemini-3.5-flash-lite"
    clean = raw_name.strip()
    if clean.startswith("gemini/") or clean.startswith("google/"):
        return clean
    return f"gemini/{clean.lower().replace(' ', '-')}"


# ─── PROMPT BUILDER ───────────────────────────────────────────────────────────

def _build_writer_prompt(scene: dict, template_html: str, plan_context: dict) -> str:
    """Build the agent prompt for populating a single scene template."""
    return f"""
You are a Senior HTML5 Template Population Specialist.

Your job is to take a STATIC Jinja2 HTML template fragment and a scene's data,
and produce the FINAL rendered HTML fragment with all placeholders filled in.

═══════════════════════════════════════════
RULES
═══════════════════════════════════════════

1. DO NOT change the layout structure, CSS classes, or animation classes in the template.
2. DO NOT invent new HTML elements or CSS. Work strictly within the template.
3. DO NOT remove any elements from the template.
4. Replace ALL Jinja2 placeholders ({{{{ }}}}, {{% %}}) with the actual data values.
5. For asset images, use the EXACT `asset_url` from the scene data. DO NOT invent URLs.
6. Every `<img>` tag MUST keep its animation class (float, float-reverse, pulse-soft).
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
    # ── Try LLM-assisted population ──
    if use_llm:
        api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        if api_key and not api_key.startswith("your_") and "key_here" not in api_key and HAS_CREWAI:
            try:
                raw_model = os.getenv("MODEL_NAME", "gemini/gemini-3.5-flash")
                model_name = normalize_model_name(raw_model)

                llm = LLM(model=model_name, api_key=api_key, temperature=0.05)
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
                result = crew.kickoff()
                html_output = str(result.raw).strip()

                # Clean potential markdown fences and Jinja comments
                for fence in ["```html", "```jinja2", "```jinja", "```"]:
                    if html_output.startswith(fence):
                        html_output = html_output[len(fence):]
                        break
                if html_output.rstrip().endswith("```"):
                    html_output = html_output.rstrip()[:-3]

                # Strip any stray Jinja comment tags {# ... #}
                import re
                html_output = re.sub(r'\{#.*?#\}', '', html_output, flags=re.DOTALL)
                html_output = html_output.strip()

                if html_output and len(html_output) > 20:
                    print(f"  [HTML WRITER] LLM populated scene {scene.get('scene_id', '?')} successfully")
                    return html_output

            except Exception as err:
                print(f"  [HTML WRITER WARNING] LLM error for scene {scene.get('scene_id', '?')}: {err}")

    # ── Fallback: direct Jinja2 rendering ──
    print(f"  [HTML WRITER] Using Jinja2 fallback for scene {scene.get('scene_id', '?')}")
    return _render_template_jinja2(template_html, scene, plan_context)
