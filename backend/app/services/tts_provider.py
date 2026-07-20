from abc import ABC, abstractmethod
import asyncio
import base64
import io
import logging
import os
import wave

logger = logging.getLogger(__name__)


class BaseTTSProvider(ABC):
    """
    Abstract Base Class for Text-to-Speech providers.
    Ensures zero vendor lock-in by enforcing a standard interface.
    """

    @abstractmethod
    async def generate_speech(
        self, text: str, voice: str = "gemini-voice-a", speaking_rate: float = 1.0
    ) -> bytes:
        """
        Converts text into audio bytes.

        :param text: The text content to read aloud.
        :param voice: Voice model identifier.
        :param speaking_rate: Rate multiplier for narration speed.
        :return: Raw audio bytes (e.g. WAV or MP3).
        """
        pass


class GeminiTTSProvider(BaseTTSProvider):
    """
    Concrete TTS Provider using Google's Gemini API.

    """

    _VOICE_MAP = {
        "gemini-voice-a": "Kore",
        "gemini-voice-b": "Puck",
    }
    _KNOWN_GEMINI_VOICES = {
        "Zephyr", "Puck", "Charon", "Kore", "Fenrir", "Leda", "Orus",
        "Aoede", "Callirrhoe", "Autonoe", "Enceladus", "Iapetus",
        "Umbriel", "Algieba", "Despina", "Erinome", "Algenib",
        "Rasalgethi", "Laomedeia", "Achernar", "Alnilam", "Schedar",
        "Gacrux", "Pulcherrima", "Achird", "Zubenelgenubi",
        "Vindemiatrix", "Sadachbia", "Sadaltager", "Sulafat",
    }
    _DEFAULT_VOICE = "Kore"
    _DEFAULT_MODEL = "gemini-3.1-flash-tts-preview"
    _MAX_RETRIES = 2  # Google's docs note occasional transient 500s on TTS

    def __init__(self, api_key: str | None = None, model: str | None = None):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        self.model = model or self._DEFAULT_MODEL
        self._client = None

    def _get_client(self):
        if self._client is None:
            if not self.api_key:
                raise ValueError(
                    "GEMINI_API_KEY is missing. Please set it in your .env "
                    "file (or pass api_key= explicitly)."
                )
            from google import genai  # local import: only needed for real calls
            self._client = genai.Client(api_key=self.api_key)
        return self._client

    def _resolve_voice(self, voice: str) -> str:
        if voice in self._KNOWN_GEMINI_VOICES:
            return voice
        mapped = self._VOICE_MAP.get(voice)
        if mapped:
            return mapped
        logger.warning(
            "Unknown Gemini voice '%s' - falling back to default '%s'. "
            "Update _VOICE_MAP or pass a real voice name from Gemini's "
            "supported voice list.",
            voice,
            self._DEFAULT_VOICE,
        )
        return self._DEFAULT_VOICE

    @staticmethod
    def _apply_pace_hint(text: str, speaking_rate: float) -> str:
        """
        Approximates the contract's numeric speaking_rate using Gemini's
        natural-language pace tags, since no numeric parameter exists.
        """
        if speaking_rate <= 0.75:
            return f"[very slow] {text}"
        if speaking_rate >= 1.4:
            return f"[very fast] {text}"
        return text

    @staticmethod
    def _pcm_to_wav(
        pcm_bytes: bytes, channels: int = 1, rate: int = 24000, sample_width: int = 2
    ) -> bytes:
        """Gemini TTS returns raw PCM, not a WAV file - wrap it ourselves."""
        buffer = io.BytesIO()
        with wave.open(buffer, "wb") as wf:
            wf.setnchannels(channels)
            wf.setsampwidth(sample_width)
            wf.setframerate(rate)
            wf.writeframes(pcm_bytes)
        return buffer.getvalue()

    async def generate_speech(
        self, text: str, voice: str = "gemini-voice-a", speaking_rate: float = 1.0
    ) -> bytes:
        client = self._get_client()
        resolved_voice = self._resolve_voice(voice)
        prompt = self._apply_pace_hint(text, speaking_rate)

        def _call():
            return client.interactions.create(
                model=self.model,
                input=prompt,
                response_format={"type": "audio"},
                generation_config={"speech_config": [{"voice": resolved_voice}]},
            )

        last_error = None
        for attempt in range(self._MAX_RETRIES + 1):
            try:
                interaction = await asyncio.to_thread(_call)
                pcm_bytes = base64.b64decode(interaction.output_audio.data)
                return self._pcm_to_wav(pcm_bytes)
            except Exception as exc:  # noqa: BLE001
                last_error = exc
                logger.warning(
                    "Gemini TTS call failed (attempt %d/%d): %s",
                    attempt + 1,
                    self._MAX_RETRIES + 1,
                    exc,
                )
        raise RuntimeError(
            f"Gemini TTS generation failed after {self._MAX_RETRIES + 1} attempts"
        ) from last_error
    

class MockTTSProvider(BaseTTSProvider):
    """
    Mock TTS Provider for unit testing and offline development.
    Returns valid minimal WAV binary data without incurring API costs.
    """
 
    async def generate_speech(
        self, text: str, voice: str = "gemini-voice-a", speaking_rate: float = 1.0
    ) -> bytes:
        await asyncio.sleep(0.1)
        sample_rate = 16000
        num_frames = sample_rate  # 1 second of audio
        silent_pcm = b"\x00\x00" * num_frames  # 16-bit silent samples
 
        buffer = io.BytesIO()
        with wave.open(buffer, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sample_rate)
            wf.writeframes(silent_pcm)
        return buffer.getvalue()