"""Composition service: turn stage contracts into renderer-ready scene maps."""

from __future__ import annotations

from backend.app.schemas.composed_scene import (
    AlignmentData, AssetCollection, AssetRecord, Canvas, ComposedElement,
    ComposedLayout, ComposedScene, CompositionOutput, ElementType, LayoutName,
    PlannerScene, Position, ScenePlanDocument, SegmentTimestamp, Size,
    VisualElement, WordTimestamp,
)


class CompositionService:
    """Build deterministic 1920×1080 slide layouts for the render stage."""

    CANVAS = Canvas(width=1920, height=1080)
    MARGIN_X = 120.0
    CONTENT_TOP = 250.0
    BOTTOM_MARGIN = 90.0
    COLUMN_GAP = 100.0

    def compose(self, scene_data: dict, asset_data: dict, timestamp_data: dict) -> dict:
        """Orchestrator entry point that returns JSON-serialisable output."""
        return self.compose_video(
            scene_data=scene_data, asset_data=asset_data, timestamp_data=timestamp_data
        ).model_dump(mode="json")

    def compose_video(
        self,
        *,
        scene_data: ScenePlanDocument | dict,
        asset_data: AssetCollection | dict,
        timestamp_data: AlignmentData | dict,
    ) -> CompositionOutput:
        planner = ScenePlanDocument.model_validate(scene_data)
        assets = AssetCollection.model_validate(asset_data)
        alignment = AlignmentData.model_validate(timestamp_data)
        self._validate_video_ids(planner, assets, alignment)

        segments = self._unique_by_id(alignment.segment_timestamps, "segment_id")
        words = self._unique_by_id(alignment.word_timestamps, "word_id")
        asset_lookup = self._asset_lookup(assets)
        self._validate_alignment(words, segments)

        scenes = [
            self._compose_scene(scene, asset_lookup, segments, words)
            for scene in planner.scenes
        ]
        return CompositionOutput(
            video_id=planner.video_id,
            composed_layout=ComposedLayout(scenes=scenes),
        )

    @staticmethod
    def _validate_video_ids(*documents: object) -> None:
        video_ids = {document.video_id for document in documents}
        if len(video_ids) != 1:
            raise ValueError("video_id must match across Scene Plan, Assets, and Alignment.")

    @staticmethod
    def _unique_by_id(items: list, field_name: str) -> dict:
        lookup = {getattr(item, field_name): item for item in items}
        if len(lookup) != len(items):
            raise ValueError(f"Duplicate {field_name} values are not allowed.")
        return lookup

    @staticmethod
    def _asset_lookup(assets: AssetCollection) -> dict[tuple[str, str, str], AssetRecord]:
        lookup = {
            (asset.scene_id, asset.cue_id, asset.asset_id): asset
            for asset in assets.assets
        }
        if len(lookup) != len(assets.assets):
            raise ValueError("Duplicate asset mappings are not allowed.")
        return lookup

    @staticmethod
    def _validate_alignment(
        words: dict[str, WordTimestamp], segments: dict[str, SegmentTimestamp]
    ) -> None:
        for word in words.values():
            try:
                segment = segments[word.segment_id]
            except KeyError as error:
                raise ValueError(f"word_id '{word.word_id}' references an unknown segment.") from error
            if not segment.start <= word.start < word.end <= segment.end:
                raise ValueError(f"word_id '{word.word_id}' is outside its segment timing.")

    def _compose_scene(self, scene, assets, segments, words) -> ComposedScene:
        scene_timings = self._scene_timings(scene, segments)
        scene_start = min(timing.start for timing in scene_timings)
        scene_end = max(timing.end for timing in scene_timings)
        placements = self._placements(scene)
        elements = [
            self._compose_element(scene, cue, position, size, layer, scene_end, assets, segments, words)
            for cue, position, size, layer in placements
        ]
        return ComposedScene(
            scene_id=scene.scene_id, layout=scene.layout, canvas=self.CANVAS,
            script_segments=scene.script_segments, start=scene_start, end=scene_end,
            elements=elements,
        )

    @staticmethod
    def _scene_timings(scene: PlannerScene, segments: dict[str, SegmentTimestamp]) -> list[SegmentTimestamp]:
        try:
            return [segments[segment_id] for segment_id in scene.script_segments]
        except KeyError as error:
            raise ValueError(f"Missing timing for segment '{error.args[0]}'.") from error

    def _placements(self, scene: PlannerScene) -> list[tuple[VisualElement, Position, Size, int]]:
        text = [cue for cue in scene.visual_elements if cue.element_type == ElementType.TEXT]
        visuals = [cue for cue in scene.visual_elements if cue.element_type != ElementType.TEXT]
        if scene.layout == LayoutName.TITLE_SLIDE:
            if len(text) != 1 or len(visuals) > 1:
                raise ValueError("title_slide requires one text cue and at most one visual cue.")
            placements = [(text[0], Position(x=220, y=120), Size(width=1480, height=180), 2)]
            if visuals:
                placements.append((visuals[0], Position(x=460, y=370), Size(width=1000, height=560), 1))
            return placements

        if len(text) != 1 or len(visuals) != 1:
            raise ValueError(f"{scene.layout.value} requires one text cue and one visual cue.")
        width = (self.CANVAS.width - 2 * self.MARGIN_X - self.COLUMN_GAP) / 2
        height = self.CANVAS.height - self.CONTENT_TOP - self.BOTTOM_MARGIN
        left = Position(x=self.MARGIN_X, y=self.CONTENT_TOP)
        right = Position(x=self.MARGIN_X + width + self.COLUMN_GAP, y=self.CONTENT_TOP)
        visual_position, text_position = (left, right) if scene.layout == LayoutName.IMAGE_LEFT_TEXT_RIGHT else (right, left)
        size = Size(width=width, height=height)
        return [(visuals[0], visual_position, size, 1), (text[0], text_position, size, 2)]

    def _compose_element(self, scene, cue, position, size, layer, scene_end, assets, segments, words) -> ComposedElement:
        start = self._cue_start(cue, segments, words)
        asset_id = asset_url = None
        if cue.element_type != ElementType.TEXT:
            key = (scene.scene_id, cue.cue_id, cue.asset_id)
            asset = assets.get(key)
            if asset is None:
                raise ValueError(f"Missing asset for scene={scene.scene_id}, cue={cue.cue_id}, asset_id={cue.asset_id}.")
            if asset.type != cue.element_type:
                raise ValueError(f"Asset '{asset.asset_id}' type does not match cue '{cue.cue_id}'.")
            asset_id, asset_url = asset.asset_id, asset.url
        return ComposedElement(
            cue_id=cue.cue_id, element_type=cue.element_type, content=cue.content,
            asset_id=asset_id, asset_url=asset_url, position=position, size=size,
            layer=layer, linked_segment_id=cue.linked_segment_id, start=start, end=scene_end,
        )

    @staticmethod
    def _cue_start(cue, segments: dict[str, SegmentTimestamp], words: dict[str, WordTimestamp]) -> float:
        if cue.appearance_trigger.type == "segment_start":
            return segments[cue.linked_segment_id].start
        word_id = cue.appearance_trigger.word_id
        word = words.get(word_id)
        if word is None:
            raise ValueError(f"Missing timing for word_id '{word_id}'.")
        if word.segment_id != cue.linked_segment_id:
            raise ValueError(f"word_id '{word_id}' does not belong to segment '{cue.linked_segment_id}'.")
        return word.start
