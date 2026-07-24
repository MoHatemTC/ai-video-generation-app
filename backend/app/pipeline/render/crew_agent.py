"""
CrewAI Agent for Generating Customized Jinja2 HTML Video Templates.

Uses Google Gemini API via CrewAI LLM wrapper to inspect any ScenePlan JSON
and produce a topic-tailored Jinja2 template with:
  - Clean white-background premium UI with colorful accents
  - Google Fonts typography
  - Rich inline SVG illustrations (via provided HTTPS asset URLs)
  - CSS @keyframes micro-animations with cubic-bezier easing
  - Web Speech API TTS narration — scene waits until narration finishes
  - Subtitle bar & interactive scene navigation
"""

import os
import json
from pathlib import Path
from dotenv import load_dotenv

THIS_DIR = Path(__file__).resolve().parent
load_dotenv(THIS_DIR / ".env")

try:
    from crewai import Agent, Task, Crew, Process, LLM
    HAS_CREWAI = True
except ImportError:
    HAS_CREWAI = False


def normalize_model_name(raw_name: str) -> str:
    """Normalize user configured model name for CrewAI Google Gemini integration."""
    if not raw_name:
        return "gemini/gemini-3.5-flash"
    clean = raw_name.strip()
    if clean.startswith("gemini/") or clean.startswith("google/"):
        return clean
    return f"gemini/{clean.lower().replace(' ', '-')}"

# ─── PROMPT ────────────────────────────────────────────────────────────────────

def _build_agent_prompt(scene_plan_dict: dict) -> str:
    title = scene_plan_dict.get("title", "Explainer Video")
    duration = scene_plan_dict.get("total_duration_seconds", 60.0)

    scenes_json = json.dumps(
        scene_plan_dict.get("scenes", []),
        indent=2,
        ensure_ascii=False
    )

    layout_hints = sorted({
        s.get("layout_hint", "generic")
        for s in scene_plan_dict.get("scenes", [])
    })

    return f"""
You are an Award-Winning Motion Graphics Engineer, HTML5 Animation Architect, and Jinja2 Template Expert.

Your job is to transform a ScenePlan JSON into a COMPLETE standalone HTML5 animated video.

=========================================================
TRANSCRIPT
=========================================================

VERY IMPORTANT.

At the bottom of EVERY scene render

<div class="scene-transcript">

<div class="transcript-title">
Transcript
</div>

<div class="transcript-text">

{{{{ scene.text }}}}

</div>

</div>

The transcript must always be visible.

Never hide it.

Never replace it with subtitles.

Never move it into JavaScript.

Never omit it.

=========================================================
VISUAL STYLE: FROSTY LIGHT-MODE GLASSMORPHISM
=========================================================

The output MUST be visually stunning, using a clean "Frosty Light-Mode Glassmorphism" style:
- Backgrounds must be extremely light/clean with animated soft gradient blobs.
- ALL UI elements, cards, and containers MUST use a glass effect: 
  `background: rgba(255, 255, 255, 0.6); backdrop-filter: blur(24px); border: 1px solid rgba(255, 255, 255, 0.8);` (Use the `.glass-panel` class).
- Text must be dark (`#0f172a`) and highly legible.
- Deep, soft shadows (`box-shadow: 0 12px 40px rgba(0,0,0,0.06)`).
- Staggered entrances: Apply `style="animation-delay: {{{{ loop.index0 * 0.2 }}}}s"` to ALL looping elements.

You are explicitly FORBIDDEN from writing generic, boring CSS.

=========================================================
ASSET ANIMATIONS (MANDATORY)
=========================================================

EVERY SINGLE ASSET (image/icon) MUST ANIMATE CONTINUOUSLY.
When you output an `<img src="{{{{ cue.asset_url | safe }}}}" ... />`, it MUST have animation classes!
Use `class="cue-asset float"`, `class="cue-asset float-reverse"`, or `class="cue-asset pulse-soft"`.
DO NOT output plain `<img>` tags without animations.

=========================================================
LAYOUT CONTRACT
=========================================================

TITLE:
{title}

TOTAL DURATION:
{duration}

LAYOUTS USED:
{", ".join(layout_hints)}

SCENE PLAN JSON:

{scenes_json}

=========================================================
CRITICAL RULE 1: THE JSON IS THE ABSOLUTE SOURCE OF TRUTH
=========================================================
Never invent content, never summarize, never omit scenes, and never hardcode text.
EVERYTHING shown on screen MUST come from the JSON loop:
{{% for scene in plan.scenes %}}
  scene.text
  scene.subtitle
  {{% for cue in scene.visual_cues %}}
    cue.description
    cue.content

=========================================================
CRITICAL RULE 2: VISUAL CUES & ASSETS (NO CSS ART)
=========================================================
DO NOT generate raw SVG code or CSS shapes for visual cues! 
The backend has an Asset Agent that maps every visual cue to a high-quality HTTPS icon/image URL (e.g., Iconify APIs).
You MUST render visual assets strictly using the provided URL WITH animation classes:

<img src="{{{{ cue.asset_url | safe }}}}" alt="{{{{ cue.description }}}}" class="cue-asset float" />

=========================================================
CRITICAL RULE 3: TIMING & SCENE TRANSITIONS
=========================================================
Scenes MUST ONLY transition when the audio transcript (Web Speech TTS) is 100% finished playing.
The Base Template provided to you handles this perfectly via JavaScript (`speechSynthesis.onend`).
DO NOT invent your own JavaScript player. 
You MUST KEEP the `<script>` block at the bottom of the document EXACTLY as it appears in the Base Template. 

=========================================================
OUTPUT
=========================================================
Return ONLY raw HTML/Jinja2 code. 
Do NOT use markdown code blocks (```html).
Do NOT write comments explaining your changes.
Do NOT omit code. Return the entire, instantly-renderable HTML document.
"""

