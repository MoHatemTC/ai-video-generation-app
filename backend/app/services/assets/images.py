import os
import uuid
import logging
import json
import asyncio
import concurrent.futures
import urllib.parse
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from crewai import Agent, Task, Crew
from backend.app.schemas.asset import AssetItem

# Pydantic V2 Migration warnings are expected from CrewAI and can be ignored for now.
logger = logging.getLogger(__name__)

# Solid blue for all icons (brand logos use their own colors)
ICON_COLOR_HEX = "3b82f6"

# Iconify icon catalog that the CrewAI agent selects from
ICONIFY_ICON_CATALOG = """
Available Iconify vector icon identifiers:
- lucide/brain-circuit  → AI, neural networks, machine learning, intelligence, quantum
- lucide/database       → databases, data storage, SQL, data management
- lucide/server         → servers, cloud, hosting, backend, infrastructure
- lucide/shield-check   → security, protection, encryption, authentication
- lucide/sprout         → nature, plants, growth, biology, photosynthesis, solar
- lucide/lightbulb      → ideas, concepts, innovation, creativity, metaphors
- lucide/cog            → processes, machines, gears, automation, settings
- lucide/laptop         → computers, screens, devices, technology
- lucide/award          → achievements, trophies, stars, badges, foundations
- lucide/code-2         → programming, coding, development, software
- lucide/sparkles       → magic, special effects, highlights, general
- lucide/globe          → world, internet, geography, global, earth
- lucide/zap            → energy, electricity, power, speed, lightning
- lucide/layers         → architecture, stacks, layers, levels
- lucide/git-branch     → version control, branches, workflow, git
- lucide/terminal       → command line, CLI, shell, console
- lucide/network        → networking, connections, mesh, topology
- lucide/cpu            → processors, chips, hardware, computing
- lucide/lock           → security, locks, access control, passwords
- lucide/book-open      → education, learning, documentation, reading
- lucide/bar-chart-3    → analytics, statistics, charts, metrics
- lucide/workflow       → pipelines, flows, processes, automation
- lucide/rocket         → launch, deployment, startup, speed
- lucide/search         → search, discovery, exploration, find
- lucide/users          → people, teams, collaboration, community
- lucide/message-square → chat, messaging, communication, conversations
- lucide/file-text      → files, documents, text, content
- lucide/image          → images, photos, media, visuals
- lucide/music          → audio, music, sound, podcast
- lucide/video          → video, streaming, media, recording
- lucide/cloud-upload   → cloud upload, deployment, publishing
- lucide/link           → links, URLs, connections, sharing
- lucide/monitor        → monitors, displays, screens, dashboards
- lucide/sliders-horizontal → sliders, controls, settings, adjustments
- lucide/puzzle         → puzzles, integration, components, assembly
- logos/docker-icon     → Docker, containers (brand logo, no color override)
- logos/python          → Python programming (brand logo, no color override)
- logos/react           → React framework (brand logo, no color override)
- logos/langchain-icon  → LangChain (brand logo, no color override)
"""

# All valid icon IDs the agent can return — used for validation
VALID_ICON_IDS = {
    "lucide/brain-circuit", "lucide/database", "lucide/server", "lucide/shield-check",
    "lucide/sprout", "lucide/lightbulb", "lucide/cog", "lucide/laptop", "lucide/award",
    "lucide/code-2", "lucide/sparkles", "lucide/globe", "lucide/zap", "lucide/layers",
    "lucide/git-branch", "lucide/terminal", "lucide/network", "lucide/cpu", "lucide/lock",
    "lucide/book-open", "lucide/bar-chart-3", "lucide/workflow", "lucide/rocket",
    "lucide/search", "lucide/users", "lucide/message-square", "lucide/file-text",
    "lucide/image", "lucide/music", "lucide/video", "lucide/cloud-upload", "lucide/link",
    "lucide/monitor", "lucide/sliders-horizontal", "lucide/puzzle",
    "logos/docker-icon", "logos/python", "logos/react", "logos/langchain-icon",
}


