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
    return {
        "model_name": os.getenv("PLANNER_MODEL", "groq/llama-3.3-70b-versatile"),
        "api_key": os.getenv("GROQ_API_KEY"),
        "base_url": None
    }