# ─── MAIN GENERATION ───────────────────────────────────────────────────────────

def generate_template_with_crewai(scene_plan_dict: dict) -> str:
    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not api_key or api_key.startswith("your_") or "key_here" in api_key:
        print("[NOTICE] No valid GEMINI_API_KEY set in .env. Using smart fallback template.")
        return generate_fallback_custom_template(scene_plan_dict)

    if not HAS_CREWAI:
        print("[NOTICE] crewai not installed. Using smart fallback template.")
        return generate_fallback_custom_template(scene_plan_dict)

    raw_model = os.getenv("MODEL_NAME", "gemini/gemini-3.5-flash")
    model_name = normalize_model_name(raw_model)
    print(f"[AGENT] Initializing CrewAI with Gemini LLM ({model_name})...")

    try:
        llm = LLM(model=model_name, api_key=api_key, temperature=0.1)
        architect = Agent(
            role="Senior Motion Graphics Engineer & HTML5 Animation Architect",
            goal="Generate flawless, production-ready HTML5 animated videos based on JSON, utilizing provided asset URLs and strict TTS timing.",
            backstory="""
            You are a senior frontend animation engineer specializing in educational motion graphics.
            You build premium animated HTML5 presentations with a Frosty Glassmorphism aesthetic.
            You NEVER hallucinate images or try to draw SVGs manually; you rely purely on the `asset_url` from the backend.
            You ALWAYS apply continuous animation classes (float, float-reverse, pulse-soft) to ALL assets.
            You NEVER break the JavaScript TTS integration because you know scene timing relies entirely on the transcript finishing.
            """,
            verbose=True, allow_delegation=False, llm=llm
        )
        
        prompt = _build_agent_prompt(scene_plan_dict)
        task = Task(
            description=prompt,
            expected_output=f"""
                A COMPLETE standalone HTML/Jinja2 template.
                
                You are provided with `BASE TEMPLATE REFERENCE` below.
                
                CRITICAL INSTRUCTIONS TO GUARANTEE HIGH VISUAL QUALITY:
                1. DO NOT DELETE OR REDUCE THE CSS IN THE `<style>` BLOCK. You MUST keep ALL the CSS rules from BASE TEMPLATE REFERENCE intact.
                2. Apply the `.glass-panel` class to structural containers to keep the frosty light-mode style.
                3. Apply `.cue-asset` AND an animation class (`.float`, `.float-reverse`, or `.pulse-soft`) to ALL `<img ...>` tags to give them continuous motion.
                4. For visual cue images, ALWAYS use `<img src="{{{{ cue.asset_url | safe }}}}" class="cue-asset float" alt="asset" />`. DO NOT hardcode local `assets/...` paths!
                5. Keep the exact JavaScript player script block at the end.
                6. Output ONLY raw HTML (no markdown code blocks, no explanation text).

                =========================================================
                BASE TEMPLATE REFERENCE (USE THIS AS YOUR EXACT FOUNDATION)
                =========================================================
                {generate_fallback_custom_template(scene_plan_dict)}
                """,
            agent=architect
        )
        crew = Crew(agents=[architect], tasks=[task], process=Process.sequential)
        print("[AGENT] CrewAI task execution started...")
        result = crew.kickoff()
        template_code = str(result.raw)

        # Clean up any potential markdown formatting the LLM still tries to apply
        for fence in ["```html", "```jinja2", "```jinja", "```"]:
            if template_code.startswith(fence):
                template_code = template_code[len(fence):]
                break
        if template_code.rstrip().endswith("```"):
            template_code = template_code.rstrip()[:-3]
        template_code = template_code.strip()

        return template_code

    except Exception as err:
        print(f"[AGENT WARNING] Gemini API error: {err}")
        print("[PIPELINE] Falling back to smart template generator.")
        return generate_fallback_custom_template(scene_plan_dict)