def _heuristic_svg_fallback(desc: str) -> str:
    """Keyword-based fallback vector SVG icon mapping. Always uses solid blue."""
    d = desc.lower()
    color_param = f"?color=%23{ICON_COLOR_HEX}"
    if "docker" in d:
        return "https://api.iconify.design/logos/docker-icon.svg"
    elif "langchain" in d:
        return "https://api.iconify.design/logos/langchain-icon.svg"
    elif "python" in d:
        return "https://api.iconify.design/logos/python.svg"
    elif "react" in d:
        return "https://api.iconify.design/logos/react.svg"
    elif "brain" in d or "ai" in d or "quantum" in d or "mind" in d or "intelligence" in d:
        return f"https://api.iconify.design/lucide/brain-circuit.svg{color_param}"
    elif "database" in d or "store" in d or "sql" in d or "data" in d:
        return f"https://api.iconify.design/lucide/database.svg{color_param}"
    elif "server" in d or "cloud" in d or "host" in d:
        return f"https://api.iconify.design/lucide/server.svg{color_param}"
    elif "shield" in d or "security" in d or "lock" in d or "padlock" in d:
        return f"https://api.iconify.design/lucide/shield-check.svg{color_param}"
    elif "leaf" in d or "plant" in d or "photosynthesis" in d or "sun" in d or "solar" in d:
        return f"https://api.iconify.design/lucide/sprout.svg{color_param}"
    elif "lightbulb" in d or "idea" in d or "concept" in d or "metaphor" in d:
        return f"https://api.iconify.design/lucide/lightbulb.svg{color_param}"
    elif "gear" in d or "wheel" in d or "process" in d or "machine" in d:
        return f"https://api.iconify.design/lucide/cog.svg{color_param}"
    elif "laptop" in d or "computer" in d or "screen" in d or "monitor" in d:
        return f"https://api.iconify.design/lucide/laptop.svg{color_param}"
    elif "key" in d or "badge" in d or "trophy" in d or "star" in d or "foundation" in d:
        return f"https://api.iconify.design/lucide/award.svg{color_param}"
    elif "code" in d or "program" in d or "developer" in d:
        return f"https://api.iconify.design/lucide/code-2.svg{color_param}"
    elif "upload" in d or "deploy" in d or "publish" in d:
        return f"https://api.iconify.design/lucide/cloud-upload.svg{color_param}"
    elif "link" in d or "url" in d or "share" in d:
        return f"https://api.iconify.design/lucide/link.svg{color_param}"
    elif "slider" in d or "control" in d:
        return f"https://api.iconify.design/lucide/sliders-horizontal.svg{color_param}"
    elif "puzzle" in d or "assembl" in d or "component" in d:
        return f"https://api.iconify.design/lucide/puzzle.svg{color_param}"
    elif "chart" in d or "graph" in d or "analytic" in d or "statistic" in d:
        return f"https://api.iconify.design/lucide/bar-chart-3.svg{color_param}"
    elif "user" in d or "people" in d or "team" in d or "person" in d:
        return f"https://api.iconify.design/lucide/users.svg{color_param}"
    elif "rocket" in d or "launch" in d:
        return f"https://api.iconify.design/lucide/rocket.svg{color_param}"
    elif "book" in d or "learn" in d or "education" in d or "read" in d:
        return f"https://api.iconify.design/lucide/book-open.svg{color_param}"
    elif "globe" in d or "world" in d or "earth" in d or "internet" in d:
        return f"https://api.iconify.design/lucide/globe.svg{color_param}"
    else:
        return f"https://api.iconify.design/lucide/sparkles.svg{color_param}"


def _build_iconify_url(icon_id: str) -> str:
    """Build a full Iconify CDN URL from an icon identifier. Always solid blue."""
    icon_id = icon_id.strip().strip("'\"")
    # Brand logos have built-in colors — no color override
    if icon_id.startswith("logos/"):
        return f"https://api.iconify.design/{icon_id}.svg"
    color_param = f"?color=%23{ICON_COLOR_HEX}"
    return f"https://api.iconify.design/{icon_id}.svg{color_param}"


