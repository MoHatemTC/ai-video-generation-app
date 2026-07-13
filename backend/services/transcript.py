"""
MARKET RESEARCH SIDE TASK: COMPETITOR & E-LEARNING VIDEO AESTHETICS
- Target Audience Engagement: Retaining learner focus requires clear micro-segmentation, limiting individual visual scenes to 15-30 seconds maximum.
- Aesthetic Patterns: High-performing educational platforms favor clean, distraction-free graphics, predictable pacing, and authoritative tones.
- Directorial Cues Formula: Blending spoken text directly with localized on-screen text animations reduces cognitive load and maximizes knowledge retention.
"""

import os
from openai import OpenAI
from backend.models.script import VideoScriptBlueprint

def generate_segmented_script(instruction: str, tone: str, audience: str, length_minutes: float) -> VideoScriptBlueprint:
    """
    Processes video instructions and returns a validated, non-hallucinated structured script blueprint.
    """
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    
    system_prompt = (
        "You are an expert educational video transcript agent.\n"
        "Your task is to convert raw user instructions into a highly structured, factual, and segmented video script.\n"
        "CRITICAL: Ground all content in verified facts. Do NOT hallucinate or introduce unverified assumptions.\n"
        "Strictly adhere to the provided JSON Schema layout without adding any markdown wrap or extra prose."
    )
    
    user_prompt = (
        f"Topic Instruction: {instruction}\n"
        f"Tone: {tone}\n"
        f"Audience Level: {audience}\n"
        f"Target Length: {length_minutes} minute(s)"
    )
    
    response = client.beta.chat.completions.parse(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        response_format=VideoScriptBlueprint,
        temperature=0.3
    )
    
    return response.choices[0].message.parsed