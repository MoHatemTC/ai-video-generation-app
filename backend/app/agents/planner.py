# backend/app/agents/planner.py
import os
import json
import logging
from typing import Dict, Any, Optional

from crewai import Agent, Task, Crew
from crewai import LLM

from ..schemas.scene import ScenePlan
from ..prompts.planner import SYSTEM_PROMPT, TASK_DESCRIPTION, RETRY_PROMPT

logger = logging.getLogger(__name__)

class ScenePlanner:
    """
    Scene Planner Agent that converts a script into a structured ScenePlan.

    Uses CrewAI with a Groq LLM (configurable) and includes retry logic with
    error feedback for robust parsing.
    """

    def __init__(
        self,
        model_name: str = "groq/llama-3.3-70b-versatile",
        temperature: float = 0.2,
        max_tokens: int = 4096,
        api_key: Optional[str] = None,
        max_retries: int = 3,
    ):
        self.model_name = model_name
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.api_key = api_key or os.getenv("GROQ_API_KEY")
        if not self.api_key:
            raise ValueError("GROQ_API_KEY must be set in environment or passed.")

        self.llm = LLM(
            model=model_name,
            api_key=self.api_key,
            temperature=temperature,
            is_litellm=True,
        )
        self.max_retries = max_retries

        # Create the CrewAI agent with the system prompt
        self.agent = Agent(
            role="Scene Planning Agent",
            goal="Convert educational script into storyboard with synchronised visuals.",
            backstory=SYSTEM_PROMPT,
            llm=self.llm,
            verbose=False,  # set to True for debugging
        )

    def _build_task(self, script_input: Dict[str, Any]) -> Task:
        """Build a CrewAI Task with the given input."""
        # The Task description uses the script input as context.
        # We inject the input into the description using f-string formatting.
        # CrewAI passes inputs via the `inputs` dict; we'll use that.
        task = Task(
            description=TASK_DESCRIPTION,
            expected_output="A JSON Scene Plan describing scenes, layouts and synchronised visual cues.",
            output_json=ScenePlan,
            agent=self.agent,
        )
        return task

    def plan_scenes(self, script_input: Dict[str, Any]) -> ScenePlan:
        """
        Execute the Scene Planner on the given script input.

        Args:
            script_input: dict containing:
                - video_id (str)
                - title (str)
                - total_duration_seconds (float)
                - segments (list of dict with id, text, visual_cue)
                - word_timestamps (list of dict with word_id, segment_id, word)
                - assets (list of dict with asset_id, element_type, description)

        Returns:
            ScenePlan validated against the schema.

        Raises:
            RuntimeError: if all retries fail.
        """
        for attempt in range(1, self.max_retries + 1):
            try:
                # Build a fresh Crew and Task for each attempt
                crew = Crew(
                    agents=[self.agent],
                    tasks=[self._build_task(script_input)],
                    verbose=False,
                )
                # Run the crew synchronously (or async if needed)
                result = crew.kickoff(inputs=script_input)

                # CrewAI returns a TaskOutput with .raw or .json_dict
                raw_output = result.raw
                # Parse JSON and validate with Pydantic
                data = json.loads(raw_output)
                scene_plan = ScenePlan(**data)
                logger.info(f"Valid ScenePlan generated on attempt {attempt}")
                return scene_plan

            except (json.JSONDecodeError, ValueError) as e:
                logger.warning(f"Attempt {attempt} failed: {e}")
                if attempt == self.max_retries:
                    logger.error("Max retries exceeded.")
                    raise RuntimeError(f"Failed to generate valid ScenePlan after {self.max_retries} attempts.") from e

                # For retry, we could modify the prompt to include the error.
                # Here we re-use the same agent; we could add a follow-up correction.
                # For simplicity we just retry with the same prompt, but a better approach
                # would be to feed the error back to the LLM.
                # We'll implement a simple correction by updating the task description.
                # However, CrewAI doesn't easily allow dynamic task updates.
                # Alternative: use direct LLM call with retry prompt.
                # Since CrewAI may not support dynamic task changes easily,
                # we fall back to a direct LLM call with the retry prompt.
                self._retry_with_correction(script_input, str(e), attempt)

        raise RuntimeError("Unexpected failure in plan_scenes.")

    def _retry_with_correction(self, script_input: Dict, error_msg: str, attempt: int):
        """
        Direct LLM call with error feedback to correct the output.
        This is a fallback when CrewAI's structured output fails.
        """
        # Build a conversation with the error
        user_prompt = f"""
        {TASK_DESCRIPTION}

        Input data:
        {json.dumps(script_input, indent=2)}

        {RETRY_PROMPT.format(error=error_msg)}
        """
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ]
        # Use litellm directly
        import litellm
        response = litellm.completion(
            model=self.model_name,
            messages=messages,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
            api_key=self.api_key,
        )
        raw = response.choices[0].message.content
        # Strip any markdown code fences
        raw = raw.strip()
        if raw.startswith("```json"):
            raw = raw[7:]
        if raw.endswith("```"):
            raw = raw[:-3]
        raw = raw.strip()
        try:
            data = json.loads(raw)
            return ScenePlan(**data)
        except Exception as e:
            logger.warning(f"Retry attempt {attempt} correction failed: {e}")
            raise