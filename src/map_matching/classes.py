from dataclasses import dataclass
import shapely as shp
from enum import Enum, auto


@dataclass
class Node:
    ID: int
    geometry: shp.Point


@dataclass
class Detector:
    ID: str
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
