# Visual Layout System — Sprint 2
**Lane:** Visual Layout System | **By:** Mahdi (Mohamed Mahdy)

## What's in here

This is the layout system for how our generated videos should look. I went through the
reference video(s) we have, pulled out the recurring visual patterns, and turned them into a
set of reusable layouts the Scene Planner can pick from and populate.

**Note on the "presenter" layout:** the PRD says a presenter face isn't part of v1, so instead
of an actual person-on-camera layout I made an "attribution card" style layout
(`narrator_note`) — a statement/quote with a small generic icon, not a real face. If we add
real presenter footage later, this layout can be extended with a video field without breaking
anything.

## Files

- `01_reference_video_analysis.md` — notes from watching the reference video, the recurring
  visual patterns I found
- `02_layout_catalogue.md` — the 8 reusable layouts
- `03_layout_specifications.md` — the actual spec for each layout: fields, placement, colors,
  text limits, fallback behavior
- `04_scene_planner_mapping.md` — how a Scene Planner output maps to these layouts and gets
  filled in

## How downstream stages should use this

- **Composition:** read `layout` from the Scene Planner output, look up the spec in file 03,
  fill in the fields using the mapping in file 04. Handle missing/broken content before it
  reaches Animation & Render.
- **Animation & Render:** use the hold-time and transition guidance in file 03 as defaults.
- **Scene Planner:** the `layout` field needs to be one of the 8 IDs exactly, otherwise it
  falls back to `text_explanation`.

## Known gaps

- Colors and fonts are placeholders — the real brand guideline doc wasn't available, so these
  need to be swapped in before this goes to production.
- Only had one reference video to work from. `comparison` and `step_by_step` weren't literally
  in it, so those two are based on the same visual language rather than something I directly
  observed — worth double-checking once we get more reference videos.