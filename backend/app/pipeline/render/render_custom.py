"""
Render any ScenePlan JSON file using CrewAI + Gemini customized Jinja2 templates.

Workflow:
1. Ingest ScenePlan JSON (e.g. docker_scene_plan.json).
2. Invoke CrewAI agent to generate a customized Jinja2 template for this specific scene plan.
3. Inject placeholder asset URLs and trigger timing metadata.
4. Validate enriched plan against ScenePlan Pydantic schema (backend/app/schemas/scene.py).
5. Render template using Jinja2 and write out preview HTML.
"""

import json
import sys
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, Template

THIS_DIR = Path(__file__).resolve().parent

# Make backend importable reliably
_repo_root = THIS_DIR
while _repo_root.name != "ai-video-generation-app" and _repo_root.parent != _repo_root:
    _repo_root = _repo_root.parent

if str(_repo_root) not in sys.path:
    sys.path.insert(0, str(_repo_root))

from backend.app.schemas.scene import ScenePlan
from backend.app.pipeline.render.agent_template_generator.crew_agent import (
    generate_template_with_crewai,
)

from backend.app.pipeline.render.agent_template_generator.asset_agent import (
    generate_assets_with_crewai,
)

def get_dummy_trigger_time(cue_id: str) -> float:
    return 0.2


def render_custom_scene_plan(json_path: str) -> str:
    # 1. Load JSON
    with open(json_path, "r", encoding="utf-8") as f:
        plan_dict = json.load(f)

    # 2. Generate custom Jinja2 template for this topic via CrewAI + Gemini
    print(f"[PIPELINE] Generating custom template for topic: '{plan_dict.get('title')}'...")
    custom_template_code = generate_template_with_crewai(plan_dict)

    prefix = Path(json_path).stem.replace("_scene_plan", "")
    template_file = THIS_DIR / f"{prefix}_custom_template.jinja2"
    template_file.write_text(custom_template_code, encoding="utf-8")
    print(f"[OK] Wrote customized template to {template_file.resolve()}")

    # 3. Generate Custom Iconify Assets
    print(f"[PIPELINE] Generating custom Iconify assets...")
    generated_assets = generate_assets_with_crewai(plan_dict)

    # 4. Enrich missing fields and inject asset URLs
    for scene in plan_dict["scenes"]:
        for cue in scene["visual_cues"]:
            aid = cue.get("asset_id")
            if aid and aid in generated_assets:
                cue["asset_url"] = generated_assets[aid]
            else:
                cue["asset_url"] = f"https://placehold.co/400x400/e2e8f0/1e293b?text={cue.get('description', 'Asset').replace(' ', '+')}"
                
            if "trigger_time_seconds" not in cue:
                cue["trigger_time_seconds"] = get_dummy_trigger_time(
                    cue.get("cue_id", "")
                )

    # 5. Validate against Pydantic schema
    print("[PIPELINE] Validating enriched dict against Pydantic ScenePlan schema...")
    ScenePlan(**plan_dict)
    print("[OK] Pydantic validation successful!")

    # 6. Render custom template
    template = Template(custom_template_code)
    return template.render(
        plan=plan_dict,
        SCENE_PLAN_JSON=plan_dict["scenes"]
    )


if __name__ == "__main__":
    target_json = sys.argv[1] if len(sys.argv) > 1 else "langchain_scene_plan.json"
    json_file_path = THIS_DIR / target_json

    if not json_file_path.exists():
        print(f"[ERROR] Specified JSON file does not exist: {json_file_path}")
        sys.exit(1)

    print(f"=== Running Agentic Custom Render Pipeline for: {target_json} ===")
    rendered_html = render_custom_scene_plan(str(json_file_path))

    prefix = json_file_path.stem.replace("_scene_plan", "")
    out_path = THIS_DIR / f"{prefix}_custom_output.html"
    out_path.write_text(rendered_html, encoding="utf-8")


    print(f"\n[SUCCESS] Wrote custom output files:")
    print(f"  - Output:  {out_path.resolve()}")
    print("\nOpen preview HTML file in your browser to watch narrated customized video!")
