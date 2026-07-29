from dataclasses import dataclass
from typing import List

@dataclass
class QualityDimension:
    name: str
    weight: float          # must sum to 1.0
    max_score: int = 100

@dataclass
class QualityRubric:
    dimensions: List[QualityDimension]
    pass_threshold_overall: int = 70
    pass_threshold_category: int = 60

    @classmethod
    def default(cls) -> "QualityRubric":
        return cls(
            dimensions=[
                QualityDimension("script_coverage", 0.20),
                QualityDimension("scene_structure", 0.15),
                QualityDimension("layout_selection", 0.15),
                QualityDimension("visual_relevance", 0.20),
                QualityDimension("educational_effectiveness", 0.15),
                QualityDimension("consistency", 0.10),
                QualityDimension("schema_validity", 0.05),
            ],
        )