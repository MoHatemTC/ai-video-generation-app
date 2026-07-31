import os
from dotenv import load_dotenv

load_dotenv()

def get_planner_config():
    gemini_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if gemini_key and not gemini_key.startswith("your_"):
        return {
            "model_name": "gemini/gemini-3.5-flash-lite",
            "api_key": gemini_key,
            "base_url": None
        }
    litellm_key = os.getenv("LITELLM_API_KEY")
    if litellm_key and not litellm_key.startswith("your_"):
        return {
            "model_name": os.getenv("PLANNER_MODEL", "gemini/gemini-3.5-flash-lite"),
            "api_key": litellm_key,
            "base_url": os.getenv("LITELLM_BASE_URL", "https://learner-os.sprints.ai/litellm")
        }
    return get_fallback_config()

def get_fallback_config():
    # Primary fallback: Gemini 3.5 Flash Lite
    gemini_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if gemini_key and not gemini_key.startswith("your_"):
        return {
            "model_name": "gemini/gemini-3.5-flash-lite",
            "api_key": gemini_key,
            "base_url": None
        }
    
    # Secondary fallback to Groq if configured
    groq_key = os.getenv("GROQ_API_KEY")
    if groq_key and not groq_key.startswith("your_"):
        return {
            "model_name": os.getenv("PLANNER_MODEL", "groq/llama-3.3-70b-versatile"),
            "api_key": groq_key,
            "base_url": None
        }
        
    return {
        "model_name": "gemini/gemini-3.5-flash-lite",
        "api_key": None,
        "base_url": None
    }