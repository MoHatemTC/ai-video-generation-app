from pydantic import BaseModel, Field
from enum import Enum

class Position(BaseModel):
    """this is the place of the element on the slide(composed scene / canvas) """
    x:float = Field(ge=0)
    y:float= Field(ge=0)

class Size(BaseModel):
    """this is the size of the element on the composed scene"""
    width:float=Field(gt=0)
    height:float= Field(gt=0)

class ElementType(str, Enum):
    TEXT="text"
    IMAGE="image"
    ICON="icon"
    DIAGRAM="diagram"
    SHAPE="shape"
    CHART="chart"
    GIF="gif"
    CLIP="clip"
    SVG="svg"


class Element(BaseModel):
    """ this is the element on the composed scene(text,image,icon,diagram) """
    element_id:str
    element_type: ElementType
    position: Position 
    size: Size
    text: str | None=None
    asset_url: str | None=None

class ComposedScene(BaseModel):
    scene_id:str
    layout:str
    elements: list[Element]

