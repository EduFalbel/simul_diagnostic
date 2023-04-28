import pytest

import shapely as shp
import geopandas as gpd
import numpy as np

from map_matching.classes import *
from map_matching.match_detector_osm import find_closest_links

@pytest.fixture
def links_gdf():
    return gpd.GeoDataFrame({
        "u": np.arange(3),
        "v": np.arange(2, -1),
        "name": ["street_name"] * 2 + ["other_street"],
        FlowOrientation.COUNTER.name: [None] * 3,
        FlowOrientation.ALONG.name: [None] * 3,
        "geometry": [shp.LineString([(x, y), (x + 5, y)] for x, y in (np.arange(2), np.arange(2)))] + [shp.LineString([(5, 0), (5, -2)])]
    }, geometry = "geometry")

@pytest.fixture
def nodes_gdf():
    pass

@pytest.fixture
def detector_gdf():
    pass

@pytest.fixture
def detector():
    return Detector(1, shp.Point(0, 0), "street_name", shp.Point(0, 10))

def test_find_closest_links(detector: Detector, links_gdf: gpd.GeoDataFrame):
    assert find_closest_links(detector, links_gdf) == links_gdf[links_gdf["name"] == "street_name"].assign(distance = [0, 5])
    

def