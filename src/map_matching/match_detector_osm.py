import logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

from collections import namedtuple
from typing import Literal
from functools import lru_cache

import click

import pandas as pd
import geopandas as gpd
import shapely as shp

from fiona.errors import DriverError
from geopy.distance import distance

from src.map_matching.classes import Node, Detector, FullInfo, FlowOrientation

def find_closest_links(detector: Detector, links_nodes: gpd.GeoDataFrame, net_name_col: str = "name"):
    """Finds the links with the same name as the axis listed by the detector and returns them sorted by distance to the detector"""
    closest_link: gpd.GeoDataFrame = \
        links_nodes[links_nodes[net_name_col] == detector.axis].copy()\
        .assign(distance = lambda x: x['geometry'].distance(detector.geometry))\
        .sort_values(by=["distance"])
        # .nsmallest(1, columns='distance', keep='all')

    return closest_link

def get_orientation(nodes: tuple[Node], direction_coord: shp.Point):
    """Determine the orientation of the detector relative to the link based on which of a link's end nodes is closer to the direction coordinate"""
    distance_from, distance_to = nodes[0].geometry.distance(direction_coord), nodes[1].geometry.distance(direction_coord)
    if distance_from < distance_to:
        # return nodes[0]
        return FlowOrientation.COUNTER
    elif distance_to < distance_from:
        # return nodes[1]
        return FlowOrientation.ALONG
    else:
        raise Exception(f"Equal distance to direction for nodes {[node.id for node in nodes]}")

# def get_orientation(link, node: Node) -> FlowOrientation:
#     if node == link.at[link.index[0], "node_from"]: return FlowOrientation.COUNTER
#     elif node == link.at[link.index[0], "node_to"]: return FlowOrientation.ALONG
#     raise Exception("Node matching gone wrong")

def verify_orientation(link, flow_orientation: FlowOrientation):
    """Verify whether the flow orientation for the detector is permitted in the given link"""
    if link.at[link.index[0], "oneway"] and flow_orientation is FlowOrientation.COUNTER: return False
    return True

def no_collision(link, flow_orientation: FlowOrientation):
    """Check whether a detector has already been assigned to the given link in the given flow orientation"""
    if (link.at[link.index[0], flow_orientation.name] is None):
        return True
    return False

def resolve_collision(network: gpd.GeoDataFrame, link, detector: Detector, flow_orientation: FlowOrientation, degree: int) -> tuple[gpd.GeoDataFrame, bool]:
    """If previously assigned detector is farther from link than current detector, assign current detector to link and reassign previous detector to new link"""
    assigned_full_info: FullInfo = network.at[link.index[0], flow_orientation.name]

    print(f"Assigned distance: {assigned_full_info.distance}")
    print(f"Link distance: {link.at[link.index[0], 'distance']}")
    
    if assigned_full_info.distance > link.at[link.index[0], 'distance']:
        # assigned_detector, degree = assigned_link[flow_orientation.name]
        network = assign_detector_to_link(detector, network, link, degree, flow_orientation)
        network = find_proper_link(assigned_full_info.detector, network, assigned_full_info.degree + 1)
        collision = False
    else:
        collision = True

    return network, collision

def assign_detector_to_link(detector, network, link, degree: int, flow_orientation: FlowOrientation) -> gpd.GeoDataFrame:
    network.at[link.index[0], flow_orientation.name] = FullInfo(detector, link.at[link.index[0], 'distance'], degree)
    return network

def perform_checks(link, flow_orientation) -> Literal[0, 1, 2]:
    """
    Returns:
        0 - If incorrect orientation
        1 - Correct orientation and no collision
        2 - Correct orientation but with collision
    """
    return 0 if not verify_orientation(link, flow_orientation) else 1 + int(no_collision(link, flow_orientation))

def find_proper_link(detector: Detector, network: gpd.GeoDataFrame, degree: int) -> gpd.GeoDataFrame:
    collision = True
    closest_links = find_closest_links(detector, network)
    
    while collision:
        try:
            nth_closest_link = closest_links.iloc[[degree]]
        except IndexError:
            print("Ran out of links for assignment")
            return network

        flow_orientation = get_orientation(
            (
                nth_closest_link.at[nth_closest_link.index[0],'node_from'], 
                nth_closest_link.at[nth_closest_link.index[0],'node_to']
            ), 
            detector.direction_coordinates
        )
        # flow_orientation = get_orientation(nth_closest_link, closest_node_to_direction)

        match pc := perform_checks(nth_closest_link, flow_orientation):
            case 0:
                # Mismatched orientation
                degree += 1
            case 1:
                # Correct orientation but with collision
                network, collision = resolve_collision(network, nth_closest_link, detector, flow_orientation, degree)
                degree += 1
                # print(nth_closest_link)
            case 2:
                # Correct orientation and no collision
                network = assign_detector_to_link(detector, network, nth_closest_link, degree, flow_orientation)
                collision = False
                # print(nth_closest_link)
            case _:
                raise Exception(f"Serious problem with perform_checks method (returned {pc})")
        print(f"Case was {pc}")
        print(network.loc[nth_closest_link.index])
        # print(network)
    return network

