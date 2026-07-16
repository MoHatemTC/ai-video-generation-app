def create_animation_map(
    composition_data: dict,
    timestamp_map: TimestampMap
):
    animation_metadata = sync_animation(
        composition_data,
        timestamp_map
    )

    return {
        "status": "animation_map_ready",
        "animation_metadata": animation_metadata,
        "composed_layout": animation_metadata
    }