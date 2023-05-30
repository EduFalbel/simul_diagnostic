import pytest

import shapely as shp
import geopandas as gpd
import pandas as pd

from map_matching.classes import *
from map_matching.match_detector_osm import find_closest_links, get_orientation, verify_orientation, no_collision

# Nodes #############################

@pytest.fixture
def nodes_df():
    # Dataframe with 4 nodes in a T shape
    return gpd.GeoDataFrame({
        "node": [Node(i, shp.Point(x, 0)) for i, x in zip(range(3), (0, 5, 10))] + [Node(3, shp.Point(5, -10))]
    }, index = pd.Index(range(4), name = 'osmid'))

@pytest.fixture
def node_tuple():
    return (Node(0, shp.Point(0, 0)), Node(1, shp.Point(5, 0)))

# Links ##############################

@pytest.fixture
def oneway_link():
    return gpd.GeoDataFrame({
        "name": ["street_name"],
        "oneway": [1],
        FlowOrientation.COUNTER.name: [None],
        FlowOrientation.ALONG.name: [None],
        "geometry": [shp.LineString([(0, 0), (5, 0)])]
    }, index = pd.MultiIndex.from_arrays([[0], [1]], names = ["u", "v"]))

@pytest.fixture
def twoway_link():
    return gpd.GeoDataFrame({
        "name": ["other_street"],
        "oneway": [0],
        FlowOrientation.COUNTER.name: [None],
        FlowOrientation.ALONG.name: [None],
        "geometry": [shp.LineString([(5, 0), (5, -2)])]
    }, index = pd.MultiIndex.from_arrays([[0], [1]], names = ["u", "v"]))

@pytest.fixture
def links_gdf():
    # Geodataframe with two streets, three line segments
    return gpd.GeoDataFrame({
        "name": ["street_name"] * 2 + ["other_street"],
        "oneway": [1] * 2 + [0],
        FlowOrientation.COUNTER.name: [None] * 3,
        FlowOrientation.ALONG.name: [None] * 3,
        "geometry": [shp.LineString([(x, 0), (x + 5, 0)]) for x in (0, 5)] + [shp.LineString([(5, 0), (5, -2)])]
    }, index = pd.MultiIndex.from_arrays([[0, 1, 1], [1, 2, 3]], names = ["u", "v"]))

# Links_nodes ##########################

@pytest.fixture
def links_nodes_gdf(links_gdf, nodes_df):
    return links_gdf\
        .merge(nodes_df["node"], left_on="u", right_index=True)\
        .merge(nodes_df["node"], left_on="v", right_index=True, suffixes=["_from", "_to"])

# Detectors ###################################

@pytest.fixture
def detector_gdf():
    return gpd.GeoDataFrame({
        "id": range(3),
        "geometry": [shp.Point(x, 0) for x in (2, 7)] + [shp.Point(5, -5)],
        "axis": ["street_name"] * 2 + ["other_street"],
        "direction_coordinates": [shp.Point(x, y) for x, y in ((20, 0), (20, 0), (5, -20))]
    })

@pytest.fixture
def detector():
    return Detector("1", shp.Point(0, 0), "street_name", shp.Point(20, 0))

# Tests ###############################################

def test_find_closest_links(detector: Detector, links_nodes_gdf: gpd.GeoDataFrame):
    find = find_closest_links(detector, links_nodes_gdf)
    manual = links_nodes_gdf[links_nodes_gdf["name"] == "street_name"].assign(distance = [0.0, 5.0])

    assert find.equals(manual)

def test_get_orientation(node_tuple, detector):
    direction_coordinates = detector.direction_coordinates
    assert get_orientation(node_tuple, direction_coordinates) == FlowOrientation.ALONG

#### Verify orientation

def test_verify_orientation_oneway_along(oneway_link):
    assert verify_orientation(oneway_link, FlowOrientation.ALONG)

def test_verify_orientation_oneway_counter(oneway_link):
    assert not verify_orientation(oneway_link, FlowOrientation.COUNTER)

def test_verify_orientation_twoway_along(twoway_link):
    assert verify_orientation(twoway_link, FlowOrientation.ALONG)

def test_verify_orientation_twoway_counter(twoway_link):
    assert verify_orientation(twoway_link, FlowOrientation.COUNTER)

#### Collision detection

def test_no_collision_oneway(oneway_link):
    assert no_collision(oneway_link, FlowOrientation.ALONG)

def test_collision_oneway(oneway_link, detector):
    oneway_link.loc[:, FlowOrientation.ALONG.name] = detector
    assert not no_collision(oneway_link, FlowOrientation.ALONG)

def test_collision_twoway_counter(twoway_link, detector):
    twoway_link.loc[:, FlowOrientation.COUNTER.name] = detector
    assert not no_collision(twoway_link, FlowOrientation.COUNTER)

def test_collision_twoway_along(twoway_link, detector):
    twoway_link.loc[:, FlowOrientation.ALONG.name] = detector
    assert not no_collision(twoway_link, FlowOrientation.ALONG)

def test_no_collision_twoway_along_counter(twoway_link, detector):
    twoway_link.loc[:, FlowOrientation.ALONG.name] = detector
    assert no_collision(twoway_link, FlowOrientation.COUNTER)