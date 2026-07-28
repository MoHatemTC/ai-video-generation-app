import os
from dotenv import load_dotenv

load_dotenv()

# We pull the model from the environment. If it's missing, it defaults to 3.5 Flash.
PLANNER_MODEL = os.getenv("PLANNER_MODEL", "gemini/gemini-3.5-flash")

def get_planner_config():
    return {
        "model_name": PLANNER_MODEL,
        "api_key": os.getenv("GEMINI_API_KEY"),
        "base_url": None  # Set to None for direct Google API calls
    }