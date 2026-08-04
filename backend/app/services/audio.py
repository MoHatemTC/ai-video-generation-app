import hashlib
import json
import logging
import os
import sys
import wave
from pathlib import Path
from typing import Optional

BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from backend.app.schemas.audio import AudioTrack, TTSRequest  # noqa: E402
from backend.app.services.tts_provider import BaseTTSProvider, GeminiTTSProvider  # noqa: E402

logger = logging.getLogger(__name__)


class AudioService:
    """
    Core service managing TTS generation, audio file caching,
    audio track metadata extraction, and (optionally) uploading
    the generated file to Supabase Storage.

    Supabase is intentionally optional and injected, not hardcoded:
    - Pass supabase_client=None (default) for local/dev/unit-test runs.
      Every existing test keeps working unchanged.
    - Pass a real `supabase.Client` (from `supabase-py`) to also persist
      the audio file to Storage and get back a public URL in
      `AudioTrack.audio_file_path`.

    NOTE on responsibility boundary: this service does NOT write to the
    `videos` table itself. Per the orchestrator's pipeline.py pattern,
    each stage returns its data and the orchestrator is the one that
    calls `supabase.table("videos").update({"audio_metadata": ...})`.
    This service only owns the audio FILE and its Storage upload.
    """

    def __init__(
        self,
        tts_provider: BaseTTSProvider,
        storage_dir: Optional[str] = None,
        supabase_client=None,
        storage_bucket: str = "audio-files",
    ):
        import tempfile
        self.provider = tts_provider
        self.storage_dir = storage_dir or os.path.join(tempfile.gettempdir(), "audio_cache")
        self.supabase = supabase_client
        self.storage_bucket = storage_bucket
        os.makedirs(self.storage_dir, exist_ok=True)

    def _generate_cache_key(self, request: TTSRequest) -> str:
        """
        Creates a unique SHA-256 hash based on request params
        to prevent redundant API calls and costs.
        """
        raw_string = f"{request.script_text}_{request.voice}_{request.speaking_rate}"
        return hashlib.sha256(raw_string.encode("utf-8")).hexdigest()

    def _get_audio_duration(self, file_path: str) -> float:
        """
        Calculates exact audio duration in seconds.
        Handles WAV files natively and MP3/AAC via ffprobe or size estimation.
        """
        try:
            import wave
            with wave.open(file_path, "rb") as wave_file:
                frames = wave_file.getnframes()
                rate = wave_file.getframerate()
                if rate > 0:
                    return round(frames / float(rate), 2)
        except Exception:
            pass

        try:
            import subprocess, json
            cmd = ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_format", file_path]
            res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=5)
            if res.returncode == 0:
                data = json.loads(res.stdout)
                dur = float(data.get("format", {}).get("duration", 0))
                if dur > 0:
                    return round(dur, 2)
        except Exception:
            pass

        try:
            sz = os.path.getsize(file_path)
            return round(max(3.0, sz / 16000.0), 2)
        except Exception:
            return 5.0

    def _metadata_sidecar_path(self, cache_key: str) -> str:
        """
        Where we remember the last known AudioTrack (including any
        Supabase URL) for a given cache key, so a cache hit doesn't
        re-upload the same file to Storage every time.
        """
        return os.path.join(self.storage_dir, f"{cache_key}.meta.json")

    def _load_cached_track(self, cache_key: str) -> Optional[AudioTrack]:
        meta_path = self._metadata_sidecar_path(cache_key)
        if not os.path.exists(meta_path):
            return None
        try:
            with open(meta_path, "r") as f:
                data = json.load(f)
            return AudioTrack(**data)
        except Exception:
            logger.warning("Failed to read cached audio metadata at %s", meta_path)
            return None

    def _save_cached_track(self, cache_key: str, track: AudioTrack) -> None:
        meta_path = self._metadata_sidecar_path(cache_key)
        try:
            with open(meta_path, "w") as f:
                json.dump(track.model_dump(), f)
        except Exception:
            logger.warning("Failed to write cached audio metadata at %s", meta_path)

    async def _upload_to_supabase(self, file_path: str, storage_key: str) -> str:
        """
        Uploads the local file to the configured Supabase Storage bucket
        and returns a public URL. Raises on failure so the caller (and
        ultimately the orchestrator's try/except) can mark the job failed
        and retry, rather than silently pretending the upload succeeded.
        """
        if not self.supabase:
            raise ValueError("Supabase client is not configured for AudioService.")

        with open(file_path, "rb") as f:
            file_bytes = f.read()

        try:
            self.supabase.storage.from_(self.storage_bucket).upload(
                storage_key,
                file_bytes,
                {"content-type": "audio/wav", "upsert": "true"},
            )
        except Exception as exc:
            logger.error("Supabase upload failed for %s: %s", storage_key, exc)
            raise

        public_url_response = self.supabase.storage.from_(
            self.storage_bucket
        ).get_public_url(storage_key)

        # supabase-py has returned either a plain string or a dict
        # depending on version - handle both defensively.
        if isinstance(public_url_response, dict):
            res = public_url_response.get("publicUrl") or public_url_response.get("public_url")
            return str(res or "")
        return str(public_url_response or "")

    async def generate_audio_track(self, request: TTSRequest) -> AudioTrack:
        """
        Main async method to generate or retrieve a cached AudioTrack,
        uploading to Supabase Storage when a client is configured.
        """
        cache_key = self._generate_cache_key(request)
        file_path = os.path.join(self.storage_dir, f"{cache_key}.wav")

        # 0. If we've handled this exact request before, reuse everything
        #    (including any previously-uploaded Storage URL) without
        #    calling the TTS provider or Supabase again.
        cached_track = self._load_cached_track(cache_key)
        if cached_track is not None and os.path.exists(file_path):
            # Cache key is content-based (text+voice+rate), so identical
            # narration from a DIFFERENT video would hit the same cache
            # entry. Always stamp the current request's video_id rather
            # than blindly returning whatever video_id was cached first.
            if cached_track.video_id != request.video_id:
                cached_track = cached_track.model_copy(
                    update={"video_id": request.video_id}
                )
            return cached_track

        # 1. Caching check: generate only if file doesn't exist locally
        if not os.path.exists(file_path):
            audio_bytes = await self.provider.generate_speech(
                text=request.script_text,
                voice=request.voice,
                speaking_rate=request.speaking_rate,
            )
            with open(file_path, "wb") as f:
                f.write(audio_bytes)

        # 2. Extract metadata
        duration = self._get_audio_duration(file_path)
        file_size = os.path.getsize(file_path)

        audio_file_path = file_path
        storage_path = None

        # 3. Optionally persist to Supabase Storage
        if self.supabase is not None:
            storage_key = f"{cache_key}.wav"
            audio_file_path = await self._upload_to_supabase(file_path, storage_key)
            storage_path = storage_key

        # 4. Construct schema contract
        track = AudioTrack(
            video_id=request.video_id,
            audio_file_path=audio_file_path,
            duration_seconds=duration,
            voice_used=request.voice,
            speaking_rate=request.speaking_rate,
            file_size_bytes=file_size,
            storage_path=storage_path,
        )

        self._save_cached_track(cache_key, track)
        return track