def sanity_checks():
    # Check that links which are oneway only have a detector assigned in the 'along' column and None in the 'counter' column
    # Check that, for each link, there is at most one assigned detector for each flow orientation
    pass

@lru_cache
def get_osm_net(place: str):
    import osmnx
    nodes, links = osmnx.graph_to_gdfs(osmnx.graph_from_place(place))
    nodes["node"] = nodes.to_crs("LV95").apply(lambda x: Node(x.name, x.geometry), axis=1)
    links = links.to_crs("LV95")[~links["name"].isna()]\
                [["name", "oneway", "geometry"]]\
                .merge(nodes["node"], left_on="u", right_index=True)\
                .merge(nodes["node"], left_on="v", right_index=True, suffixes=["_from", "_to"])
                # .merge(nodes["node"], left_on="v", right_index=True, suffixes=["_to", "_from"])
    links[FlowOrientation.ALONG.name] = None
    links[FlowOrientation.COUNTER.name] = None
    
    # nodes[nodes.index.isin(links.index.get_level_values("u")) | nodes.index.isin(links.index.get_level_values("v"))].drop(columns=["node"]).to_file("nodes.shp")
    
    return links

def prep_network(network: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Properly setup the network so it can be used in the algorithm"""
    for name, member in FlowOrientation:
        network[name] = None

    return network

@click.command()
@click.argument('detectors_filename', type=click.Path(exists=True))
@click.option('--geocoded_directions_filename', type=click.Path(exists=True))
@click.option('--output_filename', type=click.STRING, default='detector_with_network.shp')
@click.option('--direction_col', type=click.STRING, default='Richtung')
@click.option('--col_dict', type=click.STRING)
def cli(detectors_filename, geocoded_directions_filename, output_filename, direction_col, col_dict: str):
    
    detectors: gpd.GeoDataFrame = gpd.read_file(detectors_filename).set_crs(epsg=2056)

    logging.info("Read detectors")

    geocoded = gpd.read_file(geocoded_directions_filename).set_crs(epsg=4326).to_crs(epsg=2056)
    
    logging.info("Read geocoded directions")
    
    detectors = detectors.merge(geocoded, on=direction_col).rename({"geometry_x": "geometry", "geometry_y": "direction_coordinates"}, axis=1)
    detectors = detectors[detectors["direction_coordinates"] != None]

    logging.info("Merged dfs")
    
    network = get_osm_net('Zurich')

    # TEMPORARY
    network = network[network["name"].apply(lambda x: isinstance(x, str))]

    logging.info("Got OSM data")

    if col_dict:
        col_dict = {key: y for key, y in [col.split(':') for col in col_dict.split(' ')]}
        detectors = detectors.rename(col_dict, axis='columns')
        # detector = Detector(ID=detector[col_dict["ID"]], geometry=detector.geometry, direction_coordinates=detector.direction_coordinates, axis=detector[col_dict["axis"]])

    detectors.sort_values(by=["ID"])

    # Yes, we will be iterating over a dataframe's rows.
    # Yes, this is an anti-pattern.
    # However, the detector df is small (less than a thousand rows) and we rely on recursion for matching
    n = 1
    for detector in detectors.itertuples():
        logging.info("Starting detector %d: %s" % (n, detector))
        # print(network)
        degree = 0
        network = find_proper_link(detector, network, degree)
        n+=1

    for flow in FlowOrientation:
        # network[[flow.name]] = network[[flow.name]].apply(lambda x: x.detector.ID, axis=1)
        # print(network[flow.name].apply(lambda x: x.iat[0, 0].detector.ID, axis=1))
        # network[flow.name] = network[flow.name].where(network[flow.name].isna(), network[flow.name].apply(lambda x: x.iat[0, 0].detector.ID, axis=1))
        network.loc[:, flow.name] = network[flow.name].apply(lambda x: x if x is None else x.detector.ID)
    
    filtered = network[~network[FlowOrientation.COUNTER.name].isna() | ~network[FlowOrientation.ALONG.name].isna()]
    filtered.drop(columns=["node_from", "node_to"]).to_file("filtered.shp")
    nodes = pd.concat([filtered["node_from"], filtered["node_to"]])\
        .reset_index()\
        .drop(columns=["u", "v", "key"])\
        .assign(osmid = lambda x: x.apply(lambda y: y.iloc[0].ID, axis=1))\
        .assign(geometry = lambda x: x.apply(lambda y: y.iloc[0].geometry, axis=1))
        # .drop_duplicates()\
    print(nodes)
    gpd.GeoDataFrame(nodes).drop(columns=[0]).to_file("nodes.shp")

    network.drop(columns=["node_from", "node_to"]).to_file(output_filename)

if __name__ == "__main__":
    print("Started")
    cli()
    
