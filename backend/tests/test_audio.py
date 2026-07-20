import os
import sys
from pathlib import Path
from unittest.mock import MagicMock
import tempfile
import pytest

# BASE_DIR = repo root (backend/tests -> backend -> repo root), matching
# the import convention used everywhere else in the service code
# (`from backend.schemas...` / `from backend.services...`). Keeping this
# consistent avoids the same module being imported twice under two
# different names (once as `backend.schemas.audio`, once as `schemas.audio`).
BASE_DIR = Path(__file__).resolve().parent.parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from backend.app.schemas.audio import TTSRequest, AudioTrack  # noqa: E402
from backend.app.services.tts_provider import MockTTSProvider  # noqa: E402
from backend.app.services.audio import AudioService, generate_voiceover  # noqa: E402


@pytest.fixture
def temp_storage():
    """Provides a temporary directory for audio cache during tests."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        yield tmp_dir


@pytest.fixture
def audio_service(temp_storage):
    """AudioService with no Supabase client - local-only, cost-free."""
    provider = MockTTSProvider()
    return AudioService(tts_provider=provider, storage_dir=temp_storage)


@pytest.fixture
def mock_supabase_client():
    """
    A fake `supabase.Client` good enough to exercise the upload path
    without any network access. Mirrors the two calls AudioService
    actually makes: storage.from_(bucket).upload(...) and
    storage.from_(bucket).get_public_url(...).
    """
    client = MagicMock()
    client.storage.from_.return_value.upload.return_value = {"path": "fake.wav"}
    client.storage.from_.return_value.get_public_url.return_value = (
        "https://fake-project.supabase.co/storage/v1/object/public/audio-files/fake.wav"
    )
    return client


@pytest.fixture
def audio_service_with_supabase(temp_storage, mock_supabase_client):
    provider = MockTTSProvider()
    return AudioService(
        tts_provider=provider,
        storage_dir=temp_storage,
        supabase_client=mock_supabase_client,
        storage_bucket="audio-files",
    )


@pytest.mark.asyncio
async def test_generate_audio_track_creates_file(audio_service):
    """
    Test 1: Verifies that AudioService takes a TTSRequest, calls Provider,
    saves a .wav file, and returns a valid AudioTrack schema.
    """
    request = TTSRequest(
        script_text="Welcome to our course on APIs.",
        voice="gemini-voice-a",
        speaking_rate=1.0,
    )

    result = await audio_service.generate_audio_track(request)

    assert isinstance(result, AudioTrack)
    assert os.path.exists(result.audio_file_path)
    assert result.duration_seconds >= 0.0
    assert result.voice_used == "gemini-voice-a"
    assert result.file_size_bytes is not None and result.file_size_bytes > 0
    assert result.storage_path is None  # no Supabase client configured


@pytest.mark.asyncio
async def test_audio_caching_mechanism(audio_service):
    """
    Test 2: Verifies that calling generate_audio_track twice with the exact same request
    reuses the cached file instead of recreating it.
    """
    request = TTSRequest(
        script_text="Caching test prompt.", voice="gemini-voice-a", speaking_rate=1.0
    )

    track_1 = await audio_service.generate_audio_track(request)
    first_mtime = os.path.getmtime(track_1.audio_file_path)

    track_2 = await audio_service.generate_audio_track(request)
    second_mtime = os.path.getmtime(track_2.audio_file_path)

    assert track_1.audio_file_path == track_2.audio_file_path
    assert first_mtime == second_mtime  # Modification time hasn't changed = cached!


@pytest.mark.asyncio
async def test_speaking_rate_bounds_are_validated():
    """
    Test 3: Edge case - TTSRequest must reject speaking rates outside [0.5, 2.0]
    before any TTS/Supabase call is ever attempted (fail fast, no wasted spend).
    """
    with pytest.raises(Exception):
        TTSRequest(script_text="Too fast.", speaking_rate=5.0)

    with pytest.raises(Exception):
        TTSRequest(script_text="Too slow.", speaking_rate=0.1)


@pytest.mark.asyncio
async def test_generate_audio_track_uploads_to_supabase(
    audio_service_with_supabase, mock_supabase_client
):
    """
    Test 4: When a Supabase client is configured, the service uploads the
    generated file to Storage and returns the public URL as audio_file_path,
    while still keeping the storage key on the schema.
    """
    request = TTSRequest(script_text="Upload me to Supabase.", voice="gemini-voice-a")

    result = await audio_service_with_supabase.generate_audio_track(request)

    mock_supabase_client.storage.from_.assert_called_with("audio-files")
    assert result.audio_file_path.startswith("https://")
    assert result.storage_path == result.storage_path  # non-None, set below
    assert result.storage_path is not None


@pytest.mark.asyncio
async def test_supabase_upload_failure_is_not_swallowed(
    temp_storage, mock_supabase_client
):
    """
    Test 5: Edge case - if the Supabase upload throws, AudioService must
    propagate the error rather than silently returning a "successful"
    AudioTrack that was never actually persisted to Storage. This lets the
    orchestrator's existing try/except mark the job as failed and retry.
    """
    mock_supabase_client.storage.from_.return_value.upload.side_effect = Exception(
        "network error"
    )
    provider = MockTTSProvider()
    service = AudioService(
        tts_provider=provider,
        storage_dir=temp_storage,
        supabase_client=mock_supabase_client,
        storage_bucket="audio-files",
    )
    request = TTSRequest(script_text="This upload will fail.")

    with pytest.raises(Exception):
        await service.generate_audio_track(request)


@pytest.mark.asyncio
async def test_video_id_is_carried_through_to_output(audio_service):
    """
    Test 6: video_id on the request must appear on the returned AudioTrack,
    per the pipeline-wide standardized-ID contract (locked with Omar/Nada).
    """
    request = TTSRequest(video_id="vid_123", script_text="Video ID passthrough test.")
    result = await audio_service.generate_audio_track(request)
    assert result.video_id == "vid_123"


@pytest.mark.asyncio
async def test_cached_track_reports_current_video_id_not_first_writers(
    audio_service,
):
    """
    Test 7: Regression test for a real bug caught during implementation -
    the cache key is content-based (text+voice+rate), so identical
    narration reused across two DIFFERENT videos hits the same cache
    entry. The video_id on the returned track must always reflect the
    CURRENT request, not whichever video first generated that audio.
    """
    request_a = TTSRequest(video_id="vid_A", script_text="Shared narration.")
    request_b = TTSRequest(video_id="vid_B", script_text="Shared narration.")

    track_a = await audio_service.generate_audio_track(request_a)
    track_b = await audio_service.generate_audio_track(request_b)

    assert track_a.video_id == "vid_A"
    assert track_b.video_id == "vid_B"
    # Same underlying audio file was reused (cache hit) - just the
    # video_id label differs.
    assert track_a.audio_file_path == track_b.audio_file_path


@pytest.mark.asyncio
async def test_generate_voiceover_entry_point_matches_locked_contract():
    """
    Test 8: The orchestrator-facing entry point Omar will `await` directly.
    Verifies the exact input/output shape locked in with Omar + Nada on
    2026-07-16: script_data dict in, {video_id, audio_file_path,
    duration_seconds, voice_used} dict out - not an AudioTrack object.
    """
    script_data = {
        "video_id": "vid_999",
        "title": "Intro to APIs",
        "segments": [
            {"segment_id": "seg_1", "text": "Welcome to our course.", "visual_cue": "intro"},
            {"segment_id": "seg_2", "text": "Today we cover APIs.", "visual_cue": "diagram"},
        ],
    }

    result = await generate_voiceover(script_data, tts_provider=MockTTSProvider())

    assert isinstance(result, dict)  # NOT an AudioTrack/Pydantic object
    assert result["video_id"] == "vid_999"
    assert "audio_file_path" in result
    assert result["duration_seconds"] > 0
    assert result["voice_used"] == "gemini-voice-a"  # TTSRequest's default voice