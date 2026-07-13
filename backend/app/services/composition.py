from backend.app.schemas.composed_scene import ComposedScene
from pydantic import ValidationError

class CompositionService:
    """this class composes the scene-plan into a composed scene object"""



    def compose_scene(self, scene_plan:dict) -> ComposedScene:
        """ this function builds a composed scene from the scene-plan dictionary """
        """the try except block is to check if the scene_plan has any missing values or invalid ones to handle exceptions early"""
        try:
            return ComposedScene(
                scene_id=scene_plan["scene_id"],
                layout=scene_plan["layout"],
                elements=scene_plan["elements"]

            )
        except(KeyError, ValidationError) as error:
            raise ValueError(f"Invalid scene-plan data: {error}") from error
