"""
Render Pipeline — Static Template Edition (Week 3).

Workflow:
1. Ingest ScenePlan JSON (or dict from pipeline orchestrator).
2. Assign templates via rule-based mapper.
3. Ingest asset metadata from Asset Service (if available).
4. Resolve / generate Iconify SVG asset URLs for all visual cues.
5. Enrich scene cues with asset URLs + trigger times.
6. Validate enriched plan against ScenePlan Pydantic schema.
7. For each scene: load matching template, populate via html_code_writer agent.
8. Assemble all fragments into one merged HTML file with shared CSS/JS/player.
"""

import json
import sys
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

THIS_DIR = Path(__file__).resolve().parent
TEMPLATES_DIR = THIS_DIR / "templates"

# Make backend importable reliably
_repo_root = THIS_DIR
while _repo_root.name != "ai-video-generation-app" and _repo_root.parent != _repo_root:
    _repo_root = _repo_root.parent

if str(_repo_root) not in sys.path:
    sys.path.insert(0, str(_repo_root))

from backend.app.schemas.scene import ScenePlan
from backend.app.pipeline.render.template_mapper import assign_templates
from backend.app.pipeline.render.html_code_writer import populate_scene_template
from backend.app.pipeline.render.asset_agent import generate_assets_with_crewai


# ─── HELPERS ──────────────────────────────────────────────────────────────────

def _estimate_speech_ms(text: str) -> int:
    """Estimate TTS duration from word count. ~150 wpm = 400ms per word."""
    words = len(text.split()) if text else 0
    return words * 400 + 2000  # 2s buffer


def _detect_accent_colors(title: str) -> tuple:
    """Pick accent colors based on topic title, for the shared CSS vars."""
    tl = title.lower()
    if "docker" in tl:
        return "#0ea5e9", "#06b6d4", "#38bdf8"
    elif "langchain" in tl:
        return "#22c55e", "#eab308", "#4ade80"
    elif "vpn" in tl or "security" in tl:
        return "#10b981", "#14b8a6", "#6ee7b7"
    elif "ai" in tl or "machine" in tl or "learn" in tl:
        return "#8b5cf6", "#ec4899", "#a78bfa"
    else:
        return "#3b82f6", "#8b5cf6", "#60a5fa"


def _get_fallback_icon_url(desc_text: str) -> str:
    """Intelligent Iconify SVG URL resolver for missing assets."""
    d = (desc_text or "").lower()
    if "docker" in d or "whale" in d:
        return "https://api.iconify.design/logos/docker-icon.svg"
    elif "langchain" in d:
        return "https://api.iconify.design/logos/langchain-icon.svg"
    elif "dev" in d or "laptop" in d or "machine" in d or "device" in d:
        return "https://api.iconify.design/lucide/laptop.svg?color=%230ea5e9"
    elif "beam" in d or "risk" in d or "path" in d or "broken" in d or "hacker" in d:
        return "https://api.iconify.design/lucide/shield-alert.svg?color=%23ef4444"
    elif "os" in d or "mismatch" in d or "diff" in d:
        return "https://api.iconify.design/lucide/file-warning.svg?color=%23f59e0b"
    elif "dep" in d or "hell" in d or "conflict" in d:
        return "https://api.iconify.design/lucide/boxes.svg?color=%23ef4444"
    elif "vm" in d or "heavy" in d or "overhead" in d:
        return "https://api.iconify.design/lucide/server-off.svg?color=%23dc2626"
    elif "app" in d or "source" in d or "code" in d:
        return "https://api.iconify.design/lucide/code-2.svg?color=%233b82f6"
    elif "engine" in d or "container" in d or "unit" in d:
        return "https://api.iconify.design/lucide/box.svg?color=%2306b6d4"
    elif "cloud" in d or "server" in d or "host" in d or "prod" in d:
        return "https://api.iconify.design/lucide/cloud.svg?color=%230ea5e9"
    elif "file" in d or "node" in d or "build" in d:
        return "https://api.iconify.design/lucide/file-code.svg?color=%238b5cf6"
    elif "image" in d or "layer" in d or "stack" in d:
        return "https://api.iconify.design/lucide/layers.svg?color=%233b82f6"
    elif "run" in d or "instant" in d or "fast" in d:
        return "https://api.iconify.design/lucide/zap.svg?color=%23f59e0b"
    elif "iso" in d or "guard" in d or "lock" in d or "sec" in d:
        return "https://api.iconify.design/lucide/lock.svg?color=%2310b981"
    elif "waste" in d or "light" in d or "save" in d or "footprint" in d:
        return "https://api.iconify.design/lucide/feather.svg?color=%2306b6d4"
    elif "check" in d or "ship" in d or "recap" in d or "deploy" in d:
        return "https://api.iconify.design/lucide/check-circle-2.svg?color=%2322c55e"
    elif "blueprint" in d or "recipe" in d or "plan" in d:
        return "https://api.iconify.design/lucide/clipboard-list.svg?color=%233b82f6"
    elif "meal" in d or "eat" in d or "food" in d:
        return "https://api.iconify.design/lucide/utensils.svg?color=%23f59e0b"
    elif "map" in d or "world" in d or "globe" in d:
        return "https://api.iconify.design/lucide/globe.svg?color=%230ea5e9"
    else:
        return "https://api.iconify.design/lucide/sparkles.svg?color=%230ea5e9"