# ─── FALLBACK TEMPLATE ─────────────────────────────────────────────────────────

def generate_fallback_custom_template(scene_plan_dict: dict) -> str:
    title = scene_plan_dict.get("title", "AI Explainer Video")
    tl = title.lower()

    # Dynamic accent colors based on title
    if "docker" in tl:
        c1, c2 = "#0ea5e9", "#06b6d4"
    elif "langchain" in tl:
        c1, c2 = "#22c55e", "#eab308"
    elif "vpn" in tl or "security" in tl:
        c1, c2 = "#10b981", "#14b8a6"
    elif "ai" in tl or "machine" in tl or "learn" in tl:
        c1, c2 = "#8b5cf6", "#ec4899"
    else:
        c1, c2 = "#3b82f6", "#8b5cf6"

    return (
        '<!DOCTYPE html>\n'
        '<html lang="en">\n'
        '<head>\n'
        '<meta charset="UTF-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1.0">\n'
        '<title>{{ plan.title }} — Premium AI Video</title>\n'
        '<link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;600;700;800&display=swap" rel="stylesheet">\n'
        '<style>\n'
        '\n'
        ':root{\n'
        '  --c1:' + c1 + '; --c2:' + c2 + ';\n'
        '  --bg:#f1f5f9; --text:#0f172a; --muted:#475569; \n'
        '  --glass-bg:rgba(255,255,255,0.6); --glass-border:rgba(255,255,255,0.9);\n'
        '  --shadow:0 12px 40px rgba(0,0,0,0.06);\n'
        '}\n'
        '*{box-sizing:border-box;margin:0;padding:0;}\n'
        'html,body{height:100%;width:100%;background:var(--bg);font-family:"Plus Jakarta Sans",sans-serif;color:var(--text);overflow:hidden;}\n'
        '\n'
        '\n'
        '@keyframes fadeInUp{from{opacity:0;transform:translateY(40px)}to{opacity:1;transform:translateY(0)}}\n'
        '@keyframes scaleIn{from{opacity:0;transform:scale(0.85)}to{opacity:1;transform:scale(1)}}\n'
        '@keyframes slideInLeft{from{opacity:0;transform:translateX(-50px)}to{opacity:1;transform:translateX(0)}}\n'
        '@keyframes bgBlobFloat{0%,100%{transform:translateY(0) scale(1)}50%{transform:translateY(-30px) scale(1.05)}}\n'
        '@keyframes rotateSlow{from{transform:rotate(0deg)}to{transform:rotate(360deg)}}\n'
        '@keyframes bounceIn{0%{opacity:0;transform:scale(0.3)}50%{transform:scale(1.08)}70%{transform:scale(0.95)}100%{opacity:1;transform:scale(1)}}\n'
        '\n'
        '/* Premium Asset Animations */\n'
        '@keyframes float{0%,100%{transform:translateY(0) rotate(0deg)}50%{transform:translateY(-12px) rotate(3deg)}}\n'
        '@keyframes floatReverse{0%,100%{transform:translateY(0) rotate(0deg)}50%{transform:translateY(12px) rotate(-3deg)}}\n'
        '@keyframes pulseSoft{0%,100%{transform:scale(1)}50%{transform:scale(1.1)}}\n'
        '\n'
        '.bg-blob{position:absolute;border-radius:50%;filter:blur(100px);opacity:0.25;pointer-events:none;z-index:0;mix-blend-mode:multiply;}\n'
        '.bg-blob.b1{width:600px;height:600px;background:var(--c1);top:-150px;right:-150px;animation:bgBlobFloat 12s ease-in-out infinite;}\n'
        '.bg-blob.b2{width:500px;height:500px;background:var(--c2);bottom:-100px;left:-100px;animation:bgBlobFloat 15s ease-in-out infinite 2s;}\n'
        '\n'
        '/* Frosty Light-Mode Glassmorphism */\n'
        '.glass-panel{background:var(--glass-bg);backdrop-filter:blur(24px);-webkit-backdrop-filter:blur(24px);border:1px solid var(--glass-border);box-shadow:var(--shadow);border-radius:24px;}\n'
        '\n'
        '.cue-asset { filter: drop-shadow(0 10px 15px rgba(0,0,0,0.1)); }\n'
        '.float { animation: float 6s ease-in-out infinite; }\n'
        '.float-reverse { animation: floatReverse 7s ease-in-out infinite; }\n'
        '.pulse-soft { animation: pulseSoft 4s ease-in-out infinite alternate; }\n'
        '\n'
        '#page{width:100vw;height:100vh;position:relative;}\n'
        '#video-frame{position:relative;width:100vw;height:100vh;background:var(--bg);overflow:hidden;}\n'
        '\n'
        '\n'
        '#progress{position:absolute;top:24px;left:50%;transform:translateX(-50%);display:flex;gap:12px;z-index:50;}\n'
        '#progress .dot{width:10px;height:10px;border-radius:50%;background:#cbd5e1;cursor:pointer;transition:all .4s cubic-bezier(0.34,1.56,0.64,1);}\n'
        '#progress .dot.done{background:var(--c1);}\n'
        '#progress .dot.current{background:var(--c1);transform:scale(1.8);box-shadow:0 0 10px var(--c1);}\n'
        '\n'
        '.scene{\n'
        '  position:absolute;inset:0;display:flex;flex-direction:column;align-items:center;justify-content:center;\n'
        '  opacity:0;pointer-events:none;transition:opacity .7s ease;padding:60px 6vw 120px;text-align:center;z-index:1;\n'
        '}\n'
        '.scene.active{opacity:1;pointer-events:auto;}\n'
        '.scene-title{font-size:clamp(24px,3.5vw,42px);font-weight:800;color:var(--text);margin-bottom:30px;line-height:1.2;}\n'
        '.scene-title span{background:linear-gradient(135deg,var(--c1),var(--c2));-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;}\n'
        '\n'
        '\n'
        '.hero{display:flex;flex-direction:column;align-items:center;gap:24px;position:relative;}\n'
        '.hero-icon{position:relative;width:140px;height:140px;opacity:0;animation:bounceIn .8s cubic-bezier(0.34,1.56,0.64,1) forwards;animation-delay:.3s;}\n'
        '.hero-icon .orbit{position:absolute;inset:-20px;border:2px dashed var(--c1);border-radius:50%;opacity:0.3;animation:rotateSlow 20s linear infinite;}\n'
        '.hero-icon .orbit-dot{position:absolute;width:12px;height:12px;border-radius:50%;background:var(--c2);top:-6px;left:50%;transform:translateX(-50%);}\n'
        '.hero-title{font-size:clamp(40px,7vw,80px);font-weight:800;background:linear-gradient(135deg,var(--c1),var(--c2));-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;opacity:0;animation:fadeInUp .7s cubic-bezier(0.34,1.56,0.64,1) forwards;animation-delay:.5s;line-height:1.1;}\n'
        '.hero-sub{font-size:clamp(16px,2vw,22px);color:var(--muted);font-weight:500;max-width:600px;opacity:0;animation:fadeInUp .6s forwards;animation-delay:.8s;}\n'
        '\n'
        '.risk-grid{display:flex;flex-wrap:wrap;gap:20px;justify-content:center;max-width:800px;}\n'
        '.risk-card{display:flex;align-items:center;gap:18px;padding:20px 24px;min-width:240px;flex:1;opacity:0;animation:slideInLeft .6s cubic-bezier(0.34,1.56,0.64,1) forwards;transition:transform .3s;}\n'
        '.risk-card:hover{transform:translateY(-5px) scale(1.02);}\n'
        '.risk-label{font-size:16px;font-weight:700;color:var(--text);text-align:left;}\n'
        '\n'
        '.tunnel-diagram{display:flex;align-items:center;justify-content:center;gap:30px;width:100%;max-width:900px;}\n'
        '.endpoint-icon{display:flex;flex-direction:column;align-items:center;gap:14px;opacity:0;animation:scaleIn .6s cubic-bezier(0.34,1.56,0.64,1) forwards;}\n'
        '.endpoint-icon span{font-size:15px;font-weight:700;color:var(--text);}\n'
        '\n'
        '.flow-container{display:flex;align-items:center;justify-content:center;gap:10px;flex-wrap:wrap;max-width:900px;}\n'
        '.flow-node{display:flex;flex-direction:column;align-items:center;gap:14px;padding:24px;width:180px;opacity:0;animation:scaleIn .6s cubic-bezier(0.34,1.56,0.64,1) forwards;transition:transform .3s;}\n'
        '.flow-node:hover{transform:translateY(-5px) scale(1.05);}\n'
        '.flow-node span{font-size:15px;font-weight:700;color:var(--text);text-align:center;}\n'
        '.flow-arrow{opacity:0;animation:fadeInUp .4s forwards;}\n'
        '\n'
        '.card-grid{display:flex;gap:24px;justify-content:center;flex-wrap:wrap;max-width:900px;}\n'
        '.feature-card{width:220px;padding:30px 24px;text-align:center;opacity:0;animation:fadeInUp .6s cubic-bezier(0.34,1.56,0.64,1) forwards;transition:transform .3s;}\n'
        '.feature-card:hover{transform:translateY(-8px);}\n'
        '.feature-card h3{font-size:17px;font-weight:700;color:var(--text);margin-top:16px;}\n'
        '\n'
        '\n'
        '.scene-transcript{position:absolute;bottom:0;left:0;right:0;min-height:70px;background:rgba(255,255,255,0.7);backdrop-filter:blur(24px);-webkit-backdrop-filter:blur(24px);border-top:1px solid rgba(255,255,255,0.8);color:var(--text);display:flex;flex-direction:column;align-items:center;justify-content:center;padding:12px 30px;z-index:40;}\n'
        '.transcript-title{font-size:11px;text-transform:uppercase;letter-spacing:1px;color:var(--c1);margin-bottom:4px;font-weight:800;}\n'
        '.transcript-text{font-size:16px;font-weight:600;text-align:center;}\n'
        '\n'
        '#start-overlay{position:absolute;inset:0;z-index:100;background:rgba(255,255,255,0.8);backdrop-filter:blur(16px);display:flex;flex-direction:column;align-items:center;justify-content:center;gap:20px;}\n'
        '#start-overlay h1{font-size:clamp(30px,5vw,60px);font-weight:800;background:linear-gradient(135deg,var(--c1),var(--c2));-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;text-align:center;}\n'
        '#start-btn{background:linear-gradient(135deg,var(--c1),var(--c2));color:#fff;border:none;padding:18px 46px;border-radius:99px;font-size:18px;font-weight:700;cursor:pointer;box-shadow:0 10px 30px rgba(14,165,233,0.4);transition:transform .2s,box-shadow .2s;}\n'
        '#start-btn:hover{transform:scale(1.05);box-shadow:0 15px 40px rgba(14,165,233,0.5);}\n'
        '#replay-btn{display:none;background:var(--bg);border:2px solid var(--c1);color:var(--text);padding:12px 30px;border-radius:99px;font-size:15px;font-weight:700;cursor:pointer;transition:all .2s;}\n'
        '#replay-btn:hover{background:var(--c1);color:#fff;}\n'
        '.hidden{display:none !important;}\n'
        '</style>\n'
        '</head>\n'
        '<body>\n'
        '\n'
        '<div id="page">\n'
        '  <div id="video-frame">\n'
        '    <div class="bg-blob b1"></div>\n'
        '    <div class="bg-blob b2"></div>\n'
        '\n'
        '    <div id="progress">\n'
        '      {% for s in plan.scenes %}\n'
        '      <div class="dot{% if loop.first %} current{% endif %}" data-i="{{ loop.index0 }}"></div>\n'
        '      {% endfor %}\n'
        '    </div>\n'
        '\n'
        '    {% for scene in plan.scenes %}\n'
        '    <div class="scene{% if loop.first %} active{% endif %}" id="scene-{{ scene.scene_id }}" data-layout-hint="{{ scene.layout_hint }}">\n'
        '\n'
        '      {% if scene.layout_hint == "title-card" %}\n'
        '        <div class="hero">\n'
        '          <div class="hero-icon pulse-soft">\n'
        '            <div class="orbit"><div class="orbit-dot"></div></div>\n'
        '            {% for cue in scene.visual_cues %}{% if cue.element_type == "icon" %}<img src="{{ cue.asset_url | safe }}" class="cue-asset float" style="width:100%;height:100%;" />{% endif %}{% endfor %}\n'
        '          </div>\n'
        '          <div class="hero-title">{{ plan.title }}</div>\n'
        '          <div class="hero-sub">{{ scene.subtitle or scene.text }}</div>\n'
        '        </div>\n'
        '\n'
        '      {% elif scene.layout_hint == "risk-diagram" %}\n'
        '        <div class="scene-title"><span>{{ scene.subtitle or scene.text }}</span></div>\n'
        '        <div class="risk-grid">\n'
        '          {% for cue in scene.visual_cues %}\n'
        '          <div class="risk-card glass-panel" style="animation-delay:{{ loop.index0 * 0.15 }}s">\n'
        '            <img src="{{ cue.asset_url | safe }}" class="cue-asset float-reverse" style="width:48px; height:48px; flex-shrink:0;" alt="Icon" />\n'
        '            <span class="risk-label">{{ cue.content or cue.description }}</span>\n'
        '          </div>\n'
        '          {% endfor %}\n'
        '        </div>\n'
        '\n'
        '      {% elif scene.layout_hint == "tunnel-diagram" %}\n'
        '        <div class="scene-title"><span>{{ scene.subtitle or scene.text }}</span></div>\n'
        '        <div class="tunnel-diagram">\n'
        '          {% for cue in scene.visual_cues %}\n'
        '          <div class="endpoint-icon glass-panel" style="padding: 24px; animation-delay:{{ loop.index0 * 0.2 }}s">\n'
        '             <img src="{{ cue.asset_url | safe }}" class="cue-asset pulse-soft" style="width:70px; height:70px; margin-bottom:12px;" alt="Icon" />\n'
        '             <span>{{ cue.description or cue.content }}</span>\n'
        '          </div>\n'
        '          {% endfor %}\n'
        '        </div>\n'
        '\n'
        '      {% elif scene.layout_hint == "flow-diagram" %}\n'
        '        <div class="scene-title"><span>How It Works</span></div>\n'
        '        <div class="flow-container">\n'
        '          {% for cue in scene.visual_cues %}\n'
        '          {% if not loop.first %}\n'
        '          <div class="flow-arrow" style="animation-delay:{{ loop.index0 * 0.3 }}s"><svg viewBox="0 0 32 32" style="width:40px;height:40px;" fill="none"><path d="M6 16h20M20 10l6 6-6 6" stroke="var(--c1)" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/></svg></div>\n'
        '          {% endif %}\n'
        '          <div class="flow-node glass-panel" style="animation-delay:{{ loop.index0 * 0.3 }}s">\n'
        '            <img src="{{ cue.asset_url | safe }}" class="cue-asset float" style="width:54px; height:54px;" alt="Icon" />\n'
        '            <span>{{ cue.description or cue.content }}</span>\n'
        '          </div>\n'
        '          {% endfor %}\n'
        '        </div>\n'
        '\n'
        '      {% elif scene.layout_hint == "cards" %}\n'
        '        <div class="scene-title"><span>Key Benefits</span></div>\n'
        '        <div class="card-grid">\n'
        '          {% for cue in scene.visual_cues %}\n'
        '          <div class="feature-card glass-panel" style="animation-delay:{{ loop.index0 * 0.2 }}s">\n'
        '            <img src="{{ cue.asset_url | safe }}" class="cue-asset float-reverse" style="width:64px; height:64px; margin-bottom:12px;" alt="Icon" />\n'
        '            <h3>{{ cue.content or cue.description }}</h3>\n'
        '          </div>\n'
        '          {% endfor %}\n'
        '        </div>\n'
        '\n'
        '      {% else %}\n'
        '        <div class="scene-title"><span>{{ scene.text }}</span></div>\n'
        '        <div style="display:flex; gap: 24px; justify-content: center; flex-wrap: wrap;">\n'
        '          {% for cue in scene.visual_cues %}\n'
        '          <div class="glass-panel" style="padding:24px; opacity:0; animation: scaleIn 0.6s cubic-bezier(0.34,1.56,0.64,1) forwards; animation-delay: {{ loop.index0 * 0.3 }}s; display: flex; flex-direction: column; align-items: center;">\n'
        '              <img src="{{ cue.asset_url | safe }}" alt="Asset" class="cue-asset pulse-soft" style="width: 80px; height: 80px; margin-bottom: 16px;" />\n'
        '              <p style="font-weight:700; font-size: 15px;">{{ cue.description or cue.content }}</p>\n'
        '          </div>\n'
        '          {% endfor %}\n'
        '        </div>\n'
        '      {% endif %}\n'
        '\n'
        '    </div>\n'
        '    {% endfor %}\n'
        '\n'
        '    <div class="scene-transcript">\n'
        '       <div class="transcript-title">Transcript</div>\n'
        '       <div class="transcript-text" id="subtitle-text"></div>\n'
        '    </div>\n'
        '\n'
        '    <div id="start-overlay">\n'
        '      <h1>{{ plan.title }}</h1>\n'
        '      <button id="start-btn">&#9654; &nbsp;Start Presentation</button>\n'
        '      <button id="replay-btn">&#8635; &nbsp;Replay</button>\n'
        '    </div>\n'
        '\n'
        '  </div>\n'
        '</div>\n'
        '\n'
        '<script>\n'
        '(function(){\n'
        '  const scenesData = [\n'
        '    {% for scene in plan.scenes %}\n'
        '    {\n'
        '      id: "scene-{{ scene.scene_id }}",\n'
        '      narration: {{ scene.text | tojson }},\n'
        '      subtitle: {{ (scene.subtitle or scene.text) | tojson }},\n'
        '      holdMs: {{ scene.hold_ms or 8000 }}\n'
        '    }{% if not loop.last %},{% endif %}\n'
        '    {% endfor %}\n'
        '  ];\n'
        '\n'
        '  let currentIdx = 0, isPlaying = false, stepTimer = null;\n'
        '  const sceneEls = scenesData.map(s => document.getElementById(s.id));\n'
        '  const dots = document.querySelectorAll("#progress .dot");\n'
        '  const subtitleText = document.getElementById("subtitle-text");\n'
        '  const startOverlay = document.getElementById("start-overlay");\n'
        '  const startBtn = document.getElementById("start-btn");\n'
        '  const replayBtn = document.getElementById("replay-btn");\n'
        '  const synth = window.speechSynthesis;\n'
        '  let chosenVoice = null;\n'
        '\n'
        '  function pickVoice(){\n'
        '    if(!synth) return;\n'
        '    try {\n'
        '      const voices = synth.getVoices();\n'
        '      chosenVoice = voices.find(v => v.lang && v.lang.startsWith("en") && /female|Samantha|Zira|Google US/i.test(v.name))\n'
        '                 || voices.find(v => v.lang && v.lang.startsWith("en"))\n'
        '                 || voices[0] || null;\n'
        '    } catch(e){}\n'
        '  }\n'
        '  if(synth){ pickVoice(); try { synth.onvoiceschanged = pickVoice; } catch(e){} }\n'
        '\n'
        '  function resetScene(el){\n'
        '    if(!el) return;\n'
        '    el.querySelectorAll("*").forEach(n => {\n'
        '      const a = getComputedStyle(n).animationName;\n'
        '      if(a && a !== "none" && !n.classList.contains("float") && !n.classList.contains("float-reverse") && !n.classList.contains("pulse-soft") && !n.classList.contains("bg-blob") && !n.classList.contains("orbit")){\n'
        '        n.style.animation = "none"; void n.offsetWidth; n.style.animation = "";\n'
        '      }\n'
        '    });\n'
        '  }\n'
        '\n'
        '  function showScene(i){\n'
        '    currentIdx = ((i % scenesData.length) + scenesData.length) % scenesData.length;\n'
        '    sceneEls.forEach((el, idx) => {\n'
        '      if(!el) return;\n'
        '      if(idx === currentIdx){ resetScene(el); el.classList.add("active"); }\n'
        '      else { el.classList.remove("active"); }\n'
        '    });\n'
        '    dots.forEach((d, idx) => {\n'
        '      if(d){ d.classList.toggle("done", idx < currentIdx); d.classList.toggle("current", idx === currentIdx); }\n'
        '    });\n'
        '    if(subtitleText) subtitleText.textContent = scenesData[currentIdx].narration || "";\n'
        '  }\n'
        '\n'
        '  function speakCurrentScene(){\n'
        '    return new Promise(resolve => {\n'
        '      const s = scenesData[currentIdx];\n'
        '      let done = false;\n'
        '      const finish = () => { if(!done){ done = true; resolve(); } };\n'
        '\n'
        '      const safetyMs = (s.holdMs || 8000) + 3000;\n'
        '      const fallbackTimer = setTimeout(finish, safetyMs);\n'
        '\n'
        '      if(synth && s.narration){\n'
        '        try {\n'
        '          synth.cancel();\n'
        '          if(synth.resume) synth.resume();\n'
        '          const utter = new SpeechSynthesisUtterance(s.narration);\n'
        '          if(chosenVoice) utter.voice = chosenVoice;\n'
        '          utter.rate = 1.0;\n'
        '          utter.onend = () => { clearTimeout(fallbackTimer); finish(); };\n'
        '          utter.onerror = () => { clearTimeout(fallbackTimer); finish(); };\n'
        '          synth.speak(utter);\n'
        '        } catch(err){ clearTimeout(fallbackTimer); finish(); }\n'
        '      } else {\n'
        '        clearTimeout(fallbackTimer);\n'
        '        setTimeout(finish, s.holdMs || 8000);\n'
        '      }\n'
        '    });\n'
        '  }\n'
        '\n'
        '  async function stepSequence(){\n'
        '    if(!isPlaying) return;\n'
        '    showScene(currentIdx);\n'
        '    await speakCurrentScene();\n'
        '    if(!isPlaying) return;\n'
        '    if(currentIdx < scenesData.length - 1){ currentIdx++; stepTimer = setTimeout(stepSequence, 400); }\n'
        '    else { isPlaying = false; replayBtn.style.display = "inline-flex"; startOverlay.classList.remove("hidden"); startBtn.style.display = "none"; }\n'
        '  }\n'
        '\n'
        '  function startAutoPlay(f){ isPlaying = true; currentIdx = f||0; if(stepTimer) clearTimeout(stepTimer); stepSequence(); }\n'
        '  function stopAutoPlay(){ isPlaying = false; if(stepTimer) clearTimeout(stepTimer); if(synth) synth.cancel(); }\n'
        '\n'
        '  dots.forEach((dot, idx) => { dot.addEventListener("click", () => { stopAutoPlay(); startOverlay.classList.add("hidden"); showScene(idx); }); });\n'
        '  startBtn.addEventListener("click", () => { startOverlay.classList.add("hidden"); startAutoPlay(0); });\n'
        '  replayBtn.addEventListener("click", () => { startOverlay.classList.add("hidden"); startAutoPlay(0); });\n'
        '  showScene(0);\n'
        '})();\n'
        '</script>\n'
        '</body>\n'
        '</html>'
    )