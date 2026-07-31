import os
import json
from pathlib import Path
from dotenv import load_dotenv

THIS_DIR = Path(__file__).resolve().parent
load_dotenv(THIS_DIR / ".env")

try:
    from crewai import Agent, Task, Crew, Process, LLM
    HAS_CREWAI = True
except ImportError:
    HAS_CREWAI = False


def normalize_model_name(raw_name: str) -> str:
    if not raw_name:
        return "gemini/gemini-3.5-flash-lite"
    clean = raw_name.strip()
    if clean.startswith("gemini/") or clean.startswith("google/"):
        return clean
    return f"gemini/{clean.lower().replace(' ', '-')}"


def generate_assets_with_crewai(scene_plan_dict: dict) -> dict:
    """
    Returns a dict mapping asset_id -> Iconify API URL string.
    """
    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not api_key or not HAS_CREWAI:
        print("[NOTICE] CrewAI or API key not found. Skipping SVG asset generation.")
        return {}

    raw_model = os.getenv("MODEL_NAME", "gemini/gemini-3.5-flash-lite")
    model_name = normalize_model_name(raw_model)
    title = scene_plan_dict.get("title", "Unknown Topic")
    
    # Extract unique assets needed
    assets_to_generate = {}
    for scene in scene_plan_dict.get("scenes", []):
        for cue in scene.get("visual_cues", []):
            aid = cue.get("asset_id")
            if aid:
                assets_to_generate[aid] = cue.get("description", aid)
                
    if not assets_to_generate:
        return {}
        
    llm = LLM(model=model_name, api_key=api_key, temperature=0.2)
    illustrator = Agent(
        role="Senior Iconographer & API Specialist",
        goal="Determine the most appropriate HTTPS icon URL (e.g. Iconify API) for each visual cue requested in the video.",
        backstory=(
            "You are a master at selecting the perfect vector icons for technical explainer videos. "
            "You map abstract concepts to real, professional icons using the Iconify API (https://api.iconify.design/)."
        ),
        verbose=False,
        allow_delegation=False,
        llm=llm
    )

    asset_generation_task = Task(
        description=f"""
        You are provided with a list of visual cues for an explainer video on the topic: '{title}'.

        Your job is to read the 'description' of each visual cue, and find the most relevant icon from the Iconify open source icon sets (like 'lucide', 'mdi', 'carbon', 'logos').

        For each unique 'asset_id', you must return a valid Iconify API URL.
        Format: https://api.iconify.design/{{collection}}/{{icon}}.svg?color=%23{{hex_color}}
        
        Example collections:
        - 'logos' (for brand logos, e.g. logos:docker-icon -> https://api.iconify.design/logos/docker-icon.svg)
        - 'lucide' (for modern line icons, e.g. lucide:server -> https://api.iconify.design/lucide/server.svg?color=%233b82f6)
        - 'mdi' (for material design icons)

        Required Assets to map:
        {json.dumps(assets_to_generate, indent=2)}

        Return a JSON dictionary mapping the 'asset_id' to the generated Iconify URL.
        """,
        expected_output='''
        {
          "asset-langchain-logo": "https://api.iconify.design/logos/langchain.svg",
          "asset-llm-icon": "https://api.iconify.design/lucide/cpu.svg?color=%233b82f6",
          "asset-risk-beams": "https://api.iconify.design/mdi/alert-circle-outline.svg?color=%23ef4444"
        }
        ''',
        agent=illustrator
    )
    
    crew = Crew(agents=[illustrator], tasks=[asset_generation_task], process=Process.sequential)
    print(f"[ASSET AGENT] Generating {len(assets_to_generate)} Iconify URLs...")
    try:
        result = crew.kickoff()
        output = str(result.raw).strip()
        if output.startswith("```json"):
            output = output[7:]
        elif output.startswith("```"):
            output = output[3:]
        if output.endswith("```"):
            output = output[:-3]
        return json.loads(output.strip())
    except Exception as e:
        print(f"[ASSET AGENT ERROR] {e}")
        print("[ASSET AGENT] Using smart heuristic fallback for Iconify URLs...")
        fallback_assets = {}
        for aid, desc in assets_to_generate.items():
            d = desc.lower()
            if "docker" in d:
                fallback_assets[aid] = "https://api.iconify.design/logos/docker-icon.svg"
            elif "langchain" in d:
                fallback_assets[aid] = "https://api.iconify.design/logos/langchain-icon.svg"
            elif "brain" in d or "llm" in d or "ai" in d or "prompt" in d:
                fallback_assets[aid] = "https://api.iconify.design/lucide/brain-circuit.svg?color=%238b5cf6"
            elif "data" in d or "database" in d or "vector" in d or "store" in d:
                fallback_assets[aid] = "https://api.iconify.design/lucide/database.svg?color=%233b82f6"
            elif "server" in d or "host" in d or "cloud" in d:
                fallback_assets[aid] = "https://api.iconify.design/lucide/server.svg?color=%236366f1"
            elif "tool" in d or "action" in d or "wrench" in d:
                fallback_assets[aid] = "https://api.iconify.design/lucide/wrench.svg?color=%23ef4444"
            elif "memory" in d or "history" in d:
                fallback_assets[aid] = "https://api.iconify.design/lucide/history.svg?color=%23f59e0b"
            elif "bot" in d or "agent" in d:
                fallback_assets[aid] = "https://api.iconify.design/lucide/bot.svg?color=%2310b981"
            elif "search" in d or "file" in d or "doc" in d:
                fallback_assets[aid] = "https://api.iconify.design/lucide/file-search.svg?color=%233b82f6"
            elif "chain" in d or "tunnel" in d or "link" in d:
                fallback_assets[aid] = "https://api.iconify.design/lucide/link-2.svg?color=%2310b981"
            else:
                clean_text = desc.replace(" ", "+")
                fallback_assets[aid] = f"https://api.iconify.design/lucide/sparkles.svg?color=%232563eb"
        return fallback_assets
