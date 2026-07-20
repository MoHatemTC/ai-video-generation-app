import os
from openai import AsyncOpenAI
from backend.app.schemas.script import VideoScriptBlueprint

async def generate_script(user_prompt: str) -> VideoScriptBlueprint:
    # Initialize the client INSIDE the function to avoid import crashes.
    # LiteLLM uses the OpenAI SDK format, we just point it to the Sprints URL!
    client = AsyncOpenAI(
        api_key=os.getenv("LITELLM_API_KEY"),
        base_url=os.getenv("LITELLM_BASE_URL")
    )
    
    # Use the model defined in your .env
    model_name = os.getenv("LITELLM_MODEL", "kimi-k2.5")
    
    system_prompt = """
    You are an expert educational video scriptwriter. 
    Convert the user's educational topic into a highly engaging, well-structured video script.
    You must divide the script into visual segments and narrator dialogue.
    """
    
    # We use the beta.chat.completions.parse method to force the AI 
    # to return a perfect JSON matching your VideoScriptBlueprint schema
    response = await client.beta.chat.completions.parse(
        model=model_name,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Create an educational video about: {user_prompt}"}
        ],
        response_format=VideoScriptBlueprint,
    )
    
    return response.choices[0].message.parsed