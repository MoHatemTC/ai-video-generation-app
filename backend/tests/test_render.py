import os
import subprocess

import pytest

from backend.services import render


def _make_silent_audio(path: str, duration: float):
    subprocess.run(
        ["ffmpeg", "-y", "-f", "lavfi", "-i", f"anullsrc=r=44100:cl=mono", "-t", str(duration), path],
        check=True, capture_output=True,
    )


def _make_test_png(path: str):
    from PIL import Image
    Image.new("RGB", (320, 320), color=(200, 50, 50)).save(path)


@pytest.mark.skipif(subprocess.run(["which", "ffmpeg"], capture_output=True).returncode != 0,
                     reason="ffmpeg not installed")
def test_render_video_produces_playable_mp4(tmp_path):
    png_path = str(tmp_path / "e1.png")
    audio_path = str(tmp_path / "audio.mp3")
    output_path = str(tmp_path / "out.mp4")

    _make_test_png(png_path)
    _make_silent_audio(audio_path, duration=2.0)

    composed = {
        "canvas_w": 640, "canvas_h": 360, "total_duration": 2.0,
        "scenes": [{
            "scene_id": 1, "layout": "image_focus", "start": 0.0, "end": 2.0,
            "elements": [{"element_id": "e1", "file_path": png_path, "x": 10, "y": 10,
                          "w": 100, "h": 100, "appear_time": 0.5}],
        }],
    }

    result_path = render.render_video(composed, audio_path, srt_path=None, output_path=output_path)

    assert os.path.exists(result_path)
    assert os.path.getsize(result_path) > 1000

    probe = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of",
         "default=noprint_wrappers=1:nokey=1", result_path],
        capture_output=True, text=True, check=True,
    )
    duration = float(probe.stdout.strip())
    assert 1.5 <= duration <= 2.5
