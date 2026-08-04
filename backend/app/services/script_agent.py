import os
import json
import logging
import re
from openai import AsyncOpenAI
from backend.app.schemas.script import VideoScriptBlueprint, ScriptSegment

logger = logging.getLogger(__name__)


def _generate_dynamic_fallback(user_prompt: str) -> VideoScriptBlueprint:
    """
    Generates a topic-generic 12-scene beginner script blueprint (~90 seconds, <30 words per scene)
    with real-world analogies for ANY arbitrary user topic if the primary LLM call fails.
    """
    topic_clean = user_prompt.strip().title() if user_prompt else "The Topic"

    segments = [
        ScriptSegment(
            segment_id=1,
            narrator_text=f"Welcome! Ever wondered how {topic_clean} actually works under the hood?",
            visual_cue=f"A flat vector illustration of a glowing question mark over a {topic_clean} icon"
        ),
        ScriptSegment(
            segment_id=2,
            narrator_text=f"Let's break down {topic_clean} using a simple real-world metaphor.",
            visual_cue="A flat vector illustration of a lightbulb illuminating a blueprint"
        ),
        ScriptSegment(
            segment_id=3,
            narrator_text=f"Think of {topic_clean} like building a house with standardized modular bricks.",
            visual_cue="A flat vector icon of colorful modular building blocks snapping together"
        ),
        ScriptSegment(
            segment_id=4,
            narrator_text="Each block has a single clear job, working in harmony with all the others.",
            visual_cue="A flat vector diagram showing interconnected gear wheels in motion"
        ),
        ScriptSegment(
            segment_id=5,
            narrator_text=f"Without this structure, managing {topic_clean} would be messy and complex.",
            visual_cue="A flat vector illustration of tangled cables and warning signs"
        ),
        ScriptSegment(
            segment_id=6,
            narrator_text="By standardizing the process, we eliminate confusion and boost efficiency.",
            visual_cue="A flat vector checklist with green checkmarks"
        ),
        ScriptSegment(
            segment_id=7,
            narrator_text=f"In practical real-world applications, {topic_clean} solves everyday friction.",
            visual_cue="A flat vector illustration of a person operating a modern laptop"
        ),
        ScriptSegment(
            segment_id=8,
            narrator_text="It allows teams to work faster, safer, and with complete reliability.",
            visual_cue="A flat vector shield with a padlock and speed indicator"
        ),
        ScriptSegment(
            segment_id=9,
            narrator_text=f"Here is key tip number one when exploring {topic_clean}.",
            visual_cue="A flat vector icon of a key pointing to a glowing badge"
        ),
        ScriptSegment(
            segment_id=10,
            narrator_text="Always focus on the core foundation before diving into advanced details.",
            visual_cue="A flat vector illustration of a solid stone foundation block"
        ),
        ScriptSegment(
            segment_id=11,
            narrator_text=f"Now you understand the basic mechanics powering {topic_clean}!",
            visual_cue="A flat vector icon of a star trophy celebrating progress"
        ),
        ScriptSegment(
            segment_id=12,
            narrator_text="Thanks for watching! Keep exploring and building your knowledge.",
            visual_cue="A flat vector outro badge with summary notes"
        ),
    ]

    total_words = sum(len(s.narrator_text.split()) for s in segments)
    estimated_duration = max(90, int(total_words / 2.3))

    return VideoScriptBlueprint(
        title=f"Understanding {topic_clean}: A Beginner's Guide",
        target_audience="Absolute Beginners (Zero Prior Knowledge)",
        estimated_total_duration=estimated_duration,
        segments=segments
    )


async def generate_script(user_prompt: str) -> VideoScriptBlueprint:
    litellm_key = os.getenv("LITELLM_API_KEY")
    litellm_url = os.getenv("LITELLM_BASE_URL")
    gemini_key = os.getenv("GEMINI_API_KEY")
    openrouter_key = os.getenv("OPENROUTER_API_KEY")

    api_key = None
    base_url = None
    model_name = "gemini/gemini-pro-latest"

    # Determine provider — prioritize LiteLLM proxy (Sprints company API)
    if litellm_url and "your_" not in litellm_url and litellm_key and "your_" not in litellm_key:
        api_key = litellm_key
        base_url = litellm_url
        model_name = "gemini/gemini-pro-latest"
    elif gemini_key and "your_" not in gemini_key:
        api_key = gemini_key
        base_url = "https://generativelanguage.googleapis.com/v1beta/openai/"
        model_name = "gemini-3.5-flash-lite"
    elif openrouter_key and "your_" not in openrouter_key:
        api_key = openrouter_key
        base_url = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
        model_name = os.getenv("OPENROUTER_MODEL", "openrouter/free")

    if api_key and base_url:
        try:
            client = AsyncOpenAI(
                api_key=api_key.strip(),
                base_url=base_url.strip()
            )

            system_prompt = """You are a world-class science communicator and master educational scriptwriter (inspired by Richard Feynman).
Your core mission is to take any educational or technical topic provided by the user and turn it into a highly engaging, structured, beginner-friendly video script.

STRICT WRITING RULES & PEDAGOGY:
1. TARGET AUDIENCE:
   - Absolute Beginners with ZERO prior knowledge. Use warm, encouraging, jargon-free language.
   - If a technical term is necessary, explain it immediately in plain English.

2. METAPHOR-FIRST EXPLANATIONS:
   - ALWAYS introduce core concepts using a clear, intuitive, real-world everyday metaphor (e.g., shipping containers, factory assembly lines, public libraries, postal mail).
   - Follow up the metaphor with a concrete, practical, real-world application or technical example.

3. SVG-OPTIMIZED VISUAL CUES (CRITICAL FOR DOWNSTREAM RENDER ENGINE):
   - Every `visual_cue` MUST be a concrete, literal, noun-based description suitable for flat vector SVG icon/illustration selection.
   - ALWAYS specify flat vector objects, icons, or specific physical items (e.g., 'A flat vector illustration of a padlock on a server rack', 'A flat vector diagram of three connected computers').
   - NEVER use abstract phrases like 'A representation of security' or 'Visualizing data flow'.

4. STRICT SCENE PACING & GRANULARITY:
   - Divide the script into between 12 and 30 distinct visual scenes.
   - MANDATORY RULE: NO single segment's `narrator_text` may exceed 30 words (~7-10 seconds of speech per scene). This ensures rapid visual movement and keeps viewers engaged.

5. DURATION CALIBRATION (1.5 to 4.0 MINUTES):
   - Auto-determine the total video duration based on topic complexity:
     • Minimum: 90 seconds (~220 total words, ~12 scenes) for simple topics.
     • Average Target: 150 seconds (~360 total words, ~18-22 scenes) for standard topics.
     • Maximum: 240 seconds (~550 total words, ~25-30 scenes) for multi-faceted topics.
   - Set `estimated_total_duration` to the estimated total duration in seconds.
"""

            response = await client.beta.chat.completions.parse(
                model=model_name,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Create an educational video script about: {user_prompt}"}
                ],
                response_format=VideoScriptBlueprint,
            )
            parsed = response.choices[0].message.parsed
            if parsed and len(parsed.segments) >= 5:
                return parsed
        except Exception as e:
            logger.warning(f"LLM API call failed ({e}). Falling back to dynamic blueprint template.")

    # Fallback template if API key is missing, invalid, or endpoint connection fails
    return _generate_dynamic_fallback(user_prompt)