_TEMPLATE_MAP = {
    "intro": "template_intro.html",
    "content_a": "template_content_a.html",
    "content_b": "template_content_b.html",
    "outro": "template_outro.html",
}


def _load_template(template_name: str) -> str:
    """Load a raw template file as a string."""
    filename = _TEMPLATE_MAP.get(template_name, "template_content_a.html")
    path = TEMPLATES_DIR / filename
    if not path.exists():
        raise FileNotFoundError(f"Template file not found: {path}")
    return path.read_text(encoding="utf-8")


# ─── SHARED CSS ───────────────────────────────────────────────────────────────

def _build_shared_css(c1: str, c2: str, c3: str) -> str:
    """All shared CSS — static background, intro layout, glassmorphism, hero layouts, animations."""
    return f"""
:root{{
  --c1:{c1}; --c2:{c2}; --c3:{c3};
  --bg:#f8fafc; --paper-bg:#f2efe9; --text:#0f172a; --muted:#475569;
  --glass-bg:rgba(255,255,255,0.7); --glass-border:rgba(255,255,255,0.9);
  --shadow:0 12px 40px rgba(0,0,0,0.06);
}}
*{{box-sizing:border-box;margin:0;padding:0;}}
html,body{{height:100%;width:100%;background:var(--bg);font-family:"Plus Jakarta Sans",-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;color:var(--text);overflow:hidden;}}

/* ─── Static Clean Background ─── */
#page{{width:100vw;height:100vh;position:relative;}}
#video-frame{{
  position:relative;width:100vw;height:100vh;
  background:
    radial-gradient(circle at 15% 20%, rgba(14,165,233,0.05) 0%, transparent 40%),
    radial-gradient(circle at 85% 80%, rgba(6,182,212,0.06) 0%, transparent 45%),
    radial-gradient(circle at 50% 50%, rgba(248,250,252,1) 0%, #f1f5f9 100%);
  overflow:hidden;
}}

/* ─── Entry & Motion Keyframe Animations ─── */
@keyframes fadeUp{{from{{opacity:0;transform:translateY(16px)}}to{{opacity:1;transform:translateY(0)}}}}
@keyframes fadeInDown{{from{{opacity:0;transform:translateY(-30px)}}to{{opacity:1;transform:translateY(0)}}}}
@keyframes popIn{{0%{{opacity:0;transform:scale(0.6)}}70%{{transform:scale(1.05)}}100%{{opacity:1;transform:scale(1)}}}}
@keyframes scaleIn{{from{{opacity:0;transform:scale(0.85)}}to{{opacity:1;transform:scale(1)}}}}
@keyframes slideInLeft{{from{{opacity:0;transform:translateX(-40px)}}to{{opacity:1;transform:translateX(0)}}}}
@keyframes slideInRight{{from{{opacity:0;transform:translateX(40px)}}to{{opacity:1;transform:translateX(0)}}}}
@keyframes float{{0%,100%{{transform:translateY(0) rotate(0deg)}}50%{{transform:translateY(-10px) rotate(-1deg)}}}}
@keyframes floatReverse{{0%,100%{{transform:translateY(0) rotate(0deg)}}50%{{transform:translateY(10px) rotate(1deg)}}}}
@keyframes pulseSoft{{0%,100%{{transform:scale(1)}}50%{{transform:scale(1.08)}}}}
@keyframes shimmer{{0%{{background-position:-200% 0}}100%{{background-position:200% 0}}}}

.cue-asset {{ filter: drop-shadow(0 8px 16px rgba(0,0,0,0.08)); transition: transform 0.3s ease; }}
.cue-asset:hover {{ transform: scale(1.08); }}
.float {{ animation: float 5s ease-in-out infinite; }}
.float-reverse {{ animation: floatReverse 6s ease-in-out infinite; }}
.pulse-soft {{ animation: pulseSoft 3.5s ease-in-out infinite; }}

/* ─── Frosty Glassmorphism Panels ─── */
.glass-panel{{
  background:var(--glass-bg);backdrop-filter:blur(20px);-webkit-backdrop-filter:blur(20px);
  border:1px solid var(--glass-border);box-shadow:var(--shadow);border-radius:20px;
  transition:transform 0.3s ease, box-shadow 0.3s ease;
}}
.glass-panel:hover{{transform:translateY(-4px);box-shadow:0 18px 40px rgba(0,0,0,0.1);}}

/* ─── Progress Dots ─── */
#progress{{position:absolute;top:20px;left:50%;transform:translateX(-50%);display:flex;gap:10px;z-index:50;}}
#progress .dot{{width:9px;height:9px;border-radius:50%;background:#cbd5e1;cursor:pointer;transition:all .3s ease;}}
#progress .dot.done{{background:var(--c1);}}
#progress .dot.current{{background:var(--c1);transform:scale(1.6);box-shadow:0 0 10px var(--c1);}}

/* ─── Scene Base Container ─── */
.scene{{
  position:absolute;inset:0;display:flex;flex-direction:column;align-items:center;justify-content:center;
  opacity:0;pointer-events:none;transition:opacity .6s ease;padding:50px 6vw 100px;text-align:center;z-index:1;
}}
.scene.active{{opacity:1;pointer-events:auto;}}
.scene-title{{font-size:clamp(24px,3.5vw,40px);font-weight:800;color:var(--text);margin-bottom:20px;line-height:1.2;}}
.scene-title span{{
  background:linear-gradient(135deg,var(--c1),var(--c2));
  -webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;
}}

/* ─── Narration / Transcript Text (Hidden from Visual Display) ─── */
.scene-narration{{
  display:none !important;
}}
.scene-narration.centered{{display:none !important;}}


/* ─── SCENE 0 : INTRO ─── */
.scene[data-template="intro"]{{
  align-items:stretch;justify-content:flex-start;text-align:left;padding:0;
  background:
    radial-gradient(circle at 20% 30%, rgba(0,0,0,0.02) 0%, transparent 45%),
    radial-gradient(circle at 80% 70%, rgba(0,0,0,0.025) 0%, transparent 50%),
    var(--paper-bg);
}}
.paper-inner{{
  position:relative;width:100%;height:100%;padding:4% 6%;
  display:flex;flex-direction:column;justify-content:space-between;
}}
.logo-row{{
  display:flex;align-items:center;gap:10px;
  opacity:0;animation:fadeUp .5s forwards;animation-delay:.1s;
}}
.logo-row svg{{width:34px;height:34px;flex-shrink:0;}}
.logo-row .logo-text{{
  font-size:clamp(18px,2.4vw,26px);font-weight:800;color:#111827;letter-spacing:-.3px;
}}
.middle-row{{
  display:flex;align-items:center;justify-content:space-between;gap:20px;
  flex:1;position:relative;
}}
.left-title{{
  font-size:clamp(28px,4.5vw,54px);font-weight:800;line-height:1.15;color:#111827;
  max-width:52%;opacity:0;animation:fadeUp .6s forwards;animation-delay:.4s;
}}
.cloud-wrap{{
  position:relative;width:44%;max-width:340px;
  opacity:0;animation:popIn .6s cubic-bezier(.34,1.56,.64,1) forwards;animation-delay:.8s;
}}
.cloud-wrap svg{{width:100%;height:auto;overflow:visible;}}
.cloud-content{{
  position:absolute;inset:0;
  display:flex;flex-direction:column;align-items:center;justify-content:center;gap:4px;
}}
.cloud-content .emoji{{font-size:clamp(30px,4.5vw,48px);}}
.cloud-content .word{{
  font-size:clamp(18px,3vw,30px);font-weight:800;color:#111827;letter-spacing:-.5px;
}}
.bottom-row{{
  display:flex;align-items:flex-end;gap:14px;padding-bottom:1%;
  opacity:0;animation:fadeUp .6s forwards;animation-delay:1.2s;
}}
.bottom-row svg{{width:150px;height:70px;flex-shrink:0;}}
.bottom-label{{
  font-size:clamp(16px,2.2vw,26px);font-weight:600;color:#111827;transform:translateY(-6px);
}}

/* ─── Hero Layout (Content A — split screen) ─── */
.hero-layout{{
  display:flex;align-items:center;justify-content:center;gap:clamp(24px,4vw,60px);
  width:100%;max-width:1000px;flex:1;
}}
.hero-image-wrap{{
  flex-shrink:0;
  opacity:0;animation:slideInLeft .6s cubic-bezier(0.34,1.56,0.64,1) forwards;animation-delay:.3s;
}}
.hero-img{{
  width:clamp(180px,22vw,300px);height:clamp(180px,22vw,300px);
  object-fit:contain;border-radius:24px;
}}
.hero-text-wrap{{
  flex:1;text-align:left;
  opacity:0;animation:slideInRight .6s ease forwards;animation-delay:.5s;
}}
.hero-text-wrap .scene-narration{{
  text-align:left;opacity:1;animation:none;
}}

/* ─── Centered Hero Layout (Content B) ─── */
.centered-hero{{
  display:flex;flex-direction:column;align-items:center;justify-content:center;gap:20px;
  width:100%;max-width:800px;flex:1;
}}
.centered-hero-img-wrap{{
  opacity:0;animation:popIn .6s cubic-bezier(.34,1.56,.64,1) forwards;animation-delay:.3s;
}}
.centered-hero-img{{
  width:clamp(160px,20vw,280px);height:clamp(160px,20vw,280px);
  object-fit:contain;border-radius:24px;
}}

/* ─── Supporting Icons Row ─── */
.supporting-icons{{
  display:flex;flex-wrap:wrap;gap:14px;margin-top:20px;
}}
.supporting-icons.centered{{justify-content:center;}}
.supporting-icon{{
  display:flex;align-items:center;gap:10px;padding:10px 16px;
  opacity:0;
}}
.scene.active .supporting-icon{{
  animation:fadeUp .4s cubic-bezier(0.34,1.56,0.64,1) both;
}}
.supporting-icon span{{font-size:13px;font-weight:600;color:var(--text);}}

/* ─── Base Hidden State for Unactive Cues ─── */
.scene .risk-card, .scene .endpoint-icon, .scene .flow-node, .scene .flow-arrow, .scene .feature-card, .scene .check-item, .scene .final-badge {{
  opacity: 0;
}}

/* ─── Content A: Risk Grid (legacy fallback) ─── */
.risk-grid{{display:flex;flex-wrap:wrap;gap:20px;justify-content:center;max-width:850px;}}
.risk-card{{
  display:flex;align-items:center;gap:18px;padding:20px 24px;min-width:240px;flex:1;
}}
.scene.active .risk-card{{
  animation:slideInLeft .45s cubic-bezier(0.34,1.56,0.64,1) both;
}}
.risk-label{{font-size:16px;font-weight:700;color:var(--text);text-align:left;}}

/* ─── Content A: Tunnel & Flow ─── */
.tunnel-diagram{{display:flex;align-items:center;justify-content:center;gap:30px;width:100%;max-width:900px;}}
.endpoint-icon{{display:flex;flex-direction:column;align-items:center;gap:12px;}}
.scene.active .endpoint-icon{{
  animation:scaleIn .45s cubic-bezier(0.34,1.56,0.64,1) both;
}}
.endpoint-icon span{{font-size:15px;font-weight:700;color:var(--text);}}

.flow-container{{display:flex;align-items:center;justify-content:center;gap:12px;flex-wrap:wrap;max-width:900px;}}
.flow-node{{display:flex;flex-direction:column;align-items:center;gap:12px;padding:22px;width:180px;}}
.scene.active .flow-node{{
  animation:scaleIn .45s cubic-bezier(0.34,1.56,0.64,1) both;
}}
.flow-node span{{font-size:15px;font-weight:700;color:var(--text);text-align:center;}}
.scene.active .flow-arrow{{
  animation:fadeUp .35s ease both;
}}

/* ─── Content B: Card Grid (legacy fallback) ─── */
.card-grid{{display:flex;gap:22px;justify-content:center;flex-wrap:wrap;max-width:900px;}}
.feature-card{{width:220px;padding:28px 22px;text-align:center;}}
.scene.active .feature-card{{
  animation:fadeUp .45s cubic-bezier(0.34,1.56,0.64,1) both;
}}
.feature-card h3{{font-size:16px;font-weight:700;color:var(--text);margin-top:14px;}}

/* ─── Outro: Checklist ─── */
.checklist{{display:flex;flex-direction:column;gap:14px;align-items:flex-start;margin-bottom:24px;}}
.check-item{{display:flex;align-items:center;gap:12px;}}
.scene.active .check-item{{
  animation:fadeUp .4s ease both;
}}
.check-circle{{
  width:24px;height:24px;border-radius:50%;background:#16a34a;
  display:flex;align-items:center;justify-content:center;flex-shrink:0;
}}
.check-circle svg{{width:14px;height:14px;}}
.check-item span{{font-size:16px;color:var(--text);font-weight:600;}}
.final-badge{{
  padding:12px 32px;border-radius:30px;
  background:linear-gradient(90deg,var(--c1),var(--c2));
  color:#fff;font-weight:700;font-size:clamp(15px,2vw,19px);
  box-shadow:0 10px 25px rgba(14,165,233,0.3);
}}
.scene.active .final-badge{{
  animation:fadeUp .5s ease both;animation-delay:1.2s;
}}

/* ─── Subtitle / Transcript Bar (Hidden) ─── */
.scene-transcript{{
  display:none !important;
}}
.transcript-title{{display:none;}}
.transcript-text{{display:none;}}

/* ─── Start & Replay Overlays ─── */
#start-overlay{{position:absolute;inset:0;z-index:100;background:rgba(255,255,255,0.92);backdrop-filter:blur(16px);display:flex;flex-direction:column;align-items:center;justify-content:center;gap:18px;}}
#start-overlay h1{{
  font-size:clamp(28px,4.5vw,54px);font-weight:800;text-align:center;
  background:linear-gradient(135deg,var(--c1),var(--c2));
  -webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;
}}
#start-btn{{
  background:linear-gradient(135deg,var(--c1),var(--c2));color:#fff;border:none;padding:16px 42px;border-radius:99px;
  font-size:17px;font-weight:700;cursor:pointer;transition:transform .2s,box-shadow .2s;
  box-shadow:0 8px 24px rgba(14,165,233,0.35);
}}
#start-btn:hover{{transform:scale(1.05);box-shadow:0 14px 40px rgba(14,165,233,0.45);}}
#replay-btn{{display:none;background:var(--bg);border:2px solid var(--c1);color:var(--text);padding:10px 28px;border-radius:99px;font-size:14px;font-weight:700;cursor:pointer;transition:all .2s;}}
#replay-btn:hover{{background:var(--c1);color:#fff;}}
.hidden{{display:none !important;}}
"""


