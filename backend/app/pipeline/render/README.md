# Agentic Customized HTML Template Generator (CrewAI + Gemini API)

This package dynamically generates customized Jinja2 HTML templates tailored specifically to any input `ScenePlan` JSON file using **CrewAI** and **Google Gemini API**.

---

## Architecture Flow

1. **Input**: Ingests any `ScenePlan` JSON file (e.g. `docker_scene_plan.json`, `langchain_scene_plan.json`, `dummy_scene_plan.json`).
2. **AI Agent Generation**: A CrewAI `TemplateArchitect` agent powered by Google Gemini API analyzes the topic, visual cues, layout hints, and narration script to generate a customized Jinja2 template (`custom_template.jinja2`) with topic-specific CSS themes, keyframe animations, and Web Speech TTS audio scripts.
3. **Validation & Rendering**: Enriches missing asset metadata, validates against the Pydantic `ScenePlan` schema (`backend/app/schemas/scene.py`), and compiles the customized HTML file.

---

## Setup & Configuration

1. Open `.env` inside this folder:
   `backend/app/pipeline/render/agent_template_generator/.env`

2. Insert your free Google Gemini API Key from Google AI Studio:
   ```env
   GEMINI_API_KEY=AIzaSy...
   GOOGLE_API_KEY=AIzaSy...
   MODEL_NAME=gemini/gemini-2.5-flash
   ```

---

## How to Run

From this directory (`backend/app/pipeline/render/agent_template_generator/`):

```bash
# Render Docker explainer with customized AI template
python render_custom.py docker_scene_plan.json

# Render any arbitrary ScenePlan JSON file
python render_custom.py path/to/your_scene_plan.json
```

Outputs produced:
- `custom_template.jinja2`: The generated customized Jinja2 template for this topic.
- `docker_custom_output.html`: The compiled, standalone HTML presentation.
