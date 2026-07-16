"""
Scene Planner Agent: script -> scene plan with layouts + visual cues (PRD 7.3).
"""
from backend.models.script import VideoScriptBlueprint
from backend.models.scene import ScenePlan
from backend.prompts import scene_planner_agent
from backend.services.ai_client import structured_completion


def plan_scenes(script: VideoScriptBlueprint) -> ScenePlan:
    """Break a structured script into scenes with layout + visual element cues."""
    return structured_completion(
        system_prompt=scene_planner_agent.SYSTEM_PROMPT,
        user_prompt=scene_planner_agent.build_user_prompt(script.model_dump_json()),
        response_model=ScenePlan,
    )
