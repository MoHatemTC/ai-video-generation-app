"""
Comprehensive unit tests for the Alignment Service.

This test suite validates the integration between the AudioTrack/Script
contracts and the WhisperX alignment logic. It ensures word-level and
segment-level granularity, proper handling of missing word timestamps
(unaligned words), retry logic for file/system failures, dynamic model
loading based on language, adherence to the TimestampMap schema, and
graceful handling of malformed/mismatched inputs.
"""
import sys
import os

# Add the backend directory to the Python path so 'app' is importable from anywhere
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pytest
from unittest.mock import patch, MagicMock
from backend.app.schemas.timestamps import AudioTrack, TimestampMap
from backend.app.services.alignment import AlignmentService


# Updated to match the shared team contract and integer IDs
from backend.app.schemas.script import VideoScriptBlueprint, ScriptSegment

MOCK_SCRIPT = VideoScriptBlueprint(
    title="Test Video",
    target_audience="Beginner",
    estimated_total_duration=10,
    segments=[
        ScriptSegment(segment_id=1, narrator_text="Hello world.", visual_cue="fade in", duration_seconds=1),
        ScriptSegment(segment_id=2, narrator_text="This is a test.", visual_cue="zoom out", duration_seconds=1.5),
    ]
)

MOCK_AUDIO_TRACK = AudioTrack(
    audio_id="audio_001",
    audio_path="/fake/path/audio.wav",
    language="en",
    duration=2.0
)

MOCK_VIDEO_ID = "video_test_001"

# Mock data simulating a successful WhisperX alignment output (including a word missing timing)
MOCK_WHISPERX_RESULT = {
    "segments": [
        {
            "text": "Hello world.",
            "start": 0.0, "end": 1.0,
            "words": [
                {"word": "Hello", "start": 0.1, "end": 0.4, "score": 0.9},
                {"word": "world.", "start": 0.5, "end": 0.9, "score": 0.9}
            ]
        },
        {
            "text": "This is a test.",
            "start": 1.1, "end": 2.0,
            "words": [
                {"word": "This", "start": 1.1, "end": 1.3, "score": 0.9},
                {"word": "is"}, # Missing start/end timing to test allowance
                {"word": "a", "start": 1.5, "end": 1.6, "score": 0.9},
                {"word": "test.", "start": 1.6, "end": 1.9, "score": 0.9}
            ]
        }
    ]
}

@pytest.fixture
def mock_whisperx():
    """Mocks the whisperx module to avoid loading actual ML models during tests."""
    with patch("app.services.alignment.whisperx") as mock:
        # Mock model loading
        mock.load_align_model.return_value = (MagicMock(), MagicMock())
        # Mock audio loading (return a dummy numpy array of length 32000 -> 2 seconds at 16khz)
        mock.load_audio.return_value = [0] * 32000 
        # Mock alignment result
        mock.align.return_value = MOCK_WHISPERX_RESULT
        yield mock

def test_alignment_service_initialization():
    """Test that the service initializes correctly without loading models immediately."""
    service = AlignmentService(device="cpu")
    assert service.device == "cpu"
    assert len(service._models) == 0

def test_alignment_success(mock_whisperx):
    """Test the happy path where text is successfully aligned to audio."""
    service = AlignmentService(device="cpu")
    
    result = service.align(MOCK_SCRIPT, MOCK_AUDIO_TRACK, video_id=MOCK_VIDEO_ID)
    
    # Assert model loaded dynamically based on language
    mock_whisperx.load_align_model.assert_called_once_with(language_code="en", device="cpu")
    
    # Assert result is a valid TimestampMap with top-level metadata
    assert isinstance(result, TimestampMap)
    assert result.schema_version == "1.0"
    assert result.video_id == MOCK_VIDEO_ID
    assert result.audio_file_path == MOCK_AUDIO_TRACK.audio_path
    assert result.audio_duration_seconds == MOCK_AUDIO_TRACK.duration
    
    # Assert flat word list contains all words from both segments (2 + 4 = 6)
    assert len(result.word_timestamps) == 6
    
    # Assert first word has correct fields
    first_word = result.word_timestamps[0]
    assert first_word.word_id == "word_1"
    assert first_word.segment_id == "seg_1"
    assert first_word.word_index == 0
    assert first_word.word == "Hello"
    assert first_word.start == 0.1
    assert first_word.end == 0.4
    assert first_word.score == 0.9
    
    # Assert second word in first segment
    second_word = result.word_timestamps[1]
    assert second_word.word_id == "word_2"
    assert second_word.segment_id == "seg_1"
    assert second_word.word_index == 1
    assert second_word.word == "world."
    
    # Assert word_id continues sequentially across segment boundaries
    third_word = result.word_timestamps[2]
    assert third_word.word_id == "word_3"
    assert third_word.segment_id == "seg_2"
    assert third_word.word_index == 0  # Resets per segment
    assert third_word.word == "This"
    
    # Assert missing word timings are handled gracefully (word "is" has no timing)
    missing_word = result.word_timestamps[3]
    assert missing_word.word_id == "word_4"
    assert missing_word.word == "is"
    assert missing_word.segment_id == "seg_2"
    assert missing_word.word_index == 1
    assert missing_word.start is None
    assert missing_word.end is None
    assert missing_word.score is None