async def generate_voiceover(
    script_data: dict,
    tts_provider: Optional[BaseTTSProvider] = None,
    supabase_client=None,
    storage_bucket: str = "audio-files",
) -> dict:
    """
    Orchestrator-facing entry point for Stage 3 (Voiceover/TTS).

    Contract locked:
      Input:  script_data - the dict Ahmed's Transcript stage returns:
              {
                  "video_id": "...",
                  "title": "...",
                  "segments": [
                      {"segment_id": "seg_1", "text": "...", "visual_cue": "..."},
                      ...
                  ],
              }
      Output: {
                  "video_id": "...",
                  "audio_file_path": "...",
                  "duration_seconds": 45.5,
                  "voice_used": "...",
              }
              
    tts_provider/supabase_client/storage_bucket are optional overrides
    for testing - the orchestrator can call this with just script_data
    and it will default to GeminiTTSProvider with no Supabase upload.
    """
    segments = script_data.get("segments", [])
    narrations = [
        (seg.get("narrator_text") or seg.get("text") or "").strip()
        for seg in segments
        if isinstance(seg, dict)
    ]
    full_narration = " ".join(n for n in narrations if n)
    if not full_narration:
        full_narration = script_data.get("title") or "AI Educational Video Overview"

    request = TTSRequest(
        video_id=script_data.get("video_id"),
        script_text=full_narration,
    )

    provider = tts_provider or GeminiTTSProvider()
    service = AudioService(
        tts_provider=provider,
        supabase_client=supabase_client,
        storage_bucket=storage_bucket,
    )

    track = await service.generate_audio_track(request)

    cache_key = service._generate_cache_key(request)
    local_path = os.path.join(service.storage_dir, f"{cache_key}.wav")

    return {
        "video_id": track.video_id,
        "audio_file_path": track.audio_file_path,
        "duration_seconds": track.duration_seconds,
        "voice_used": track.voice_used,
        "local_path": local_path,
    }