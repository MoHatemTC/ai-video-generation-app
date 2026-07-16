"""Run Youssef's Animation + Final Render stages from the terminal.

Example:
    python run_pipeline.py composition.json narration.mp3
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from agents.animation import create_animation_map
from agents.final_render import render_final_video, save_animation_metadata


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

    # Stage 7 - Animation Engine
    animation_data = create_animation_map(composition_data)
    video_id = composition_data["video_id"]
    metadata_path = Path("outputs") / f"{video_id}_animation_metadata.json"
    metadata_path.parent.mkdir(parents=True, exist_ok=True)
    save_animation_metadata(animation_data, metadata_path)
    print(f"Stage 7 complete: {metadata_path}")

    # Stage 8 - Final Render
    audio_data = {
        "video_id": video_id,
        "audio_file_path": str(audio_path.resolve()),
    }
    final_mp4_url = render_final_video(animation_data, audio_data)
    print(f"Stage 8 complete: {final_mp4_url}")


if __name__ == "__main__":
    main()