def _extract_icon_id(raw_output: str) -> Optional[str]:
    """Extract a valid Iconify icon ID from CrewAI agent output text."""
    raw = raw_output.strip()
    # Try exact match first
    if raw in VALID_ICON_IDS:
        return raw
    # Search for any valid ID within the output
    for icon_id in VALID_ICON_IDS:
        if icon_id in raw:
            return icon_id
    return None


def _extract_multiple_icon_ids(raw_output: str, expected_count: int) -> List[Optional[str]]:
    """
    Extract multiple icon IDs from a numbered agent response.
    Expected format: '1. lucide/laptop\n2. lucide/code-2'
    Returns a list of length expected_count (None for any that couldn't be parsed).
    """
    lines = [line.strip() for line in raw_output.strip().splitlines() if line.strip()]
    results: List[Optional[str]] = []
    used_ids: set = set()

    for line in lines:
        # Strip numbering like "1.", "2)", "1:", etc.
        cleaned = line.lstrip("0123456789.-:) ").strip()
        icon_id = _extract_icon_id(cleaned)
        if icon_id and icon_id not in used_ids:
            results.append(icon_id)
            used_ids.add(icon_id)
        elif icon_id and icon_id in used_ids:
            # Agent repeated an icon — try to find another one in the line
            alt_id = None
            for vid in VALID_ICON_IDS:
                if vid in cleaned and vid != icon_id and vid not in used_ids:
                    alt_id = vid
                    break
            results.append(alt_id)
            if alt_id:
                used_ids.add(alt_id)

    # Pad with None if agent returned fewer than expected
    while len(results) < expected_count:
        results.append(None)

    return results[:expected_count]


def _get_refinement_llm():
    """Build a valid CrewAI LLM instance matching the application configuration."""
    api_key = os.getenv("LITELLM_API_KEY") or os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    litellm_base = os.getenv("LITELLM_BASE_URL", "https://learner-os.sprints.ai/litellm/v1")
    if api_key and not api_key.startswith("your_") and "key_here" not in api_key:
        os.environ["OPENAI_API_KEY"] = api_key
        os.environ["OPENAI_API_BASE"] = litellm_base
        from backend.app.config.model_config import format_model_for_litellm_proxy
        raw_model = os.getenv("MODEL_NAME", "gemini/gemini-flash-latest")
        model_name = format_model_for_litellm_proxy(raw_model)
        try:
            from crewai import LLM
            return LLM(model=model_name, api_key=api_key, base_url=litellm_base, temperature=0.2)
        except Exception:
            pass

    openrouter_key = os.getenv("OPENROUTER_API_KEY")
    if openrouter_key and not openrouter_key.startswith("your_"):
        openrouter_base = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
        openrouter_model = os.getenv("OPENROUTER_MODEL", "openrouter/free")
        try:
            from crewai import LLM
            return LLM(model=openrouter_model, api_key=openrouter_key, base_url=openrouter_base, temperature=0.2)
        except Exception:
            pass
    return None


