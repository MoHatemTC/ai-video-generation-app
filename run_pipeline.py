"""
Run Youssef's Animation + Final Render stages from the terminal.

Example:
    python run_pipeline.py composition.json narration.mp3
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from backend.models.timeline import TimestampMap
from backend.services.animation import sync_animation
from backend.services.render import render_final_video


def main() -> None:
    if len(sys.argv) != 3:
        print("Usage: python run_pipeline.py <composition.json> <audio-file>")
        raise SystemExit(2)

    composition_path = Path(sys.argv[1])
    audio_path = Path(sys.argv[2])

    if not composition_path.is_file():
        raise FileNotFoundError(f"Composition JSON not found: {composition_path}")

    if not audio_path.is_file():
        raise FileNotFoundError(f"Audio file not found: {audio_path}")

    with composition_path.open(encoding="utf-8") as file:
        composition_data = json.load(file)

    # Placeholder timestamp map until integrated with transcript service
    timestamp_map = TimestampMap(
        segments=[],
        total_duration=0.0,
    )

    # Stage 7 - Animation
    animation_layout = sync_animation(
        composition_data,
        timestamp_map,
    )

    animation_data = {
        "animation_metadata": animation_layout,
        "composed_layout": animation_layout,
        "subtitle_file": None,
    }

    audio_data = {
        "video_id": composition_data["video_id"],
        "audio_file_path": str(audio_path.resolve()),
    }

    output = render_final_video(
        animation_data,
        audio_data,
    )

    print(f"Final video generated: {output}")


if __name__ == "__main__":
    main()