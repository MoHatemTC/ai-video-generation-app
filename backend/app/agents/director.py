import os
import json
import logging
from typing import Dict, Any, Optional

from crewai import Agent, Task, Crew, LLM
import litellm

from ..schemas.scene import ScenePlan, SceneQualityReport
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
    ):
        self.api_key = api_key or os.getenv("LITELLM_API_KEY")
        if not self.api_key:
            raise ValueError("LITELLM_API_KEY must be set in environment or passed.")
        self.base_url = base_url
        self.model_name = model_name
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.max_retries = max_retries

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
            expected_output="A SceneQualityReport JSON with scores, issues, and revision instructions.",
            output_json=SceneQualityReport,
            agent=self.agent,
        )

    async def evaluate(self, script_input: Dict[str, Any], scene_plan: ScenePlan) -> SceneQualityReport:
        original_base = litellm.api_base
        original_key = litellm.api_key
        try:
            litellm.api_base = self.base_url
            litellm.api_key = self.api_key
            task = self._build_task(script_input, scene_plan)
            for attempt in range(1, self.max_retries + 1):
                try:
                    crew = Crew(
                        agents=[self.agent],
                        tasks=[task],
                        verbose=False,
                    )
                    result = await crew.kickoff_async()
                    data = json.loads(result.raw)
                    return SceneQualityReport(**data)
                except (json.JSONDecodeError, ValueError) as e:
                    if attempt == self.max_retries:
                        raise RuntimeError(f"Quality evaluation failed after {self.max_retries} attempts.") from e
                    corrected = await self._retry_correction(script_input, scene_plan, str(e), attempt)
                    if corrected:
                        return corrected
        finally:
            litellm.api_base = original_base
            litellm.api_key = original_key
        raise RuntimeError("Unexpected failure in evaluate.")

    async def _retry_correction(
        self,
        script_input: Dict,
        scene_plan: ScenePlan,
        error_msg: str,
        attempt: int,
    ) -> Optional[SceneQualityReport]:
        user_prompt = DIRECTOR_TASK_TEMPLATE.format(
            script=json.dumps(script_input, indent=2),
            scene_plan=json.dumps(scene_plan.model_dump(), indent=2),
        ) + "\n\n" + RETRY_PROMPT.format(error=error_msg)

        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ]
        response = await litellm.acompletion(
            model=self.model_name,
            messages=messages,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
            api_key=self.api_key,
            base_url=self.base_url,
        )
        raw = response.choices[0].message.content
        raw = raw.strip()
        if raw.startswith("```json"):
            raw = raw[7:]
        if raw.endswith("```"):
            raw = raw[:-3]
        raw = raw.strip()
        try:
            data = json.loads(raw)
            return SceneQualityReport(**data)
        except Exception:
            return None