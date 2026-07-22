import os
import json
import logging
from typing import Dict, Any, Optional

from crewai import Agent, Task, Crew, LLM
import litellm

from ..schemas.scene import ScenePlan, SceneQualityReport
from ..prompts.planner import (
    SYSTEM_PROMPT, TASK_TEMPLATE, RETRY_PROMPT, REVISION_TEMPLATE
)

logger = logging.getLogger(__name__)

class ScenePlanner:
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
            role="Scene Planning Agent",
            goal="Convert educational script into storyboard with synchronised visuals.",
            backstory=SYSTEM_PROMPT,
            llm=self.llm,
            verbose=False,
        )

    def _build_task(self, script_input: Dict[str, Any]) -> Task:
        segments_str = json.dumps(script_input.get("segments", []), indent=2)
        word_ts_str = json.dumps(script_input.get("word_timestamps", []), indent=2)
        assets_str = json.dumps(script_input.get("assets", []), indent=2)

        description = TASK_TEMPLATE.format(
            video_id=script_input.get("video_id", "unknown"),
            title=script_input.get("title", "Untitled"),
            total_duration_seconds=script_input.get("total_duration_seconds", 0.0),
            segments=segments_str,
            word_timestamps=word_ts_str,
            assets=assets_str,
        )

        return Task(
            description=description,
            expected_output="A JSON Scene Plan describing scenes, layouts and synchronised visual cues.",
            output_json=ScenePlan,
            agent=self.agent,
        )

    async def plan_scenes(self, script_input: Dict[str, Any]) -> ScenePlan:
        original_base = litellm.api_base
        original_key = litellm.api_key
        try:
            litellm.api_base = self.base_url
            litellm.api_key = self.api_key
            for attempt in range(1, self.max_retries + 1):
                try:
                    crew = Crew(
                        agents=[self.agent],
                        tasks=[self._build_task(script_input)],
                        verbose=False,
                    )
                    result = await crew.kickoff_async(inputs=script_input)
                    data = json.loads(result.raw)
                    return ScenePlan(**data)
                except (json.JSONDecodeError, ValueError) as e:
                    if attempt == self.max_retries:
                        raise RuntimeError(f"Failed after {self.max_retries} attempts.") from e
                    corrected = await self._retry_with_correction(script_input, str(e), attempt)
                    if corrected:
                        return corrected
        finally:
            litellm.api_base = original_base
            litellm.api_key = original_key
        raise RuntimeError("Unexpected failure.")

    async def _retry_with_correction(self, script_input: Dict, error_msg: str, attempt: int):
        segments_str = json.dumps(script_input.get("segments", []), indent=2)
        word_ts_str = json.dumps(script_input.get("word_timestamps", []), indent=2)
        assets_str = json.dumps(script_input.get("assets", []), indent=2)

        user_prompt = TASK_TEMPLATE.format(
            video_id=script_input.get("video_id", "unknown"),
            title=script_input.get("title", "Untitled"),
            total_duration_seconds=script_input.get("total_duration_seconds", 0.0),
            segments=segments_str,
            word_timestamps=word_ts_str,
            assets=assets_str,
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
            return ScenePlan(**data)
        except Exception:
            return None

    # ---------- Revision ----------
    def _build_revision_task(self) -> Task:
        return Task(
            description=REVISION_TEMPLATE,
            expected_output="A revised ScenePlan JSON after applying all revision instructions.",
            output_json=ScenePlan,
            agent=self.agent,
        )

    async def revise_scenes(
        self,
        script_input: Dict[str, Any],
        scene_plan: ScenePlan,
        quality_report: SceneQualityReport,
    ) -> ScenePlan:
        original_base = litellm.api_base
        original_key = litellm.api_key
        try:
            litellm.api_base = self.base_url
            litellm.api_key = self.api_key
            revision_task = self._build_revision_task()
            for attempt in range(1, self.max_retries + 1):
                try:
                    crew = Crew(
                        agents=[self.agent],
                        tasks=[revision_task],
                        verbose=False,
                    )
                    result = await crew.kickoff_async(
                        inputs={
                            "script": json.dumps(script_input, indent=2),
                            "scene_plan": json.dumps(scene_plan.model_dump(), indent=2),
                            "quality_report": json.dumps(quality_report.model_dump(), indent=2),
                        }
                    )
                    data = json.loads(result.raw)
                    return ScenePlan(**data)
                except (json.JSONDecodeError, ValueError) as e:
                    if attempt == self.max_retries:
                        raise RuntimeError(f"Revision failed after {self.max_retries} attempts.") from e
                    corrected = await self._retry_revision_correction(
                        script_input, scene_plan, quality_report, str(e), attempt
                    )
                    if corrected:
                        return corrected
        finally:
            litellm.api_base = original_base
            litellm.api_key = original_key
        raise RuntimeError("Unexpected revision failure.")

    async def _retry_revision_correction(
        self,
        script_input: Dict,
        scene_plan: ScenePlan,
        quality_report: SceneQualityReport,
        error_msg: str,
        attempt: int,
    ) -> Optional[ScenePlan]:
        user_prompt = REVISION_TEMPLATE.format(
            script=json.dumps(script_input, indent=2),
            scene_plan=json.dumps(scene_plan.model_dump(), indent=2),
            quality_report=json.dumps(quality_report.model_dump(), indent=2),
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
            return ScenePlan(**data)
        except Exception:
            return None