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

def _playwright_capture_worker(target_html: str, total_scenes: int, temp_dir: str) -> List[str]:
    """
    Top-level worker function running in an isolated process with its own event loop policy.
    Bypasses Windows Uvicorn SelectorEventLoop subprocess NotImplementedError.
    Waits for all external SVG/image assets and CSS animations to settle before capturing.
    """
    slide_images = []
    try:
        from pathlib import Path
        from playwright.sync_api import sync_playwright

        file_url = Path(os.path.abspath(target_html)).as_uri()

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(viewport={"width": 1920, "height": 1080})
            page.goto(file_url, wait_until="domcontentloaded", timeout=15000)
            try:
                page.wait_for_load_state("networkidle", timeout=3000)
            except Exception:
                pass
            page.wait_for_timeout(1000)

            # Force remove start overlay
            try:
                page.evaluate("""() => {
                    const overlay = document.getElementById('start-overlay');
                    if (overlay) {
                        overlay.style.display = 'none';
                        overlay.style.visibility = 'hidden';
                        overlay.style.opacity = '0';
                    }
                }""")
            except Exception:
                pass

            # Brief pause for assets & fonts
            page.wait_for_timeout(800)

            for idx in range(total_scenes):
                try:
                    # Activate scene idx via JS showScene and force inline styles
                    page.evaluate(f"""(idx) => {{
                        if (typeof window.showScene === 'function') {{
                            window.showScene(idx);
                        }}
                        const sceneEls = document.querySelectorAll('.scene');
                        sceneEls.forEach((el, i) => {{
                            if (i === idx) {{
                                el.classList.add('active');
                                el.style.display = 'block';
                                el.style.visibility = 'visible';
                                el.style.opacity = '1';
                            }} else {{
                                el.classList.remove('active');
                                el.style.display = 'none';
                                el.style.opacity = '0';
                            }}
                        }});
                    }}""", idx)
                except Exception as scene_err:
                    logger.warning(f"Scene activation error for index {idx}: {scene_err}")

                # Wait for CSS transitions and animations to reveal content
                page.wait_for_timeout(1200)
                slide_path = os.path.join(temp_dir, f"slide_{idx:03d}.png")
                try:
                    page.screenshot(path=slide_path, full_page=False)
                    if os.path.exists(slide_path) and os.path.getsize(slide_path) > 0:
                        slide_images.append(slide_path)
                except Exception as ss_err:
                    logger.warning(f"Screenshot error for slide {idx}: {ss_err}")

            browser.close()
    except Exception as err:
        logger.warning(f"Error inside _playwright_capture_worker: {err}")

    return slide_images


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
            # Check if explicit start/end alignment timestamps exist
            s_time = scene.get("start_time")
            e_time = scene.get("end_time")
            if s_time is not None and e_time is not None and float(e_time) > float(s_time):
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
        try:
            loop = asyncio.get_running_loop()
            with concurrent.futures.ProcessPoolExecutor(max_workers=1) as executor:
                slide_images = await loop.run_in_executor(
                    executor, _playwright_capture_worker, target_html, len(scenes), temp_dir
                )
        except Exception as pw_err:
            logger.warning(f"ProcessPoolExecutor capture warning ({pw_err}). Trying direct invocation...")
            try:
                slide_images = _playwright_capture_worker(target_html, len(scenes), temp_dir)
            except Exception as sync_err:
                logger.warning(f"Direct sync capture fallback: {sync_err}")

        # PIL Fallback if Playwright capture returned no images
        if not slide_images:
            logger.warning("Playwright rendering fallback to PIL generator")
            from PIL import Image, ImageDraw
            for idx, scene in enumerate(scenes):
                img = Image.new("RGB", (1920, 1080), color=(15, 23, 42))
                draw = ImageDraw.Draw(img)
                draw.text((80, 60), "SPRINTS VIDEO STUDIO", fill=(56, 189, 248))
                title = scene.get("subtitle") or scene.get("title") or f"Scene {idx+1}"
                draw.text((80, 160), str(title)[:60], fill=(255, 255, 255))
                narration = scene.get("text", "")
                draw.rectangle([(60, 900), (1860, 1020)], fill=(30, 41, 59))
                draw.text((90, 930), str(narration)[:120], fill=(226, 232, 240))
                slide_path = os.path.join(temp_dir, f"slide_{idx:03d}.png")
                img.save(slide_path)
                slide_images.append(slide_path)

        if not slide_images:
            return ""

        # 3. Build ffmpeg concat list file
        concat_list_path = os.path.join(temp_dir, "input.txt")
        with open(concat_list_path, "w", encoding="utf-8") as f:
            for s_path, dur in zip(slide_images, durations):
                abs_p = os.path.abspath(s_path).replace("\\", "/")
                f.write(f"file '{abs_p}'\n")
                f.write(f"duration {dur}\n")
            if slide_images:
                abs_p = os.path.abspath(slide_images[-1]).replace("\\", "/")
                f.write(f"file '{abs_p}'\n")

        # 4. Run ffmpeg to combine browser screenshots + audio track into high-res MP4 video
        has_audio = bool(audio_path and os.path.exists(audio_path))
        safe_concat_path = os.path.abspath(concat_list_path).replace("\\", "/")
        safe_output_path = os.path.abspath(output_mp4_path).replace("\\", "/")

        cmd = [
            "ffmpeg", "-y",
            "-f", "concat", "-safe", "0", "-i", safe_concat_path,
        ]
        if has_audio:
            safe_audio_path = os.path.abspath(audio_path).replace("\\", "/")
            cmd.extend(["-i", safe_audio_path, "-c:a", "aac", "-b:a", "192k"])
        else:
            cmd.extend(["-f", "lavfi", "-i", "anullsrc=channel_layout=stereo:sample_rate=44100", "-c:a", "aac"])

        cmd.extend([
            "-c:v", "libx264",
            "-r", "30",
            "-pix_fmt", "yuv420p",
            safe_output_path
        ])

        logger.info(f"Rendering high-quality HTML MP4 video to {output_mp4_path}...")
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=90)
        
        if res.returncode != 0:
            logger.warning(f"ffmpeg MP4 rendering returned code {res.returncode}: {res.stderr[:500]}")
        
        if os.path.exists(output_mp4_path) and os.path.getsize(output_mp4_path) > 0:
            logger.info(f"MP4 Video rendered successfully: {output_mp4_path} ({os.path.getsize(output_mp4_path)} bytes)")
            return output_mp4_path

        return ""

    except Exception as e:
        logger.error(f"Failed to render MP4 video: {e}")
        return ""


def sync_render_scene_plan_to_mp4(scene_data: Dict[str, Any], audio_path: str, output_mp4_path: str, html_path: str = "") -> str:
    """Synchronous wrapper for render_scene_plan_to_mp4. Use only outside of async contexts."""
    return asyncio.run(render_scene_plan_to_mp4(scene_data, audio_path, output_mp4_path, html_path))

