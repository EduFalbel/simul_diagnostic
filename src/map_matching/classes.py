from dataclasses import dataclass
import shapely as shp

@dataclass
class Node:
    ID: str
    geometry: shp.Point

@dataclass
class Detector:
    ID: int
    geometry: shp.Point
    axis: str
    direction_coordinates: shp.Point
    # degree: int

@dataclass
class FullInfo:
    detector: Detector
    distance: float
    degree: int


class FlowOrientation(Enum):
    ALONG = auto()
    COUNTER = auto()