# ─── SHARED JAVASCRIPT (TTS Scene Player — speech-driven transitions) ────────

def _build_shared_js(scenes_data_json: str) -> str:
    """Build the JS block for TTS scene playback with speech-driven transitions."""
    return f"""
(function(){{
  const scenesData = {scenes_data_json};

  let currentIdx = 0, isPlaying = false, stepTimer = null;
  const sceneEls = scenesData.map(s => document.getElementById(s.id));
  const dots = document.querySelectorAll("#progress .dot");
  const subtitleText = document.getElementById("subtitle-text");
  const startOverlay = document.getElementById("start-overlay");
  const startBtn = document.getElementById("start-btn");
  const replayBtn = document.getElementById("replay-btn");
  const synth = window.speechSynthesis;
  let chosenVoice = null;

  function pickVoice(){{
    if(!synth) return;
    try {{
      const voices = synth.getVoices();
      chosenVoice = voices.find(v => v.lang && v.lang.startsWith("en") && /female|Samantha|Zira|Google US/i.test(v.name))
                 || voices.find(v => v.lang && v.lang.startsWith("en"))
                 || voices[0] || null;
    }} catch(e){{}}
  }}
  if(synth){{ pickVoice(); try {{ synth.onvoiceschanged = pickVoice; }} catch(e){{}} }}

  function resetScene(el){{
    if(!el) return;
    el.querySelectorAll("*").forEach(n => {{
      const a = getComputedStyle(n).animationName;
      if(a && a !== "none" && !n.classList.contains("float") && !n.classList.contains("float-reverse") && !n.classList.contains("pulse-soft")){{
        n.style.animation = "none"; void n.offsetWidth; n.style.animation = "";
      }}
    }});
  }}

  function showScene(i){{
    currentIdx = ((i % scenesData.length) + scenesData.length) % scenesData.length;
    sceneEls.forEach((el, idx) => {{
      if(!el) return;
      if(idx === currentIdx){{ resetScene(el); el.classList.add("active"); }}
      else {{ el.classList.remove("active"); }}
    }});
    dots.forEach((d, idx) => {{
      d.classList.toggle("done", idx < currentIdx);
      d.classList.toggle("current", idx === currentIdx);
    }});
  }}
  window.showScene = showScene;

  function speakCurrentScene(){{
    const s = scenesData[currentIdx];
    const minHold = s.holdMs || 8000;
    const isIntro = (s.template === 'intro' || s.template === 'template_intro' || currentIdx === 0);

    return new Promise(resolve => {{
      let speechDone = false;
      let holdDone = false;
      const finish = () => {{
        if(speechDone && holdDone) resolve();
      }};

      // Safety timeout: holdMs + 15s max to prevent infinite hang
      const safetyTimer = setTimeout(() => {{
        speechDone = true; holdDone = true;
        if(synth) try{{ synth.cancel(); }} catch(e){{}}
        resolve();
      }}, minHold + 15000);

      // Minimum display time — always wait at least holdMs
      setTimeout(() => {{
        holdDone = true;
        finish();
      }}, minHold);

      // TTS narration — intro scene is completely silent (no speaking)
      if(synth && s.narration && !isIntro){{
        try{{
          synth.cancel();
          const utter = new SpeechSynthesisUtterance(s.narration);
          if(chosenVoice) utter.voice = chosenVoice;
          utter.rate = 0.95;
          utter.onend = () => {{
            clearTimeout(safetyTimer);
            speechDone = true;
            finish();
          }};
          utter.onerror = () => {{
            clearTimeout(safetyTimer);
            speechDone = true;
            finish();
          }};
          synth.speak(utter);
        }} catch(err){{
          clearTimeout(safetyTimer);
          speechDone = true;
          finish();
        }}
      }} else {{
        // Intro scene or no TTS available — silent hold
        speechDone = true;
        finish();
      }}
    }});
  }}

  async function stepSequence(){{
    if(!isPlaying) return;
    showScene(currentIdx);
    await speakCurrentScene();
    if(!isPlaying) return;
    if(currentIdx < scenesData.length - 1){{
      currentIdx++;
      stepTimer = setTimeout(stepSequence, 600);
    }} else {{
      isPlaying = false;
      replayBtn.style.display = "inline-flex";
      startOverlay.classList.remove("hidden");
      startBtn.style.display = "none";
    }}
  }}

  function startAutoPlay(f){{ isPlaying = true; currentIdx = f||0; if(stepTimer) clearTimeout(stepTimer); stepSequence(); }}
  function stopAutoPlay(){{ isPlaying = false; if(stepTimer) clearTimeout(stepTimer); if(synth) try{{ synth.cancel(); }} catch(e){{}} }}

  dots.forEach((dot, idx) => {{ dot.addEventListener("click", () => {{ stopAutoPlay(); startOverlay.classList.add("hidden"); showScene(idx); }}); }});
  startBtn.addEventListener("click", () => {{ startOverlay.classList.add("hidden"); startAutoPlay(0); }});
  replayBtn.addEventListener("click", () => {{ startOverlay.classList.add("hidden"); startAutoPlay(0); }});
  showScene(0);
}})();
"""


