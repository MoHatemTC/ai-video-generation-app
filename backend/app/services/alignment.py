"""
Forced Alignment Service for Sprints Video Studio.

This module provides the AlignmentService, which bridges the gap between
narration (AudioTrack) and the generated Script. It utilizes WhisperX
to perform word-level forced alignment, outputting precise timestamps
mapped directly to the original script's segment IDs.

This service handles dynamic model loading, fallback rough estimations
using character-proportional timing, and graceful error recovery.
"""
import logging
import time
from typing import Dict, Any, List, Optional, Tuple
import whisperx
import numpy as np

# Use the team's canonical script model
from backend.app.schemas.script import VideoScriptBlueprint

from backend.app.schemas.timestamps import (
    AudioTrack,
    TimestampMap,
    WordTimestamp,
    SegmentTimestamp,
)

logger = logging.getLogger(__name__)

# Rough (pre-alignment) boundary estimate for a single segment: (start, end).
RoughBounds = Dict[str, Tuple[float, float]]

def normalize_segment_id(seg_id: Any) -> str:
    """Standardizes segment IDs to the 'seg_X' string format."""
    seg_id_str = str(seg_id)
    if not seg_id_str.startswith("seg_"):
        return f"seg_{seg_id_str}"
    return seg_id_str

class AlignmentService:
    def __init__(self, device: str = "cpu"):
        """
        Initializes the service. Models are loaded dynamically based on audio language.
        """
        self.device = device
        self.sample_rate = 16000 # WhisperX default sample rate
        self._models = {} # Cache for loaded language models

    def _get_model(self, language_code: str):
        """Loads and caches the alignment model for a specific language."""
        if language_code not in self._models:
            logger.info(f"Loading WhisperX align model for '{language_code}' on {self.device}...")
            try:
                model_a, metadata = whisperx.load_align_model(
                    language_code=language_code,
                    device=self.device
                )
                self._models[language_code] = (model_a, metadata)
            except Exception as e:
                logger.error(f"Failed to load align model for {language_code}: {e}")
                raise RuntimeError(f"Alignment model initialization failed: {e}")
        return self._models[language_code]

    def align(self, script: VideoScriptBlueprint, audio_track: AudioTrack, video_id: str, retries: int = 2) -> TimestampMap:
        """
        Aligns the text script with the audio track to produce word-level timestamps.
        Includes basic retry logic for upstream/file system glitches.

        Args:
            script: The structured script with segments to align.
            audio_track: Reference to the generated voiceover audio track.
            video_id: Identifier for the video this alignment belongs to.
            retries: Number of retry attempts on failure (default: 2).

        Returns:
            TimestampMap with flat word-level timestamps, plus aggregated
            segment-level timestamps, linked to the script's segment IDs.
        """
        if not script.segments:
            # No text to align. Not an upstream failure worth retrying -- return
            # an empty, schema-valid map so the pipeline can continue rather than
            # crash the job.
            logger.warning("Script has no segments; returning empty TimestampMap.")
            return TimestampMap(
                schema_version="1.0",
                video_id=video_id,
                audio_file_path=audio_track.audio_path,
                audio_duration_seconds=audio_track.duration or 0.0,
                word_timestamps=[],
                segment_timestamps=[],
            )

        attempt = 0
        while attempt <= retries:
            try:
                # 1. Ensure the correct language model is loaded
                model_a, metadata = self._get_model(audio_track.language)

                logger.info(f"Loading audio from {audio_track.audio_path} (Attempt {attempt + 1})")
                # 2. Load the audio using whisperx's built-in loader
                audio = whisperx.load_audio(audio_track.audio_path)

                # 3. Prepare segments using proportional duration estimation.
                # This returns the WhisperX-ready segment list AND a local map of
                # rough (start, end) boundaries per segment_id -- it does NOT
                # mutate the caller's `script` object.
                whisperx_segments, rough_bounds = self._prepare_segments_for_alignment(
                    script, audio, audio_track.duration
                )

                # 4. Run forced alignment
                logger.info("Running WhisperX alignment...")
                aligned_result = whisperx.align(
                    transcript=whisperx_segments,
                    model=model_a,
                    align_model_metadata=metadata,
                    audio=audio,
                    device=self.device,
                    return_char_alignments=False
                )

                # 5. Compute audio duration from known duration or audio array length
                audio_duration = audio_track.duration or (len(audio) / self.sample_rate)

                # 6. Map results back to structured TimestampMap
                return self._map_to_schema(
                    script, aligned_result,
                    video_id=video_id,
                    audio_file_path=audio_track.audio_path,
                    audio_duration=audio_duration,
                    rough_bounds=rough_bounds,
                )

            except Exception as e:
                # Catching and handling potential failures to avoid pipeline crashes
                logger.warning(f"Alignment failed on attempt {attempt + 1}: {e}")
                attempt += 1
                if attempt > retries:
                    logger.error("Max retries reached. Alignment failed.")
                    raise RuntimeError(f"Alignment process failed after {retries} retries. Last error: {e}")
                time.sleep(2) # Short backoff before retry

        raise RuntimeError("Alignment process completed without returning a TimestampMap.")

    def _prepare_segments_for_alignment(
        self, script: VideoScriptBlueprint, audio: np.ndarray, known_duration: Optional[float] = None
    ) -> Tuple[List[Dict[str, Any]], RoughBounds]:
        """
        Calculates rough start/end boundaries for WhisperX using character-proportional
        estimation.

        Returns a tuple of:
          - the WhisperX-ready segment list (text + padded search window), and
          - a local `{segment_id: (start, end)}` map of the *unpadded* rough
            boundaries, to be used later as a segment-level fallback if a segment
            ends up with no successfully aligned words.

        Does not mutate `script` or its segments -- the caller's Script object is
        read-only input here, consistent with it being a shared upstream contract.
        """
        total_chars = sum(len(seg.narrator_text) for seg in script.segments)
        audio_duration = known_duration or (len(audio) / self.sample_rate)

        segments = []
        rough_bounds: RoughBounds = {}
        current_time = 0.0

        for seg in script.segments:
            # Guess duration based on character count ratio
            duration_ratio = (len(seg.narrator_text) / total_chars) if total_chars > 0 else 0
            paragraph_duration = duration_ratio * audio_duration

            seg_start = current_time
            seg_end = current_time + paragraph_duration
            rough_bounds[normalize_segment_id(seg.segment_id)] = (seg_start, seg_end)

            # Add a padding/buffer on both sides for the search window as requested
            start_time = max(0.0, seg_start - 10.0)
            end_time = min(audio_duration, seg_end + 10.0)

            segments.append({
                "text": seg.narrator_text,
                "start": start_time,
                "end": end_time
            })


            # Move tracker forward
            current_time = seg_end

        return segments, rough_bounds

    def _map_to_schema(
        self,
        script: VideoScriptBlueprint,
        aligned_result: Dict[str, Any],
        video_id: str,
        audio_file_path: str,
        audio_duration: float,
        rough_bounds: RoughBounds,
    ) -> TimestampMap:
        """
        Converts WhisperX dict output back to our rigid Pydantic TimestampMap schema.
        Produces a flat word_timestamps list where each word carries its own
        word_id, segment_id, and word_index so downstream stages can link
        visual cues to specific spoken words, plus a segment_timestamps list
        aggregating start/end per script segment.

        `rough_bounds` (from _prepare_segments_for_alignment) is used as the
        segment-level start/end fallback when a segment has no successfully
        aligned words.
        """
        whisperx_segments = aligned_result.get("segments", [])

        # WhisperX is expected to preserve the order of the input segments list,
        # but a provider glitch (or a future alignment backend) could return a
        # different count. Rather than let that throw an uncaught IndexError,
        # log it and process only the overlapping range -- a partial timestamp
        # map is more useful downstream than a hard pipeline crash.
        if len(whisperx_segments) != len(script.segments):
            logger.warning(
                "WhisperX returned %d segment(s) but script has %d; "
                "processing the overlapping %d segment(s) only.",
                len(whisperx_segments), len(script.segments),
                min(len(whisperx_segments), len(script.segments)),
            )

        segment_count = min(len(whisperx_segments), len(script.segments))

        all_words: List[WordTimestamp] = []
        segment_timestamps: List[SegmentTimestamp] = []
        global_word_counter = 0

        for idx in range(segment_count):
            aligned_seg = whisperx_segments[idx]
            original_script_seg = script.segments[idx]
            seg_id_str = normalize_segment_id(original_script_seg.segment_id)

            segment_words: List[WordTimestamp] = []

            for word_idx, word_data in enumerate(aligned_seg.get("words", [])):
                global_word_counter += 1

                word_ts = WordTimestamp(
                    word_id=f"word_{global_word_counter}",
                    segment_id=seg_id_str,
                    word_index=word_idx,
                    word=word_data["word"],
                    start=word_data.get("start"),
                    end=word_data.get("end"),
                    score=word_data.get("score"),
                )
                all_words.append(word_ts)
                segment_words.append(word_ts)

            # Aggregate segment-level start/end from the words that actually
            # aligned. If none aligned (e.g. all unaligned, or zero words),
            # fall back to the rough character-proportional estimate computed
            # up front in _prepare_segments_for_alignment, so the segment still
            # has a usable boundary for scene/segment-level consumers.
            starts = [w.start for w in segment_words if w.start is not None]
            ends = [w.end for w in segment_words if w.end is not None]

            fallback_start, fallback_end = rough_bounds.get(
                seg_id_str, (None, None)
            )
            seg_start = min(starts) if starts else fallback_start
            seg_end = max(ends) if ends else fallback_end

            segment_timestamps.append(
                SegmentTimestamp(
                    segment_id=seg_id_str,
                    start=seg_start,
                    end=seg_end,
                )
            )

        return TimestampMap(
            schema_version="1.0",
            video_id=video_id,
            audio_file_path=audio_file_path,
            audio_duration_seconds=audio_duration,
            word_timestamps=all_words,
            segment_timestamps=segment_timestamps,
        )