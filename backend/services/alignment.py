"""
Timestamped Transcription (Alignment): narration audio -> word/segment timestamps (PRD 7.5).

Primary path: forced alignment via the Whisper API (real word-level timestamps
from the actual rendered audio -- this is what the PRD asks for).

Fallback path: if no AI provider is configured (AIConfigError) or the provider
call fails, fall back to an even-split heuristic driven by each segment's
`duration_seconds` estimate from the script. This keeps the pipeline runnable
end-to-end for local development without an API key, at the cost of timing
accuracy -- this tradeoff is logged, never silently hidden.
"""
import logging

from backend.models.script import VideoScriptBlueprint
from backend.models.timeline import SegmentTimestamp, TimestampMap, WordTimestamp
from backend.services.ai_client import AIConfigError, transcribe_with_word_timestamps

logger = logging.getLogger(__name__)


def _heuristic_alignment(script: VideoScriptBlueprint) -> TimestampMap:
    segments = []
    cursor = 0.0
    for segment in script.segments:
        words = segment.text.split()
        duration = max(segment.duration_seconds, 1)
        per_word = duration / max(len(words), 1)
        word_timestamps = []
        word_cursor = cursor
        for word in words:
            word_timestamps.append(
                WordTimestamp(word=word, start=round(word_cursor, 2), end=round(word_cursor + per_word, 2))
            )
            word_cursor += per_word
        segments.append(
            SegmentTimestamp(
                segment_id=segment.segment_id,
                start=round(cursor, 2),
                end=round(cursor + duration, 2),
                words=word_timestamps,
            )
        )
        cursor += duration
    return TimestampMap(segments=segments, total_duration=round(cursor, 2))


def align_audio_to_script(script: VideoScriptBlueprint, audio_path: str | None) -> TimestampMap:
    """
    Produce a TimestampMap for the rendered audio. Uses real forced alignment
    when a provider + audio file are available; otherwise falls back to an
    even-split heuristic so the pipeline stays runnable offline.
    """
    if not audio_path:
        logger.warning("No audio_path provided; using heuristic alignment.")
        return _heuristic_alignment(script)

    try:
        raw = transcribe_with_word_timestamps(audio_path=audio_path)
    except AIConfigError:
        logger.warning("No AI provider configured; using heuristic alignment instead of real alignment.")
        return _heuristic_alignment(script)
    except Exception as exc:  # provider/network failure -- degrade gracefully, don't crash the job
        logger.warning("Alignment provider call failed (%s); using heuristic alignment.", exc)
        return _heuristic_alignment(script)

    # Map the flat word-level Whisper output back onto script segments by
    # walking through segment word counts in order.
    all_words = [
        WordTimestamp(word=w["word"], start=round(w["start"], 2), end=round(w["end"], 2))
        for w in raw.get("words", [])
    ]
    segments = []
    cursor_idx = 0
    for segment in script.segments:
        n = len(segment.text.split())
        segment_words = all_words[cursor_idx: cursor_idx + n]
        cursor_idx += n
        start = segment_words[0].start if segment_words else 0.0
        end = segment_words[-1].end if segment_words else start
        segments.append(
            SegmentTimestamp(segment_id=segment.segment_id, start=start, end=end, words=segment_words)
        )
    total_duration = segments[-1].end if segments else 0.0
    return TimestampMap(segments=segments, total_duration=total_duration)