def test_segment_timestamps_aggregation(mock_whisperx):
    """Test that segment-level timestamps are aggregated correctly from word timings,
    satisfying the PRD requirement for both word- and segment-level output."""
    service = AlignmentService(device="cpu")

    result = service.align(MOCK_SCRIPT, MOCK_AUDIO_TRACK, video_id=MOCK_VIDEO_ID)

    assert len(result.segment_timestamps) == 2

    seg_1 = result.segment_timestamps[0]
    assert seg_1.segment_id == "seg_1"
    assert seg_1.start == 0.1  # min start of "Hello"/"world."
    assert seg_1.end == 0.9    # max end of "Hello"/"world."

    seg_2 = result.segment_timestamps[1]
    assert seg_2.segment_id == "seg_2"
    # "is" has no timing and must be excluded from the min/max, not crash it
    assert seg_2.start == 1.1  # min start across This/a/test. (is excluded)
    assert seg_2.end == 1.9    # max end across This/a/test. (is excluded)

def test_alignment_retries_on_failure(mock_whisperx):
    """Test that the service retries on failure and eventually raises an error."""
    service = AlignmentService(device="cpu")
    
    # Force load_audio to fail to simulate a missing file or permission issue
    mock_whisperx.load_audio.side_effect = FileNotFoundError("Audio not found")
    
    with pytest.raises(RuntimeError) as exc_info:
        # Should attempt 3 times (initial + 2 retries)
        service.align(MOCK_SCRIPT, MOCK_AUDIO_TRACK, video_id=MOCK_VIDEO_ID, retries=2)
        
    assert "Alignment process failed after 2 retries" in str(exc_info.value)
    # Verify the mock was called the correct number of times due to retries
    assert mock_whisperx.load_audio.call_count == 3

def test_output_matches_downstream_contract(mock_whisperx):
    """Test that the output structure matches the expected downstream schema
    used by Scene Planner / Animation Engine (word_id linkable for appearance_trigger)."""
    service = AlignmentService(device="cpu")
    
    result = service.align(MOCK_SCRIPT, MOCK_AUDIO_TRACK, video_id=MOCK_VIDEO_ID)
    
    # Serialize to dict (as downstream stages would consume it)
    output = result.model_dump()
    
    # Validate top-level keys match the expected contract
    assert "schema_version" in output
    assert "video_id" in output
    assert "audio_file_path" in output
    assert "audio_duration_seconds" in output
    assert "word_timestamps" in output
    assert "segment_timestamps" in output
    
    # Validate each word entry has the required downstream fields
    for word_entry in output["word_timestamps"]:
        assert "word_id" in word_entry
        assert "segment_id" in word_entry
        assert "word_index" in word_entry
        assert "word" in word_entry
        assert "start" in word_entry
        assert "end" in word_entry
    
    # Validate word_ids can be used as lookup keys (all unique)
    word_ids = [w["word_id"] for w in output["word_timestamps"]]
    assert len(word_ids) == len(set(word_ids)), "word_ids must be unique"
    
    # Validate a specific word can be found by word_id (animation trigger use case)
    word_3 = next(w for w in output["word_timestamps"] if w["word_id"] == "word_3")
    assert word_3["word"] == "This"
    assert word_3["segment_id"] == "seg_2"

def test_audio_duration_from_array_when_not_provided(mock_whisperx):
    """Test that audio_duration_seconds is computed from the audio array
    when AudioTrack.duration is not provided."""
    service = AlignmentService(device="cpu")
    
    # Create AudioTrack without explicit duration
    audio_track_no_duration = AudioTrack(
        audio_id="audio_002",
        audio_path="/fake/path/audio2.wav",
        language="en",
        duration=None
    )
    
    result = service.align(MOCK_SCRIPT, audio_track_no_duration, video_id=MOCK_VIDEO_ID)
    
    # Mock audio is [0]*32000, at 16kHz sample rate = 2.0 seconds
    assert result.audio_duration_seconds == 2.0

# --- Malformed / edge-case input handling ---

def test_empty_script_returns_empty_timestamp_map():
    """Test that an empty Script (no segments) does not crash the service and
    does not attempt to load a model or touch WhisperX -- it just returns a
    schema-valid, empty TimestampMap so the pipeline can continue."""
    service = AlignmentService(device="cpu")
    
    # Updated to VideoScriptBlueprint
    empty_script = VideoScriptBlueprint(title="", target_audience="", estimated_total_duration=0, segments=[])

    with patch("app.services.alignment.whisperx") as mock_whisperx:
        result = service.align(empty_script, MOCK_AUDIO_TRACK, video_id=MOCK_VIDEO_ID)

        mock_whisperx.load_align_model.assert_not_called()
        mock_whisperx.load_audio.assert_not_called()

    assert isinstance(result, TimestampMap)
    assert result.word_timestamps == []
    assert result.segment_timestamps == []
    assert result.audio_duration_seconds == MOCK_AUDIO_TRACK.duration

def test_segment_count_mismatch_handled_gracefully(mock_whisperx):
    """Test that if WhisperX returns fewer segments than the script has
    (a malformed/unexpected upstream response), the service processes the
    overlapping segments instead of raising an uncaught IndexError."""
    service = AlignmentService(device="cpu")

    # Only one segment returned, even though MOCK_SCRIPT has two.
    mock_whisperx.align.return_value = {
        "segments": [
            {
                "text": "Hello world.",
                "start": 0.0, "end": 1.0,
                "words": [
                    {"word": "Hello", "start": 0.1, "end": 0.4, "score": 0.9},
                    {"word": "world.", "start": 0.5, "end": 0.9, "score": 0.9}
                ]
            }
        ]
    }

    result = service.align(MOCK_SCRIPT, MOCK_AUDIO_TRACK, video_id=MOCK_VIDEO_ID)

    # Only the overlapping segment (seg_01) should be present; no crash.
    assert len(result.segment_timestamps) == 1
    assert result.segment_timestamps[0].segment_id == "seg_1"
    assert len(result.word_timestamps) == 2