class AssetService:
    def __init__(self):
        self.local_storage_db = "data/supabase_asset_metadata.json"
        os.makedirs(os.path.dirname(self.local_storage_db), exist_ok=True)
        if not os.path.exists(self.local_storage_db):
            with open(self.local_storage_db, "w", encoding="utf-8") as f:
                json.dump([], f)

    def register_asset_in_storage(self, asset: AssetItem, video_id: str) -> str:
        try:
            with open(self.local_storage_db, "r", encoding="utf-8") as f:
                db = json.load(f)
            if not isinstance(db, list):
                db = []
        except Exception:
            db = []

        asset_entry = {
            "video_id": video_id,
            "asset_id": asset.asset_id,
            "scene_id": asset.scene_reference,
            "cue_id": asset.cue_reference,
            "element": asset.element,
            "prompt": asset.prompt,
            "url": asset.url,
            "type": asset.asset_type,
            "source": asset.source,
            "license": asset.asset_license,
            "registered_at": datetime.now(timezone.utc).isoformat()
        }
        db.append(asset_entry)

        with open(self.local_storage_db, "w", encoding="utf-8") as f:
            json.dump(db, f, indent=4, ensure_ascii=False)
        return asset.url

    async def resolve_scene_cues(
        self, cue_batch: List[Dict[str, str]], scene_id: str,
        video_id: str, supabase_client: Any = None
    ) -> List[AssetItem]:
        """
        Use CrewAI agent to select the best Iconify SVG icons for ALL visual cues
        in a scene at once. This ensures the agent picks distinct, complementary icons.
        
        cue_batch: list of dicts with keys 'cue_id', 'asset_id', 'description', 'element'
        """
        num_cues = len(cue_batch)
        if num_cues == 0:
            return []

        resolved_assets: List[AssetItem] = []
        agent_icon_ids: List[Optional[str]] = [None] * num_cues

        llm = _get_refinement_llm()
        if llm:
            try:
                # Build a numbered list of cues for the agent
                cue_list_text = "\n".join(
                    f"{i+1}. \"{cue['description']}\""
                    for i, cue in enumerate(cue_batch)
                )

                if num_cues == 1:
                    task_instruction = (
                        f"Given this visual cue for scene '{scene_id}':\n"
                        f"1. \"{cue_batch[0]['description']}\"\n\n"
                        f"Select the single best matching icon from this catalog:\n{ICONIFY_ICON_CATALOG}\n\n"
                        "Respond with ONLY the icon identifier (e.g. 'lucide/brain-circuit'). "
                        "No explanation, no extra text."
                    )
                    expected_output = "A single Iconify icon identifier string like 'lucide/brain-circuit'."
                else:
                    task_instruction = (
                        f"This scene '{scene_id}' has {num_cues} visual elements that will appear together.\n"
                        f"The visual cues are:\n{cue_list_text}\n\n"
                        f"From this catalog, select {num_cues} DIFFERENT icons — one per cue, in order.\n"
                        f"Each icon must be DISTINCT (no duplicates within the same scene).\n"
                        f"{ICONIFY_ICON_CATALOG}\n\n"
                        f"Respond with EXACTLY {num_cues} lines, numbered 1 to {num_cues}, each containing "
                        "only the icon identifier. Example:\n"
                        "1. lucide/laptop\n"
                        "2. lucide/code-2\n"
                        "No explanation, no extra text."
                    )
                    expected_output = (
                        f"Exactly {num_cues} numbered lines, each with one Iconify icon identifier. "
                        "Example: '1. lucide/laptop\\n2. lucide/code-2'"
                    )

                svg_selector = Agent(
                    role="Visual Icon Design Director",
                    goal=(
                        "Select the most semantically appropriate and visually distinct "
                        "vector icons for educational video scenes."
                    ),
                    backstory=(
                        "You are the visual design director at Sprints Video Studio. "
                        "Your job is to pick the best icons from the Iconify catalog "
                        "that visually represent concepts for educational videos. "
                        "When a scene has multiple visuals, you MUST pick DIFFERENT icons "
                        "so the scene looks varied and informative."
                    ),
                    verbose=False,
                    allow_delegation=False,
                    llm=llm
                )

                selection_task = Task(
                    description=task_instruction,
                    expected_output=expected_output,
                    agent=svg_selector
                )

                my_crew = Crew(agents=[svg_selector], tasks=[selection_task])

                with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                    future = executor.submit(my_crew.kickoff)
                    result = future.result(timeout=45)

                raw_output = str(getattr(result, "raw", result)).strip()

                if num_cues == 1:
                    icon_id = _extract_icon_id(raw_output)
                    agent_icon_ids = [icon_id]
                    if icon_id:
                        logger.info(f"[SVG AGENT] Scene '{scene_id}': selected '{icon_id}' for 1 cue")
                    else:
                        logger.warning(
                            f"[SVG AGENT] Scene '{scene_id}': could not parse icon from: '{raw_output}'"
                        )
                else:
                    agent_icon_ids = _extract_multiple_icon_ids(raw_output, num_cues)
                    parsed_count = sum(1 for x in agent_icon_ids if x is not None)
                    logger.info(
                        f"[SVG AGENT] Scene '{scene_id}': parsed {parsed_count}/{num_cues} icons "
                        f"from agent output"
                    )

            except Exception as e:
                logger.warning(
                    f"[SVG AGENT] Scene '{scene_id}': agent failed ({e}). "
                    "All cues will use heuristic fallback."
                )

        # Build AssetItems — use agent result if available, else heuristic fallback
        for i, cue in enumerate(cue_batch):
            icon_id = agent_icon_ids[i] if i < len(agent_icon_ids) else None

            if icon_id:
                svg_url = _build_iconify_url(icon_id)
                icon_source = "iconify"
            else:
                svg_url = _heuristic_svg_fallback(cue["description"])
                icon_source = "iconify-heuristic"
                logger.info(
                    f"[SVG FALLBACK] Scene '{scene_id}', cue '{cue['cue_id']}': "
                    f"heuristic → {svg_url}"
                )

            asset = AssetItem(
                asset_id=cue["asset_id"],
                scene_reference=scene_id,
                scene_id=scene_id,
                cue_reference=cue["cue_id"],
                cue_id=cue["cue_id"],
                asset_type="svg",
                url=svg_url,
                prompt=cue["description"],
                description=cue["description"],
                source=icon_source,
                asset_license="open-source",
                element=cue["element"]
            )

            self.register_asset_in_storage(asset, video_id)
            resolved_assets.append(asset)

        return resolved_assets


