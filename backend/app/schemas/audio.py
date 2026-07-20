from pydantic import BaseModel, ConfigDict, Field
from typing import Optional


class TTSRequest(BaseModel):
    """
    Schema representing the input payload for generating a voiceover.
    """

    video_id: Optional[str] = Field(
        default=None,
        description="The pipeline's standardized video_id, carried through "
        "so downstream stages can correlate this audio with its video.",
    )
    script_text: str = Field(
        ...,
        description="The full educational script text to be converted to audio.",
        json_schema_extra={"example": "Welcome to our course on APIs."},
    )
    voice: str = Field(
        default="gemini-voice-a",
        description="The voice identifier/model name to be used for narration.",
    )
    speaking_rate: float = Field(
        default=1.0,
        ge=0.5,
        le=2.0,
        description="Narration speed multiplier (between 0.5 and 2.0).",
    )


class AudioTrack(BaseModel):
    """
    Schema representing the output contract for generated audio metadata.
    Matches the team's Stage 3 JSON Contract.

    Note: `audio_file_path` will be a local path when Supabase is not
    configured (e.g. during tests), and a Supabase Storage public URL
    once uploaded. Downstream stages (Alignment / Whisper) should treat
    it as "wherever the audio actually lives", not assume a local path.
    """

    audio_file_path: str = Field(
        ...,
        description="Local path or Supabase Storage URL where the audio file is stored.",
        json_schema_extra={"example": "/tmp/audio_123.wav"},
    )
    video_id: Optional[str] = Field(
        default=None,
        description="The pipeline's standardized video_id this audio belongs to.",
    )
    duration_seconds: float = Field(
        ..., ge=0.0, description="Exact duration of the audio file in seconds."
    )
    voice_used: str = Field(
        ..., description="The voice model used to generate this audio track."
    )
    speaking_rate: float = Field(
        default=1.0, description="The speaking rate applied to the generated audio."
    )
    file_size_bytes: Optional[int] = Field(
        default=None, description="Size of the audio file in bytes."
    )
    storage_path: Optional[str] = Field(
        default=None,
        description="Path/key inside the Supabase Storage bucket (None if not yet uploaded).",
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "video_id": "vid_123",
                "audio_file_path": "https://<project>.supabase.co/storage/v1/object/public/audio-files/abc123.wav",
                "duration_seconds": 45.5,
                "voice_used": "gemini-voice-a",
                "speaking_rate": 1.0,
                "file_size_bytes": 102400,
                "storage_path": "abc123.wav",
            }
        }
    )