# ─── MAIN FUNCTION ────────────────────────────────────────────────────────────

def generate_video_html(scene_plan: dict, asset_data: dict | None = None) -> str:
    """
    Main entrypoint: turn a ScenePlan dict into a single merged HTML file.

    Parameters
    ----------
    scene_plan : dict
        A ScenePlan dictionary with ``scenes`` list.
    asset_data : dict | None
        Optional asset data from Asset Service (``{"assets": [...]}"`).

    Returns
    -------
    str
        A complete, self-contained HTML document string.
    """
    # 0. Deep copy & normalize
    plan = json.loads(json.dumps(scene_plan))
    for scene in plan.get("scenes", []):
        if "visual_cues" not in scene and "visual_elements" in scene:
            scene["visual_cues"] = scene["visual_elements"]
        if "visual_cues" not in scene:
            scene["visual_cues"] = []

    # 1. Assign templates via rule-based mapper
    print("[PIPELINE] Assigning templates to scenes...")
    assign_templates(plan)
    for s in plan.get("scenes", []):
        print(f"  scene {s['scene_id']:>3}  hint={s.get('layout_hint',''):20s}  -> template={s['template']}")

    # 2. Build asset lookup from asset_data if provided
    asset_lookup = {}
    if asset_data and isinstance(asset_data, dict):
        assets_list = asset_data.get("assets", [])
        for item in assets_list:
            if isinstance(item, dict):
                if "asset_id" in item and "url" in item:
                    asset_lookup[item["asset_id"]] = item["url"]
                if "cue_id" in item and "url" in item and item["cue_id"]:
                    asset_lookup[item["cue_id"]] = item["url"]

    # 3. Generate fallback Iconify assets for missing cues via CrewAI agent if available
    generated_assets = {}
    try:
        generated_assets = generate_assets_with_crewai(plan)
    except Exception as e:
        print(f"[PIPELINE WARNING] Iconify asset agent skipped/failed: {e}")

    # 4. Enrich cues with asset URLs + progressive trigger times
    for scene in plan.get("scenes", []):
        cues = scene.get("visual_cues", [])
        num_cues = len(cues)
        scene_duration = (scene.get("hold_ms") or 8000) / 1000.0

        for idx, cue in enumerate(cues):
            aid = cue.get("asset_id")
            cid = cue.get("cue_id")
            desc = cue.get("description") or cue.get("content") or cue.get("cue_id") or ""

            # Check for existing image URL on cue object
            existing_url = cue.get("asset_url") or cue.get("url") or cue.get("image_url")
            
            if existing_url and "placehold.co" not in str(existing_url):
                cue["asset_url"] = str(existing_url)
            elif aid and aid in asset_lookup:
                cue["asset_url"] = asset_lookup[aid]
            elif cid and cid in asset_lookup:
                cue["asset_url"] = asset_lookup[cid]
            elif aid and aid in generated_assets:
                cue["asset_url"] = generated_assets[aid]
            else:
                cue["asset_url"] = _get_fallback_icon_url(f"{aid} {cid} {desc}")

            # Progressive trigger time
            if "trigger_time_seconds" not in cue or cue["trigger_time_seconds"] is None or cue["trigger_time_seconds"] == 0:
                if num_cues <= 1:
                    cue["trigger_time_seconds"] = 0.15
                else:
                    spacing = min(1.0, max(0.4, (scene_duration * 0.45) / (num_cues - 1)))
                    cue["trigger_time_seconds"] = round(0.15 + idx * spacing, 2)

    # 4b. Auto-calculate hold_ms from narration word count
    for scene in plan.get("scenes", []):
        narration = scene.get("text", "")
        estimated_ms = _estimate_speech_ms(narration)
        current_hold = scene.get("hold_ms") or 6000
        scene["hold_ms"] = max(current_hold, estimated_ms)

    # 5. Validate against Pydantic schema
    try:
        print("[PIPELINE] Validating enriched plan against Pydantic ScenePlan schema...")
        ScenePlan(**plan)
        print("[OK] Pydantic validation successful!")
    except Exception as err:
        print(f"[PIPELINE WARNING] Pydantic validation warning: {err}")

    # 6. Populate each scene's template
    print("[PIPELINE] Populating scene templates...")
    scene_fragments = []
    for scene in plan.get("scenes", []):
        template_name = scene.get("template", "content_a")
        template_html = _load_template(template_name)

        populated = populate_scene_template(
            scene=scene,
            template_html=template_html,
            plan_context=plan,
            use_llm=True,
        )
        scene_fragments.append((scene, populated))

    # 7. Assemble the final merged HTML
    print("[PIPELINE] Assembling final merged HTML document...")
    title = plan.get("title", "AI Explainer Video")
    c1, c2, c3 = _detect_accent_colors(title)

    # Build progress dots
    dots_html = "\n".join(
        f'      <div class="dot{" current" if i == 0 else ""}" data-i="{i}"></div>'
        for i in range(len(scene_fragments))
    )

    # Build scene divs
    scenes_html_parts = []
    for i, (scene, fragment) in enumerate(scene_fragments):
        active = " active" if i == 0 else ""
        sid = scene.get("scene_id", str(i))
        hint = scene.get("layout_hint", "")
        template_type = scene.get("template", "content_a")
        scenes_html_parts.append(
            f'    <div class="scene{active}" id="scene-{sid}" data-layout-hint="{hint}" data-template="{template_type}">\n'
            f'{fragment}\n'
            f'    </div>'
        )
    scenes_html = "\n\n".join(scenes_html_parts)

    # Build JS scene data array
    js_scenes = []
    for scene, _ in scene_fragments:
        js_scenes.append({
            "id": f"scene-{scene.get('scene_id', '')}",
            "narration": scene.get("text", ""),
            "subtitle": scene.get("subtitle") or scene.get("text", ""),
            "holdMs": scene.get("hold_ms") or 8000,
        })
    scenes_data_json = json.dumps(js_scenes, ensure_ascii=False)

    css = _build_shared_css(c1, c2, c3)
    js = _build_shared_js(scenes_data_json)

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title} — Explainer Video</title>
<link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap" rel="stylesheet">
<style>
{css}
</style>
</head>
<body>