async def process_scene_elements(scene_data: Dict[str, Any], supabase_client: Any = None) -> Dict[str, Any]:
    """
    Stage 5 Asset Resolution Engine.
    Uses CrewAI agent to select Iconify vector SVG icons for each scene's visual cues.
    The agent sees ALL cues per scene together to pick distinct, complementary icons.
    Falls back to heuristic keyword matching if the agent is unavailable.
    All icons use solid blue (#3b82f6).
    """
    video_id = scene_data.get("video_id", "default_video_id")
    scenes = scene_data.get("scenes", [])
    service = AssetService()
    asset_index = 1

    # Semaphore to avoid bursting too many concurrent LLM requests (HTTP 429 prevention)
    semaphore = asyncio.Semaphore(2)

    async def sem_resolve_scene(cue_batch: List[Dict[str, str]], scene_id: str):
        async with semaphore:
            return await service.resolve_scene_cues(
                cue_batch=cue_batch,
                scene_id=scene_id,
                video_id=video_id,
                supabase_client=supabase_client
            )

    # Collect cue batches per scene
    scene_tasks = []
    for idx, scene in enumerate(scenes):
        scene_id = scene.get("scene_id", f"scene_{idx+1}")
        cues_or_elements = scene.get("visual_cues") or scene.get("visual_elements") or []

        cue_batch: List[Dict[str, str]] = []
        for element in cues_or_elements:
            element_type = element.get("element_type")
            if element_type != "text" or "asset_id" in element:
                fallback_id = f"image_{asset_index}"
                asset_id = element.get("asset_id") or fallback_id

                cue_batch.append({
                    "cue_id": element.get("cue_id", f"cue_{asset_index}"),
                    "asset_id": asset_id,
                    "description": element.get("description", element.get("text", "")),
                    "element": element.get("content", element.get("description", ""))
                })
                asset_index += 1

        if cue_batch:
            scene_tasks.append(sem_resolve_scene(cue_batch, scene_id))

    if not scene_tasks:
        return {
            "video_id": video_id,
            "assets": []
        }

    # Each task returns a list of AssetItems for that scene
    gathered_scene_results = await asyncio.gather(*scene_tasks)

    resolved_assets = []
    asset_map = {}
    for scene_assets in gathered_scene_results:
        for asset in scene_assets:
            resolved_assets.append({
                "asset_id": asset.asset_id,
                "scene_id": asset.scene_reference,
                "cue_id": asset.cue_reference,
                "url": asset.url,
                "type": asset.asset_type,
                "license": asset.asset_license,
                "source": asset.source
            })
            asset_map[asset.asset_id] = asset.url

    return {
        "video_id": video_id,
        "assets": resolved_assets,
        **asset_map
    }