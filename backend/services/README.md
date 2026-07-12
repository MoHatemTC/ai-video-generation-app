# Services

Create the pipeline stages and backend business logic here.

Examples interns may create:

- `transcript_agent.py` - instruction to structured script.
- `scene_planner.py` - script to scene plan with visual cues.
- `audio.py` - script to voiceover (text-to-speech).
- `alignment.py` - voiceover to word/segment timestamps.
- `assets.py` - cue to asset (image, diagram, icon, GIF, SVG, clip).
- `composition.py` - assets to composed scene layout.
- `animation.py` - timed animation synced to the narration.
- `render.py` - composed scenes plus audio to a final video.
- `pipeline.py` - orchestrates the stages in order.
- `ai_client.py` - shared, swappable LLM client.

Each stage should be reusable, testable, consume the previous stage's structured output, and be able to retry independently.
