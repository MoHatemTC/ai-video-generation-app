import os
import json
import logging
from typing import Dict, Any, Optional

from crewai import Agent, Task, Crew, LLM
import litellm

from ..schemas.scene import ScenePlan, SceneQualityReport, CategoryScores
from ..config.quality import QualityRubric
from ..validators import validate_scene_plan
from ..prompts.planner import SYSTEM_PROMPT, DIRECTOR_TASK_TEMPLATE, RETRY_PROMPT

logger = logging.getLogger(__name__)

class SceneDirector:
    def __init__(
        self,
        model_name: str = "kimi-k2.5",
        temperature: float = 0.2,
        max_tokens: int = 4096,
        api_key: Optional[str] = None,
        base_url: Optional[str] = "https://learner-os.sprints.ai/litellm",
        max_retries: int = 3,
        rubric: Optional[QualityRubric] = None,
    ):
        self.api_key = api_key or os.getenv("LITELLM_API_KEY")
        if not self.api_key:
            raise ValueError("LITELLM_API_KEY must be set in environment or passed.")
        self.base_url = base_url
        self.model_name = model_name
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.max_retries = max_retries
        self.rubric = rubric or QualityRubric.default()

        litellm.api_base = self.base_url
        litellm.api_key = self.api_key

        self.llm = LLM(
            model=model_name,
            api_key=self.api_key,
            temperature=temperature,
            is_litellm=True,
            base_url=self.base_url,
        )

        self.agent = Agent(
            role="Scene Director",
            goal="Evaluate Scene Plan quality and issue precise revision instructions.",
            backstory=(
                "You are an experienced film director and instructional designer. "
                "You review AI-generated storyboards before production. "
                "You identify weaknesses objectively and issue machine‑readable instructions."
            ),
            llm=self.llm,
            verbose=False,
        )

    def _build_task(self, script_input: Dict[str, Any], scene_plan: ScenePlan) -> Task:
        description = DIRECTOR_TASK_TEMPLATE.format(
            script=json.dumps(script_input, indent=2),
            scene_plan=json.dumps(scene_plan.model_dump(), indent=2),
        )
        return Task(
            description=description,
            expected_output=(
                "A JSON object with 'strengths' (list) and 'revision_instructions' (list). "
                "Do not include scores."
            ),
            agent=self.agent,
            # We'll parse manually, not output_json, because we will merge with computed scores
        )

    async def evaluate(self, script_input: Dict[str, Any], scene_plan: ScenePlan) -> SceneQualityReport:
        # 1. Compute deterministic scores and base instructions
        category_scores, auto_instructions, detected_issues = validate_scene_plan(
            script_input, scene_plan, self.rubric
        )

        # 2. Compute overall score using weights
        weighted_sum = 0.0
        for dim in self.rubric.dimensions:
            score = getattr(category_scores, dim.name)
            weighted_sum += score * dim.weight
        overall_score = round(weighted_sum)
        passed = (
            overall_score >= self.rubric.pass_threshold_overall
            and all(
                getattr(category_scores, dim.name) >= self.rubric.pass_threshold_category
                for dim in self.rubric.dimensions
            )
        )

        # 3. Call LLM to get additional strengths and revision instructions
        llm_strengths = []
        llm_instructions = []
        try:
            crew = Crew(
                agents=[self.agent],
                tasks=[self._build_task(script_input, scene_plan)],
                verbose=False,
            )
            result = await crew.kickoff_async()
            raw = result.raw
            # Clean markdown if present
            raw = raw.strip()
            if raw.startswith("```json"):
                raw = raw[7:]
            if raw.endswith("```"):
                raw = raw[:-3]
            raw = raw.strip()
            data = json.loads(raw)
            llm_strengths = data.get("strengths", [])
            llm_instructions = data.get("revision_instructions", [])
        except Exception as e:
            logger.warning(f"LLM evaluation failed, using only deterministic checks: {e}")

        # 4. Merge instructions (auto + LLM)
        # Ensure instruction IDs are unique
        all_instructions = auto_instructions.copy()
        # Convert LLM instructions to RevisionInstruction objects
        for instr in llm_instructions:
            # remove duplicates based on reason? we can just append if new
            # generate ID if missing
            if "instruction_id" not in instr:
                instr["instruction_id"] = f"llm_{len(all_instructions)}"
            try:
                all_instructions.append(RevisionInstruction(**instr))
            except Exception as e:
                logger.warning(f"Skipping invalid LLM instruction: {e}")

        # 5. Build final report
        report = SceneQualityReport(
            overall_score=overall_score,
            passed=passed,
            category_scores=category_scores,
            strengths=llm_strengths or ["Plan is generally well-structured."],
            detected_issues=detected_issues,
            revision_instructions=all_instructions,
        )
        return report