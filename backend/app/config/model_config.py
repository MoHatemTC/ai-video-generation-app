import os
from dotenv import load_dotenv

load_dotenv()

def get_planner_config():
    return {
        "model_name": "openai/kimi-k2.5",
        "api_key": os.getenv("LITELLM_API_KEY"),
        "base_url": "https://learner-os.sprints.ai/litellm"
    }

def get_fallback_config():
    # Prioritize Gemini 3.5 Flash Lite if available
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