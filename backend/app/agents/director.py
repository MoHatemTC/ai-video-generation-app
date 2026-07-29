import os
import json
import logging
from typing import Dict, Any, Optional

from crewai import Agent, Task, Crew, LLM
try:
    import litellm
except ImportError:
    litellm = None

from ..schemas.scene import ScenePlan, SceneQualityReport, CategoryScores, RevisionInstruction
from ..config.quality import QualityRubric
from ..validators.scene_validator import validate_scene_plan
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
        fallback_config: Optional[Dict[str, Any]] = None,
    ):
        self.fallback_config = fallback_config
        self.api_key = api_key or os.getenv("LITELLM_API_KEY")
        if not self.api_key:
            raise ValueError("LITELLM_API_KEY must be set in environment or passed.")
        self.base_url = base_url
        self.model_name = model_name
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.max_retries = max_retries
        self.rubric = rubric or QualityRubric.default()

        if litellm is not None:
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

    def _switch_to_fallback(self) -> bool:
        if not self.fallback_config:
            return False
            
        logger.warning("Primary LLM failed in Director. Switching to fallback config...")
        self.model_name = self.fallback_config["model_name"]
        self.api_key = self.fallback_config["api_key"]
        self.base_url = self.fallback_config["base_url"]
        
        litellm.api_base = self.base_url
        litellm.api_key = self.api_key
        
        self.llm = LLM(
            model=self.model_name,
            api_key=self.api_key,
            temperature=self.temperature,
            is_litellm=True,
            base_url=self.base_url,
        )
        self.agent.llm = self.llm
        return True

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
            task = self._build_task(script_input, scene_plan)
            messages = [
                {"role": "system", "content": self.agent.backstory},
                {"role": "user", "content": task.description + "\n\n" + task.expected_output}
            ]
            response = await litellm.acompletion(
                model=self.llm.model,
                messages=messages,
                api_key=self.llm.api_key,
                base_url=self.llm.base_url,
                temperature=self.llm.temperature or 0.2
            )
            raw = response.choices[0].message.content
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
            logger.error(f"LLM evaluation failed (API or JSON error): {e}")
            if self._switch_to_fallback():
                # We do a simple recursive retry once if we switch
                # Since we don't have a loop here, we can just call evaluate again
                # But to avoid infinite recursion, we unset the fallback_config before doing so
                self.fallback_config = None
                return await self.evaluate(script_input, scene_plan)
            logger.warning("Falling back to deterministic checks only.")

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