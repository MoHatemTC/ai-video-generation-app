"""
MP4 Video Renderer Engine
Renders HTML video compositions into pixel-perfect .mp4 video files matching the web application 1-to-1.
Uses Playwright Headless Chromium to capture exact CSS styles, animations, typography, and images.
"""

import os
import logging
import subprocess
import asyncio
from pathlib import Path
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

import concurrent.futures

def _playwright_record_worker(
    target_html: str,
    total_duration_ms: int,
    temp_dir: str,
) -> str:
    """
    Record the actual HTML animation using Playwright.
    The HTML scene player and CSS/SVG animations run normally.
    """
    from pathlib import Path
    from playwright.sync_api import sync_playwright

    os.makedirs(temp_dir, exist_ok=True)

    try:
        file_url = Path(os.path.abspath(target_html)).as_uri()

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)

            context = browser.new_context(
                viewport={"width": 1920, "height": 1080},
                record_video_dir=temp_dir,
                record_video_size={
                    "width": 1920,
                    "height": 1080,
                },
            )

            page = context.new_page()

            logger.info("Opening HTML for video recording")

            page.goto(
                file_url,
                wait_until="domcontentloaded",
                timeout=30000,
            )

            try:
                page.wait_for_load_state(
                    "networkidle",
                    timeout=5000,
                )
            except Exception:
                pass

            # Wait for fonts / SVG / assets
            page.wait_for_timeout(1000)

            # Start the actual HTML presentation
            page.evaluate("""
                () => {
                    const overlay =
                        document.getElementById("start-overlay");

                    if (overlay) {
                        overlay.style.display = "none";
                    }

                    if (typeof window.showScene === "function") {
                        window.showScene(0);
                    }

                    if (typeof window.startAutoPlay === "function") {
                        window.startAutoPlay(0);
                    }
                }
            """)

            logger.info(
                "Recording HTML animation for %.2f seconds",
                total_duration_ms / 1000.0,
            )

            # Let all scenes + CSS/SVG animations play
            page.wait_for_timeout(total_duration_ms + 1000)

            video = page.video

            # Closing context finalizes the video
            context.close()
            browser.close()

            if video:
                recorded_path = video.path()

                if (
                    recorded_path
                    and os.path.exists(recorded_path)
                    and os.path.getsize(recorded_path) > 0
                ):
                    logger.info(
                        "Playwright recording completed: %s",
                        recorded_path,
                    )
                    return recorded_path

    except Exception as err:
        logger.exception(
            "Playwright recording failed: %s",
            err,
        )

    return ""


