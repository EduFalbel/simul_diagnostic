from collections import namedtuple
from typing import Literal
from enum import Enum, auto

import click

import pandas as pd
import geopandas as gpd

from fiona.errors import DriverError
from geopy.distance import distance

from classes import Node, Detector, FullInfo, FlowOrientation

def find_closest_links(detector, links_nodes: gpd.GeoDataFrame, net_name_col: str = "name"):
    """Finds the links with the same name as the axis listed by the detector and returns them sorted by distance to the detector"""
    closest_link: gpd.GeoDataFrame = \
        links_nodes[links_nodes[net_name_col] == detector.axis][['link_id', 'geometry', 'node_coord']].copy()\
        .assign(distance = lambda x: x['geometry'].distance(detector.geometry))\
        .sort_values(by=["distance"])
        # .nsmallest(1, columns='distance', keep='all')

    return closest_link

def find_closest_node(nodes: tuple[Node], direction_coord):
    """Determine which of a link's end nodes is closer to a given direction coordinate"""
    distance_1, distance_2 = distance(nodes[0].geometry, direction_coord), distance(nodes[1].geometry, direction_coord)
    if distance_1 < distance_2:
        return nodes[0]
    elif distance_2 < distance_1:
        return nodes[1]
    else:
        raise Exception(f"Equal distance to direction for nodes {[node.id for node in nodes]}")

def get_orientation(link, node) -> FlowOrientation:
    if node.id == link["from_node"]: return FlowOrientation.COUNTER
    return FlowOrientation.ALONG

def verify_orientation(link, flow_orientation: FlowOrientation):
    """Verify whether the flow orientation for the detector is permitted in the given link"""
    if link["oneway"] and flow_orientation == 'counter': return False
    return True

def no_collision(link, flow_orientation: FlowOrientation):
    """Check whether a detector has already been assigned to the given link in the given flow orientation"""
    if (
        (flow_orientation is FlowOrientation.COUNTER and link["counter_detector"] is None) or\
        (flow_orientation is FlowOrientation.ALONG and link["along_detector"] is None)):
        return True
    return False

def resolve_collision(network: gpd.GeoDataFrame, link, detector: Detector, flow_orientation: FlowOrientation, degree: int) -> tuple[gpd.GeoDataFrame, bool]:
    """If previously assigned detector is farther from link than current detector, assign current detector to link and reassign previous detector to new link"""
    assigned_full_info: FullInfo = network.iloc[link.index][flow_orientation.name]
    
    if assigned_full_info.distance > link['distance']:
        # assigned_detector, degree = assigned_link[flow_orientation.name]
        network = assign_detector_to_link(detector, network, link, distance, degree, flow_orientation)
        network = find_proper_link(assigned_full_info.detector, network, assigned_full_info.degree)
        collision = False
    else:
        collision = True

    return network, collision

def assign_detector_to_link(detector, network, link, distance, degree, flow_orientation) -> gpd.GeoDataFrame:
    network.iloc[link.index][flow_orientation.name] = FullInfo(detector, distance, degree + 1)
    pass

def perform_checks() -> Literal[0, 1, 2]:
    """
    Returns:
        0 - If incorrect orientation
        1 - Correct orientation and no collision
        2 - Correct orientation but with collision
    """
    return 0 if not verify_orientation() else 1 + int(no_collision())

def find_proper_link(detector: Detector, network: gpd.GeoDataFrame, degree: int) -> gpd.GeoDataFrame:
    collision = True
    closest_links = find_closest_links(detector, network)
    
    while collision:
        try:
            nth_closest_link = closest_links.iloc[[degree]]
        except IndexError:
            raise IndexError("Ran out of links for assignment")

        # TODO: Fix below
        closest_node_to_direction = find_closest_node(nth_closest_link.nodes, detector.direction_coordinates)
        flow_orientation = get_orientation(nth_closest_link, closest_node_to_direction)

        match pc := perform_checks():
            case 0:
                # Mismatched orientation
                degree += 1
            case 1:
                # Correct orientation and no collision
                network = assign_detector_to_link(detector, network, nth_closest_link, distance, degree, flow_orientation)
                collision = False
            case 2:
                # Correct orientation but with collision
                network, collision = resolve_collision(network, nth_closest_link, detector, flow_orientation, degree)
                degree += 1
            case _:
                raise Exception(f"Serious problem with perform_checks method (returned {pc})")
    return network

def sanity_checks():
    # Check that links which are oneway only have a detector assigned in the 'along' column and None in the 'counter' column
    # Check that, for each link, there is at most one assigned detector for each flow orientation
    pass

def prep_network(network: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Properly setup the network so it can be used in the algorithm"""
    for name, member in FlowOrientation:
        network[name] = None

    return network

@click.command()
@click.argument('detectors_filename', type=click.Path(exists=True))
@click.argument('network_filename', type=click.Path(exists=True))
@click.option('--direction_col', type=click.STRING, default='Richtung')
@click.option('--geocoded_directions_filename', type=click.Path(), default=None)
@click.option('--filter_link_col', type=click.STRING, is_flag=False, flag_value='Filtered')
@click.option('--output_filename', type=click.STRING, default='detector_with_network.shp')
def cli(detectors_filename, network_filename, direction_col, geocoded_directions_filename, filter_link_col, output_filename):
    detectors = gpd.read_file(detectors_filename)
    network = gpd.read_file(network_filename)

    for detector in detectors:
        degree = 0
        network = find_proper_link(detector, network, degree)
    pass

if __name__ == "main":
    cli()
    