<div id="page">
  <div id="video-frame">

    <div id="progress">
{dots_html}
    </div>

{scenes_html}



    <div id="start-overlay">
      <h1>{title}</h1>
      <button id="start-btn">&#9654; &nbsp;Start Presentation</button>
      <button id="replay-btn">&#8635; &nbsp;Replay</button>
    </div>

  </div>
</div>

<script>
{js}
</script>
</body>
</html>"""

    return html


# Alias for backward compatibility
render_custom_template = generate_video_html


# ─── STANDALONE CLI ───────────────────────────────────────────────────────────

if __name__ == "__main__":
    target_json = sys.argv[1] if len(sys.argv) > 1 else "docker_scene_plan.json"
    json_path = Path(target_json)
    if not json_path.is_absolute():
        json_file_path = THIS_DIR / target_json
        if not json_file_path.exists():
            json_file_path = Path.cwd() / target_json
    else:
        json_file_path = json_path

    if not json_file_path.exists():
        print(f"[ERROR] Specified JSON file does not exist: {json_file_path}")
        sys.exit(1)

    print(f"=== Running Static Template Render Pipeline for: {target_json} ===")

    with open(json_file_path, "r", encoding="utf-8") as f:
        plan_dict = json.load(f)

    rendered_html = generate_video_html(plan_dict)

    prefix = json_file_path.stem.replace("_scene_plan", "")
    out_path = THIS_DIR / f"{prefix}_output.html"
    out_path.write_text(rendered_html, encoding="utf-8")

    print(f"\n[SUCCESS] Wrote output file:")
    print(f"  - Output:  {out_path.resolve()}")
    print("\nOpen the HTML file in your browser to watch the narrated video!")