async def render_scene_plan_to_mp4(scene_data: Dict[str, Any], audio_path: str, output_mp4_path: str, html_path: str = "") -> str:
    """
    Render HTML composition + audio track into a standalone .mp4 video file using Playwright + ffmpeg.
    Matches the live HTML webpage visually 1-to-1 with exact audio synchronization.
    """
    try:
        os.makedirs(os.path.dirname(output_mp4_path), exist_ok=True)
        scenes = scene_data.get("scenes", [])
        if not scenes:
            logger.warning("No scenes found in scene_data for MP4 rendering.")
            return ""

        temp_dir = os.path.join(os.path.dirname(output_mp4_path), f"temp_{os.path.basename(output_mp4_path)[:8]}")
        os.makedirs(temp_dir, exist_ok=True)

        # 1. Locate or generate HTML file
        target_html = html_path if (html_path and os.path.exists(html_path)) else ""
        if not target_html:
            possible_html = output_mp4_path.replace(".mp4", ".html")
            if os.path.exists(possible_html):
                target_html = possible_html

        if not target_html or not os.path.exists(target_html):
            # Compile HTML using render_custom
            from backend.app.pipeline.render.render_custom import generate_video_html
            compiled_html = generate_video_html(scene_data)
            target_html = os.path.join(temp_dir, "rendered_page.html")
            with open(target_html, "w", encoding="utf-8") as f:
                f.write(compiled_html)

        slide_images: List[str] = []
        durations: List[float] = []

        # Check audio duration if available
        audio_duration = 0.0
        if audio_path and os.path.exists(audio_path):
            try:
                import wave
                with wave.open(audio_path, "rb") as wf:
                    frames = wf.getnframes()
                    rate = wf.getframerate()
                    if rate > 0:
                        audio_duration = frames / float(rate)
            except Exception:
                pass

            if audio_duration == 0.0:
                try:
                    import json
                    cmd = ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_format", audio_path]
                    res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=5)
                    if res.returncode == 0:
                        data = json.loads(res.stdout)
                        audio_duration = float(data.get("format", {}).get("duration", 0))
                except Exception:
                    pass

        # Calculate exact audio-synced scene durations
        scene_word_counts = []
        for scene in scenes:
            text = scene.get("text") or scene.get("narration") or ""
            words = len(text.split()) if text else 1
            scene_word_counts.append(max(1, words))

        total_words = sum(scene_word_counts)

        for idx, scene in enumerate(scenes):
            is_intro = (scene.get("template") == "intro") or (idx == 0)
            # Check if explicit start/end alignment timestamps exist
            s_time = scene.get("start_time")
            e_time = scene.get("end_time")
            if is_intro:
                duration_sec = 2.5
            elif s_time is not None and e_time is not None and float(e_time) > float(s_time):
                duration_sec = round(float(e_time) - float(s_time), 2)
            elif audio_duration > 0 and total_words > 0:
                # Calculate duration proportional to narration word count
                prop = scene_word_counts[idx] / total_words
                duration_sec = round(prop * audio_duration, 2)
            else:
                hold_ms = scene.get("hold_ms") or 6000
                duration_sec = max(2.5, hold_ms / 1000.0)

            durations.append(max(1.5, duration_sec))

        # Enforce exact total audio alignment
        if audio_duration > 0 and durations:
            total_visual_dur = sum(durations)
            diff = round(audio_duration - total_visual_dur, 2)
            if abs(diff) > 0.1:
                durations[-1] = max(1.5, round(durations[-1] + diff, 2))

        # 2. Use ProcessPoolExecutor to run Playwright capture in an isolated process
        # 2. Record the actual HTML animation using Playwright
        total_duration_ms = int(sum(durations) * 1000)

        recorded_video = ""

        try:
            loop = asyncio.get_running_loop()

            with concurrent.futures.ProcessPoolExecutor(max_workers=1) as executor:
                recorded_video = await loop.run_in_executor(
                    executor,
                    _playwright_record_worker,
                    target_html,
                    total_duration_ms,
                    temp_dir,
                )

        except Exception as pw_err:
            logger.warning(
                f"Playwright recording warning ({pw_err}). "
                "Trying direct invocation..."
            )

            try:
                recorded_video = _playwright_record_worker(
                    target_html,
                    total_duration_ms,
                    temp_dir,
                )
            except Exception as sync_err:
                logger.warning(
                    f"Direct recording fallback failed: {sync_err}"
                )

        

        safe_video_path = os.path.abspath(recorded_video).replace("\\", "/")
        safe_output_path = os.path.abspath(output_mp4_path).replace("\\", "/")

        cmd = [
            "ffmpeg",
            "-y",
            "-i", safe_video_path,
        ]

        if audio_path and os.path.exists(audio_path):
            safe_audio_path = os.path.abspath(audio_path).replace("\\", "/")
            cmd.extend([
                "-i", safe_audio_path,
                "-c:v", "libx264",
                "-preset", "medium",
                "-crf", "18",
                "-pix_fmt", "yuv420p",
                "-c:a", "aac",
                "-b:a", "192k",
                "-shortest",
                "-movflags", "+faststart",
            ])
        else:
            cmd.extend([
                "-c:v", "libx264",
                "-preset", "medium",
                "-crf", "18",
                "-pix_fmt", "yuv420p",
                "-movflags", "+faststart",
            ])

        cmd.append(safe_output_path)

        logger.info(f"Converting Playwright recording to MP4: {output_mp4_path}")

        res = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=180,
        )

        if res.returncode != 0:
            logger.error(
                f"FFmpeg MP4 conversion failed: {res.stderr[-2000:]}"
            )
            return ""

        if os.path.exists(output_mp4_path) and os.path.getsize(output_mp4_path) > 0:
            logger.info(
                f"MP4 rendered successfully: {output_mp4_path} "
                f"({os.path.getsize(output_mp4_path)} bytes)"
            )
            return output_mp4_path

        logger.error("FFmpeg finished but MP4 file was not created.")
        return ""

    except Exception as e:
        logger.error(f"Failed to render MP4 video: {e}")
        return ""


def sync_render_scene_plan_to_mp4(scene_data: Dict[str, Any], audio_path: str, output_mp4_path: str, html_path: str = "") -> str:
    """Synchronous wrapper for render_scene_plan_to_mp4. Use only outside of async contexts."""
    return asyncio.run(render_scene_plan_to_mp4(scene_data, audio_path, output_mp4_path, html_path))

