import os
import json
import logging
import asyncio
import re
from typing import Dict, Any, Optional

from crewai import Agent, Task, Crew, LLM
try:
    import litellm
except ImportError:
    litellm = None

from ..schemas.scene import ScenePlan, SceneQualityReport, Scene, VisualCue, AppearanceTrigger
from ..prompts.planner import (
    SYSTEM_PROMPT, TASK_TEMPLATE, RETRY_PROMPT, REVISION_TEMPLATE
)

logger = logging.getLogger(__name__)


def create_fallback_scene_plan(script_input: Dict[str, Any]) -> ScenePlan:
    segments = script_input.get("segments", [])
    scenes = []
    for idx, seg in enumerate(segments, 1):
        seg_id = str(seg.get("segment_id", idx))
        if not seg_id.startswith("seg_"):
            seg_id = f"seg_{seg_id}"
        narrator_text = seg.get("narrator_text", "")
        visual_cue_text = seg.get("visual_cue", f"Visual cue for {seg_id}")
        
        layout_hint = "title-card" if idx == 1 else ("outro-checklist" if idx == len(segments) else "content_a")
        template_name = "intro" if idx == 1 else ("outro" if idx == len(segments) else "content_a")

        scenes.append(
            Scene(
                scene_id=f"scene_{idx}",
                text=narrator_text,
                subtitle=narrator_text,
                hold_ms=6000,
                script_segment_ids=[seg_id],
                layout_hint=layout_hint,
                template=template_name,
                visual_cues=[
                    VisualCue(
                        cue_id=f"cue_{idx}",
                        description=visual_cue_text,
                        element_type="image",
                        asset_id=f"image_{idx}",
                        linked_segment_id=seg_id,
                        appearance_trigger=AppearanceTrigger(type="segment_start"),
                        preferred_region="center",
                        importance="primary",
                        trigger_time_seconds=0.2
                    )
                ]
            )
        )
    if not scenes:
        scenes = [
            Scene(
                scene_id="scene_1",
                text=script_input.get("title", "AI Educational Video"),
                subtitle=script_input.get("title", "AI Educational Video"),
                hold_ms=6000,
                script_segment_ids=["seg_1"],
                layout_hint="title-card",
                template="intro",
                visual_cues=[]
            )
        ]
    return ScenePlan(
        schema_version="1.0",
        video_id=script_input.get("video_id", "demo_job_id"),
        title=script_input.get("title", "AI Educational Video"),
        total_duration_seconds=float(script_input.get("estimated_total_duration", 30.0)),
        scenes=scenes
    )


def extract_scene_plan_from_raw(raw: str) -> Optional[ScenePlan]:
    if not raw:
        return None
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

    # 2. Extract embedded JSON in string
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
        self.base_url = base_url
        self.model_name = model_name
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.max_retries = max_retries

        # If primary API key is missing or placeholder, immediately try fallback config (e.g. Gemini 3.5 Flash Lite)
        if not self.api_key or "your_" in str(self.api_key):
            if self.fallback_config and self.fallback_config.get("api_key"):
                self.model_name = self.fallback_config["model_name"]
                self.api_key = self.fallback_config["api_key"]
                self.base_url = self.fallback_config.get("base_url")

        if litellm is not None and self.base_url:
            litellm.api_base = self.base_url
            litellm.api_key = self.api_key

        kwargs = {
            "model": self.model_name,
            "temperature": self.temperature,
        }
        if self.api_key:
            kwargs["api_key"] = self.api_key
        if self.base_url:
            kwargs["base_url"] = self.base_url
            kwargs["is_litellm"] = True

        self.llm = LLM(**kwargs)

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
        self.base_url = self.fallback_config.get("base_url")
        
        if litellm is not None and self.base_url:
            litellm.api_base = self.base_url
            litellm.api_key = self.api_key
        
        kwargs = {
            "model": self.model_name,
            "temperature": self.temperature,
        }
        if self.api_key:
            kwargs["api_key"] = self.api_key
        if self.base_url:
            kwargs["base_url"] = self.base_url
            kwargs["is_litellm"] = True

        self.llm = LLM(**kwargs)
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
        original_base = litellm.api_base if (litellm is not None and hasattr(litellm, "api_base")) else None
        original_key = litellm.api_key if (litellm is not None and hasattr(litellm, "api_key")) else None
        try:
            if litellm is not None and self.base_url:
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
                    parsed = extract_scene_plan_from_raw(result.raw)
                    if parsed:
                        return parsed
                    return ScenePlan(**json.loads(result.raw))
                except Exception as e:
                    logger.error(f"LLM API Error during planning (attempt {attempt}): {e}")
                    extracted = extract_scene_plan_from_raw(str(e))
                    if extracted:
                        logger.info("Successfully recovered valid ScenePlan from error payload!")
                        return extracted
                    if "rate_limit" in str(e).lower() or "429" in str(e):
                        logger.warning("Rate limit hit during planning. Sleeping 5s...")
                        await asyncio.sleep(5)
                        continue
                    if self._switch_to_fallback():
                        continue
                    if attempt == self.max_retries:
                        break
        finally:
            if litellm is not None and original_base:
                litellm.api_base = original_base
                litellm.api_key = original_key

        logger.warning("Returning deterministic fallback ScenePlan to keep pipeline operational.")
        return create_fallback_scene_plan(script_input)

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

        if litellm is None:
            return None

        try:
            response = await litellm.acompletion(
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
        original_base = litellm.api_base if (litellm is not None and hasattr(litellm, "api_base")) else None
        original_key = litellm.api_key if (litellm is not None and hasattr(litellm, "api_key")) else None
        try:
            if litellm is not None and self.base_url:
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
                    parsed = extract_scene_plan_from_raw(result.raw)
                    if parsed:
                        return parsed
                    return ScenePlan(**json.loads(result.raw))
                except Exception as e:
                    logger.error(f"LLM API Error during revision: {e}")
                    extracted = extract_scene_plan_from_raw(str(e))
                    if extracted:
                        logger.info("Successfully recovered valid ScenePlan from revision error payload!")
                        return extracted
                    if "rate_limit" in str(e).lower() or "429" in str(e):
                        await asyncio.sleep(5)
                        continue
                    if self._switch_to_fallback():
                        continue
                    if attempt == self.max_retries:
                        break
        finally:
            if litellm is not None and original_base:
                litellm.api_base = original_base
                litellm.api_key = original_key
        return scene_plan

    async def _retry_revision_correction(
        self,
        script_input: Dict,
        scene_plan: ScenePlan,
        quality_report: SceneQualityReport,
        error_msg: str,
        attempt: int,
    ) -> Optional[ScenePlan]:
        if litellm is None:
            return None

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
            response = await litellm.acompletion(
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