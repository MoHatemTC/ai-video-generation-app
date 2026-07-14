"""
Rendering & Delivery: combine composed/animated scenes + voiceover + captions
into a single video file (PRD 7.9).

Approach (documented ADR-lite, per PRD 10.1's Sprint-3 composition-engine
spike): SVG/PNG element overlays driven purely by ffmpeg's `overlay` filter
with `enable='gte(t, appear_time)'` expressions, rather than Manim or
Remotion. This was chosen for the MVP because it needs no extra heavy
runtime (no headless Chromium, no Manim/LaTeX toolchain) and ffmpeg is
already a required system dependency for audio/video muxing either way.
Trade-off: entrances are a hard cut-in, not an eased fade/slide -- a good
Sprint-4 follow-up (see docs/architecture.md) is to fade each overlay in
over ~0.3s via the `alpha='min(1,(t-appear_time)/0.3)'` expression.
"""
import os
import subprocess


def render_video(composed: dict, audio_path: str, srt_path: str | None, output_path: str) -> str:
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

    w, h = composed["canvas_w"], composed["canvas_h"]
    duration = max(composed.get("total_duration", 1.0), 1.0)

    inputs = ["-f", "lavfi", "-i", f"color=c=white:s={w}x{h}:d={duration}"]
    filter_chain = []
    last_label = "0:v"
    input_idx = 1

    for scene in composed["scenes"]:
        for element in scene["elements"]:
            if not os.path.exists(element["file_path"]):
                continue
            inputs += ["-loop", "1", "-t", str(duration), "-i", element["file_path"]]
            scaled_label = f"s{input_idx}"
            filter_chain.append(f"[{input_idx}:v]scale={element['w']}:{element['h']}[{scaled_label}]")
            out_label = f"v{input_idx}"
            appear = element["appear_time"]
            disappear = scene["end"]
            filter_chain.append(
                f"[{last_label}][{scaled_label}]overlay=x={element['x']}:y={element['y']}:"
                f"enable='between(t,{appear},{disappear})'[{out_label}]"
            )
            last_label = out_label
            input_idx += 1

    if srt_path and os.path.exists(srt_path):
        escaped = srt_path.replace(":", r"\:")
        filter_chain.append(
            f"[{last_label}]subtitles='{escaped}':force_style="
            "'FontSize=20,PrimaryColour=&H111111&,OutlineColour=&HFFFFFF&,BorderStyle=3'[vout]"
        )
        last_label = "vout"

    inputs += ["-i", audio_path]
    audio_input_idx = input_idx

    filter_complex = ";".join(filter_chain) if filter_chain else None

    cmd = ["ffmpeg", "-y", *inputs]
    if filter_complex:
        cmd += ["-filter_complex", filter_complex, "-map", f"[{last_label}]"]
    else:
        cmd += ["-map", "0:v"]
    cmd += ["-map", f"{audio_input_idx}:a", "-shortest", "-c:v", "libx264", "-pix_fmt", "yuv420p",
            "-c:a", "aac", output_path]

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg render failed:\n{result.stderr[-4000:]}")
    return output_path
