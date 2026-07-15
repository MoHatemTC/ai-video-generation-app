from pathlib import Path

from backend.app.services.composition import CompositionService


def main() -> None:
    #Dummy Scene Planner output.
    #Notice: there are no x, y, width, or height values.
    #The CompositionService must calculate them.
    

    
    scene_plan = {
        "scene_id": "scene_1",
        "layout": "image_left_text_right",
        "script_segment_ids": ["seg_1"],
        "elements": [
            {
                "element_id": "title_1",
                "element_type": "text",
                "role": "title",
                "text": "How RAG Works",
            },
            {
                "element_id": "diagram_1",
                "element_type": "diagram",
                "role": "main_visual",
                "asset_url": "RAG-IMAGE.jpg",
                "alt_text": "RAG retrieval and generation diagram",
            },
            {
                "element_id": "body_1",
                "element_type": "text",
                "role": "body",
                "text": (
                    "1. Retrieve trusted context\n"
                    "2. Add context to the prompt\n"
                    "3. Generate a grounded answer"
                ),
            },
        ],
        # Timing is optional in Sprint 1.
        "timing": [
            {
                "script_segment_id": "seg_1",
                "start_time_seconds": 0.0,
                "end_time_seconds": 6.0,
            }
        ],
    }

    service = CompositionService()

    # Convert the high-level plan into exact renderer-ready coordinates.
    composed_scene = service.compose_scene(scene_plan)

    print("Composed scene generated successfully:\n")
    print(composed_scene.model_dump_json(indent=2))

    # Create visible static evidence.
    preview_path = service.save_svg(
        composed_scene,
        Path("composition_preview.svg"),
    )

    print(f"\nSVG preview saved to: {preview_path.resolve()}")


if __name__ == "__main__":
    main()