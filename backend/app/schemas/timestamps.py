"""
Timestamp schemas for the Alignment stage.

This module defines the public output contract produced by the
Alignment Service (TimestampMap), as well as the expected upstream
input contracts (Script and AudioTrack). It is intentionally independent
from WhisperX so downstream services (Animation, Composition, Rendering)
never depend on provider-specific objects.

All timestamps use floating-point seconds to match WhisperX output,
and missing timings are handled gracefully to prevent pipeline crashes.
"""
from pydantic import BaseModel, Field
from typing import List, Optional


class ScriptSegment(BaseModel):
    """Represents a single segment or paragraph of the generated script."""
    segment_id: str = Field(..., description="Unique identifier for the script segment (e.g., 'seg_01')")
    text: str = Field(..., description="The narration text for this segment")
    visual_cue: Optional[str] = Field(None, description="The intended visual cue for this segment")
    start: Optional[float] = Field(None, description="Rough start boundary estimate")
    end: Optional[float] = Field(None, description="Rough end boundary estimate")

class Script(BaseModel):
    """The complete script containing ordered segments."""
    segments: List[ScriptSegment] = Field(..., description="Ordered list of script segments")

class AudioTrack(BaseModel):
    """Reference to the generated voiceover audio file."""
    audio_id: str = Field(..., description="Unique identifier for the audio generation")
    audio_path: str = Field(..., description="File path or URI to the generated TTS audio file")
    language: str = Field("en", description="Language code for the audio (e.g., 'en', 'fr')")
    duration: Optional[float] = Field(None, description="Total duration of the audio in seconds, if known")


class WordTimestamp(BaseModel):
    """Precise timing for a single spoken word, with identifiers for downstream linking.

    Each word carries its own word_id and segment_id so the Animation Engine
    can link visual cues (appearance_trigger) to specific spoken words
    without needing segment-level grouping.
    """
    word_id: str = Field(..., description="Unique identifier for this word (e.g., 'word_1')")
    segment_id: str = Field(..., description="The script segment this word belongs to")
    word_index: int = Field(..., description="0-based position of the word within its segment")
    word: str = Field(..., description="The specific word token")
    start_seconds: Optional[float] = Field(None, description="Start time of the word in seconds. May be None if unaligned.")
    end_seconds: Optional[float] = Field(None, description="End time of the word in seconds. May be None if unaligned.")
    score: Optional[float] = Field(None, description="Confidence score from the alignment model")

class SegmentTimestamp(BaseModel):
    """Aggregated timing for an entire script segment.

    Included in the public TimestampMap output (`segment_timestamps`) so
    stages that only need scene/segment-level timing -- e.g. Composition
    deciding when a scene's layout is on screen, or caption generation --
    don't have to re-derive segment boundaries by scanning the flat word
    list themselves. `start`/`end` are the min/max of the segment's aligned
    word timings when at least one word aligned successfully; otherwise
    they fall back to the rough character-proportional estimate computed
    before alignment, so a segment is never left without a boundary.
    `words` duplicates (by reference) the same WordTimestamp objects that
    also appear in TimestampMap.word_timestamps, for convenience when a
    consumer only cares about one segment at a time -- it is not a
    different source of truth from the flat list.
    """
    segment_id: str = Field(..., description="References the original ScriptSegment ID")
    start: Optional[float] = Field(None, description="Start time of the segment in seconds")
    end: Optional[float] = Field(None, description="End time of the segment in seconds")
    words: List[WordTimestamp] = Field(default_factory=list, description="Word-level timestamps within this segment")

class TimestampMap(BaseModel):
    """The final mapped output connecting all audio timings to the script.

    This is the public contract consumed by downstream pipeline stages
    (Scene Planner, Animation Engine, Composition, Rendering). It exposes
    timing at both granularities called out in the PRD:
      - word_timestamps: flat list, for word-level appearance_trigger lookups.
      - segment_timestamps: aggregated per segment_id, for scene/segment-level sync.
    `segment_timestamps` defaults to an empty list so existing producers/consumers
    that only populate word_timestamps (e.g. hand-built fixtures) remain valid.
    """
    schema_version: str = Field("1.0", description="Schema version for forward compatibility")
    video_id: str = Field(..., description="Identifier for the video this timestamp map belongs to")
    audio_file_path: str = Field(..., description="Path to the audio file that was aligned")
    audio_duration_seconds: float = Field(..., description="Total duration of the audio in seconds")
    word_timestamps: List[WordTimestamp] = Field(..., description="Flat list of all word-level timestamps across all segments")
    segment_timestamps: List[SegmentTimestamp] = Field(default_factory=list, description="Aggregated start/end + words per script segment")