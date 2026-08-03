import os
from dotenv import load_dotenv

load_dotenv()

# ── Primary model: strongest available Gemini via the Sprints LiteLLM proxy ──
PRIMARY_MODEL = "gemini/gemini-2.0-flash"
# ── Fallback model: lighter, proven-reliable Gemini via the same proxy ──
FALLBACK_MODEL = "gemini/gemini-2.0-flash"

def format_model_for_litellm_proxy(model: str) -> str:
    clean = (model or "").strip()
    if clean.startswith("gemini/"):
        return clean
    if clean.startswith("openai/"):
        clean = clean.replace("openai/", "", 1)
    if clean.startswith("google/"):
        clean = clean.replace("google/", "", 1)
    return f"gemini/{clean}"


def get_planner_config():
    # 1. Check Sprints LiteLLM proxy (primary required LLM provider)
    litellm_key = os.getenv("LITELLM_API_KEY")
    if litellm_key and not litellm_key.startswith("your_"):
        base_url = os.getenv("LITELLM_BASE_URL", "https://learner-os.sprints.ai/litellm/v1")
        model = format_model_for_litellm_proxy(os.getenv("MODEL_NAME", PRIMARY_MODEL))
        return {
            "model_name": model,
            "api_key": litellm_key,
            "base_url": base_url
        }

    # 2. Fallback to direct Gemini API key if LiteLLM key is not provided
    gemini_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if gemini_key and not gemini_key.startswith("your_"):
        return {
            "model_name": "gemini-2.0-flash",
            "api_key": gemini_key,
            "base_url": None
        }
    return get_fallback_config()

def get_fallback_config():
    litellm_key = os.getenv("LITELLM_API_KEY")
    if litellm_key and not litellm_key.startswith("your_"):
        base_url = os.getenv("LITELLM_BASE_URL", "https://learner-os.sprints.ai/litellm/v1")
        model = format_model_for_litellm_proxy(FALLBACK_MODEL)
        return {
            "model_name": model,
            "api_key": litellm_key,
            "base_url": base_url
        }

    gemini_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if gemini_key and not gemini_key.startswith("your_"):
        return {
            "model_name": FALLBACK_MODEL,
            "api_key": gemini_key,
            "base_url": None
        }

    return {
        "model_name": FALLBACK_MODEL,
        "api_key": None,
        "base_url": None
    }