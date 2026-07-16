"""
Shared, swappable AI provider client (PRD 10.1: "keep the interface abstracted").

Every pipeline stage that talks to an LLM or TTS provider should go through
this module instead of instantiating its own SDK client. That keeps provider
swaps (OpenAI <-> Gemini, or a different TTS vendor) to a single file.
"""
import os
from functools import lru_cache
from typing import Type, TypeVar

from openai import OpenAI
from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


class AIConfigError(RuntimeError):
    """Raised when a required provider API key is missing."""


@lru_cache
def get_openai_client() -> OpenAI:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise AIConfigError(
            "OPENAI_API_KEY is not set. Copy .env.example to .env and add your key."
        )
    return OpenAI(api_key=api_key)


def structured_completion(
    *,
    system_prompt: str,
    user_prompt: str,
    response_model: Type[T],
    model: str = "gpt-4o-mini",
    temperature: float = 0.3,
) -> T:
    """Call the chat completions API and parse the result into `response_model`."""
    client = get_openai_client()
    response = client.beta.chat.completions.parse(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        response_format=response_model,
        temperature=temperature,
    )
    parsed = response.choices[0].message.parsed
    if parsed is None:
        raise ValueError("AI provider returned a response that could not be parsed into the expected schema.")
    return parsed


def text_to_speech(*, text: str, voice: str = "alloy", output_path: str = "audio.mp3") -> str:
    """Generate a voiceover file from text. Returns the output file path."""
    client = get_openai_client()
    with client.audio.speech.with_streaming_response.create(
        model="tts-1",
        voice=voice,
        input=text,
    ) as response:
        response.stream_to_file(output_path)
    return output_path


def transcribe_with_word_timestamps(*, audio_path: str) -> dict:
    """Run forced alignment via the Whisper API and return word-level timestamps."""
    client = get_openai_client()
    with open(audio_path, "rb") as audio_file:
        transcript = client.audio.transcriptions.create(
            model="whisper-1",
            file=audio_file,
            response_format="verbose_json",
            timestamp_granularities=["word"],
        )
    return transcript.model_dump()
