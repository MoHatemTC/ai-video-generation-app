import os
import json
import logging
import asyncio
from typing import Dict, Any, Optional

from crewai import Agent, Task, Crew, LLM
import litellm

from ..schemas.scene import ScenePlan, SceneQualityReport
from ..prompts.planner import (
    SYSTEM_PROMPT, TASK_TEMPLATE, RETRY_PROMPT, REVISION_TEMPLATE
)

logger = logging.getLogger(__name__)

import re

def extract_scene_plan_from_raw(raw: Any) -> Optional[ScenePlan]:
    if not raw:
        return None
    if isinstance(raw, ScenePlan):
        return raw
    if isinstance(raw, dict):
        try:
            return ScenePlan(**raw)
        except Exception:
            return None
    if hasattr(raw, "raw"):
        raw = getattr(raw, "raw")
    if not isinstance(raw, str):
        raw = str(raw)
    # 1. Direct json load try
    try:
        raw_clean = raw.strip()
        if raw_clean.startswith("```json"):
            raw_clean = raw_clean[7:]
        if raw_clean.endswith("```"):
            raw_clean = raw_clean[:-3]
        raw_clean = raw_clean.strip()
        data = json.loads(raw_clean)
        return ScenePlan(**data)
    except Exception:
        pass

    # 2. Extract embedded JSON in string (e.g. from <function=ScenePlan>... or error payload)
    try:
        match = re.search(r'\{.*\}', raw, re.DOTALL)
        if match:
            json_str = match.group(0)
            if '\"' in json_str:
                json_str = json_str.replace('\\"', '"')
            if '\\n' in json_str:
                json_str = json_str.replace('\\n', '\n')
            data = json.loads(json_str)
            return ScenePlan(**data)
    except Exception:
        pass
        
    return None

class ScenePlanner:
    def __init__(
        self,
        model_name: str = "kimi-k2.5",
        temperature: float = 0.2,
        max_tokens: int = 4096,
        api_key: Optional[str] = None,
        base_url: Optional[str] = "https://learner-os.sprints.ai/litellm",
        max_retries: int = 3,
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

    def _switch_to_fallback(self) -> bool:
        if not self.fallback_config:
            return False
            
        logger.warning("Primary LLM failed. Switching to fallback config...")
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
        self.fallback_config = None
        return True

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
                    parsed = extract_scene_plan_from_raw(result)
                    if parsed:
                        return parsed
                    raw_str = result.raw if hasattr(result, "raw") else str(result)
                    return ScenePlan(**json.loads(raw_str))
                except (json.JSONDecodeError, ValueError, litellm.BadRequestError) as e:
                    extracted = extract_scene_plan_from_raw(str(e))
                    if extracted:
                        logger.info("Successfully recovered valid ScenePlan from exception payload!")
                        return extracted
                    if attempt == self.max_retries:
                        raise RuntimeError(f"Failed after {self.max_retries} attempts.") from e
                    corrected = await self._retry_with_correction(script_input, str(e), attempt)
                    if corrected:
                        return corrected
                except Exception as e:
                    logger.error(f"LLM API Error during planning: {e}")
                    extracted = extract_scene_plan_from_raw(str(e))
                    if extracted:
                        logger.info("Successfully recovered valid ScenePlan from error payload!")
                        return extracted
                    if "rate_limit" in str(e).lower() or "429" in str(e):
                        logger.warning("Rate limit hit during planning. Sleeping for 15 seconds before retrying...")
                        await asyncio.sleep(15)
                        continue
                    if self._switch_to_fallback():
                        continue
                    if attempt == self.max_retries:
                        raise RuntimeError(f"Failed after {self.max_retries} attempts.") from e
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

        try:
            acompletion_func: Any = litellm.acompletion
            response = await acompletion_func(
                model=self.model_name,
                messages=messages,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                api_key=self.api_key,
                base_url=self.base_url,
                tools=[{
                    "type": "function",
                    "function": {
                        "name": "ScenePlan",
                        "description": "Schema for ScenePlan",
                        "parameters": ScenePlan.model_json_schema()
                    }
                }],
                tool_choice={"type": "function", "function": {"name": "ScenePlan"}}
            )
            tool_calls = response.choices[0].message.tool_calls
            if tool_calls and len(tool_calls) > 0:
                raw = tool_calls[0].function.arguments
            else:
                raw = response.choices[0].message.content or ""
                
            parsed = extract_scene_plan_from_raw(raw)
            if parsed:
                return parsed
            return ScenePlan(**json.loads(raw))
        except Exception as retry_err:
            extracted = extract_scene_plan_from_raw(str(retry_err))
            if extracted:
                logger.info("Successfully recovered valid ScenePlan from retry error payload!")
                return extracted
            logger.warning(f"Correction retry attempt {attempt} failed: {retry_err}")
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
                    parsed = extract_scene_plan_from_raw(result)
                    if parsed:
                        return parsed
                    raw_str = result.raw if hasattr(result, "raw") else str(result)
                    return ScenePlan(**json.loads(raw_str))
                except (json.JSONDecodeError, ValueError, litellm.BadRequestError) as e:
                    extracted = extract_scene_plan_from_raw(str(e))
                    if extracted:
                        logger.info("Successfully recovered valid ScenePlan from revision error payload!")
                        return extracted
                    if attempt == self.max_retries:
                        raise RuntimeError(f"Failed after {self.max_retries} attempts.") from e
                    corrected = await self._retry_revision_correction(
                        script_input, scene_plan, quality_report, str(e), attempt
                    )
                    if corrected:
                        return corrected
                except Exception as e:
                    logger.error(f"LLM API Error during revision: {e}")
                    extracted = extract_scene_plan_from_raw(str(e))
                    if extracted:
                        logger.info("Successfully recovered valid ScenePlan from revision error payload!")
                        return extracted
                    if "rate_limit" in str(e).lower() or "429" in str(e):
                        logger.warning("Rate limit hit during revision. Sleeping for 15 seconds before retrying...")
                        await asyncio.sleep(15)
                        continue
                    if self._switch_to_fallback():
                        continue
                    if attempt == self.max_retries:
                        raise RuntimeError(f"Revision failed after {self.max_retries} attempts.") from e
            raise RuntimeError(f"Failed after {self.max_retries} attempts.")
        finally:
            litellm.api_base = original_base
            litellm.api_key = original_key

    async def _retry_revision_correction(
        self,
        script_input: Dict[str, Any],
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
        try:
            acompletion_func: Any = litellm.acompletion
            response = await acompletion_func(
                model=self.model_name,
                messages=messages,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                api_key=self.api_key,
                base_url=self.base_url,
                tools=[{
                    "type": "function",
                    "function": {
                        "name": "ScenePlan",
                        "description": "Schema for ScenePlan",
                        "parameters": ScenePlan.model_json_schema()
                    }
                }],
                tool_choice={"type": "function", "function": {"name": "ScenePlan"}}
            )
            tool_calls = response.choices[0].message.tool_calls
            if tool_calls and len(tool_calls) > 0:
                raw = tool_calls[0].function.arguments
            else:
                raw = response.choices[0].message.content or ""
                
            parsed = extract_scene_plan_from_raw(raw)
            if parsed:
                return parsed
            return ScenePlan(**json.loads(raw))
        except Exception as retry_err:
            extracted = extract_scene_plan_from_raw(str(retry_err))
            if extracted:
                logger.info("Successfully recovered valid ScenePlan from revision retry payload!")
                return extracted
            logger.warning(f"Revision correction retry attempt {attempt} failed: {retry_err}")
            return None