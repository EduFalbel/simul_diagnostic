import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)

from typing import Literal
from functools import lru_cache
from pathlib import Path

import geopandas as gpd
import shapely as shp

from map_matching.classes import Node, Detector, FullInfo, FlowOrientation


def find_closest_links(detector: Detector, network: gpd.GeoDataFrame, net_name_col: str = "name"):
    """Finds the links with the same name as the axis listed by the detector and returns them sorted by distance to the detector
    
    Args:
        detector: The Detector object for which we want to find the closest link
        network: The network we are matching the detectors to
        net_name_col: The column in the network GeoDataFrame which contains the link/street names

    Returns:
        GeoDataFrame of links which have the same name as the axis listed by the detector, sorted by their distance to the detector
    """
    closest_links: gpd.GeoDataFrame = (
        network[network[net_name_col] == detector.axis]
        .copy()
        .assign(distance=lambda x: x["geometry"].distance(detector.geometry))
        .sort_values(by=["distance"])
    )

    return closest_links


def get_orientation(nodes: tuple[Node, Node], direction_coord: shp.Point):
    """Determine the orientation of a detector's measured flow relative to a link based on which of the link's end nodes is closer to the direction coordinate
    
    Args:
        nodes: Tuple of Node objects representing the link's starting and end nodes, respectively
        direction_coord: geocoded geometry of the detector's 'direction' attribute
        
    Returns:
        FlowOrientation enum representing whether the detector's measured flow is aligned with the link geometry or goes against it
    """
    distance_from, distance_to = nodes[0].geometry.distance(direction_coord), nodes[1].geometry.distance(
        direction_coord
    )
    if distance_from < distance_to:
        # return nodes[0]
        return FlowOrientation.COUNTER
    elif distance_to < distance_from:
        # return nodes[1]
        return FlowOrientation.ALONG
    else:
        raise Exception(f"Equal distance to direction for nodes {[node.id for node in nodes]}")


def verify_orientation(link, flow_orientation: FlowOrientation):
    """Verify whether the flow orientation for the detector is permitted in the given link
    
    Args:
        link: single-row GeoDataFrame representing the analyzed link
        flow_orientation: Orientation of the detector's measured flow
        
    Returns:
        False if flow's orientation goes against link geometry and link is only one-way and True otherwise
    """
    if link.at[link.index[0], "oneway"] and flow_orientation is FlowOrientation.COUNTER:
        return False
    return True


def no_collision(link, flow_orientation: FlowOrientation):
    """Check whether a detector has already been assigned to the given link in the given flow orientation
    
    Args:
        link: single-row GeoDataFrame representing the analyzed link
        flow_orientation: Orientation of the detector's measured flow
    
    Returns:
        True if there is currently no other detector assigned to the link's flow_orientation and False otherwise
    """
    if link.at[link.index[0], flow_orientation.name] is None:
        return True
    return False


def perform_checks(link, flow_orientation) -> Literal[0, 1, 2]:
    """
    Performs direction and collision checks

    Args:
        link: single-row GeoDataFrame representing the analyzed link
        flow_orientation: Orientation of the detector's measured flow

    Returns:
        0 - If incorrect orientation
        1 - Correct orientation but with collision
        2 - Correct orientation and no collision
    """
    return 0 if not verify_orientation(link, flow_orientation) else 1 + int(no_collision(link, flow_orientation))


def resolve_collision(
    network: gpd.GeoDataFrame, link, detector: Detector, flow_orientation: FlowOrientation, degree: int
) -> tuple[gpd.GeoDataFrame, bool]:
    """If previously assigned detector is farther from link than current detector, assign current detector to link and reassign previous detector to new link
    
    Args:
        network: The network we are matching the detectors to
        link: single-row GeoDataFrame representing the analyzed link
        detector: The Detector object for which we want to find the closest link
        flow_orientation: Orientation of the detector's measured flow
        degree: n representing that we're dealing with the n-th closest link to the detector
        
    Returns:
        Tuple consisting of the network and boolean indicating whether the provided link replaced the previously assigned one or not
    """
    assigned_full_info: FullInfo = network.at[link.index[0], flow_orientation.name]

    logging.debug(f"Assigned distance: {assigned_full_info.distance}")
    logging.debug(f"Link distance: {link.at[link.index[0], 'distance']}")

    if assigned_full_info.distance > link.at[link.index[0], "distance"]:
        network = assign_detector_to_link(detector, network, link, degree, flow_orientation)
        network = find_proper_link(assigned_full_info.detector, network, assigned_full_info.degree + 1)
        collision = False
    else:
        collision = True

    return network, collision


def assign_detector_to_link(
    detector, network, link, degree: int, flow_orientation: FlowOrientation
) -> gpd.GeoDataFrame:
    """Assign detector to link in the network
    
    Args:
        detector: The Detector object for which we want to find the closest link
        network: The network we are matching the detectors to
        link: single-row GeoDataFrame representing the analyzed link
        degree: n representing that we're dealing with the n-th closest link to the detector
        flow_orientation: Orientation of the detector's measured flow
    
    Returns:
        Modified network
    """
    logging.debug(f"link index:\n{link.index[0]}")
    logging.debug(f"flow orientation:\n{flow_orientation.name}")
    network.at[link.index[0], flow_orientation.name] = FullInfo(detector, link.at[link.index[0], "distance"], degree)
    return network


def find_proper_link(detector: Detector, network: gpd.GeoDataFrame, degree: int) -> gpd.GeoDataFrame:
    """Recursive funtion which attempts to assign the given detector to the network while dealing with potential conflicts
    
    Args:
        detector: The Detector object for which we want to find the closest link
        network: The network we are matching the detectors to
        degree: n representing that we're dealing with the n-th closest link to the detector

    Returns:
        Network with matched detector, if found. Otherwise no changes are made
    """
    collision = True
    closest_links = find_closest_links(detector, network)

    while collision:
        # Attempt to get the next closest link (with the correct name)
        try:
            nth_closest_link = closest_links.iloc[[degree]]
        except IndexError:
            logging.warning(f"Ran out of links for assignment of detector {detector}")
            return network

        flow_orientation = get_orientation(
            (
                nth_closest_link.at[nth_closest_link.index[0], "node_from"],
                nth_closest_link.at[nth_closest_link.index[0], "node_to"],
            ),
            detector.direction_coordinates,
        )

        match pc := perform_checks(nth_closest_link, flow_orientation):
            case 0:
                # Mismatched orientation
                degree += 1
            case 1:
                # Correct orientation but with collision
                network, collision = resolve_collision(network, nth_closest_link, detector, flow_orientation, degree)
                degree += 1
            case 2:
                # Correct orientation and no collision
                network = assign_detector_to_link(detector, network, nth_closest_link, degree, flow_orientation)
                collision = False
            case _:
                raise Exception(f"Serious problem with perform_checks method (returned {pc})")
        logging.debug(f"Case was {pc}")
    return network


def iterate(detectors: gpd.GeoDataFrame, network: gpd.GeoDataFrame):
    """Method to iterate over the detectors and call find_proper_link to match them to links in the network
    Args:
        detectors: GeoDataFrame of detectors
        network: The network we are matching the detectors to
        
    Returns:
        Network with matched detectors
    """
    # TODO: SPECIFY EXACT FORMAT OF DETECTORS GEODATAFRAME
    logging.debug(f"Network:\n\n{network}")

    n = 1
    for detector in detectors.itertuples():
        logging.info("Starting detector %d: %s" % (n, detector))
        degree = 0
        network = find_proper_link(detector, network, degree)
        n += 1
    return network


# Sanity check methods ###################


def perform_sanity_checks(network: gpd.GeoDataFrame):
    """Perform tests on the detector-matched network to make sure there were no collision-avoidance failures"""
    return only_along_oneway(network) and one_per_flow(network)


def only_along_oneway(network: gpd.GeoDataFrame) -> bool:
    """Check that links which are oneway only have a detector assigned in the 'along' column and None in the 'counter' column"""
    return network[network["oneway"] == 1].unique_values().to_list() == [None]


def one_per_flow(network: gpd.GeoDataFrame) -> bool:
    """Check that, for each link, there is at most one assigned detector for each flow orientation"""

    return (
        network[FlowOrientation.ALONG.name].map(type).apply(lambda x: isinstance(x, (FullInfo, None))).all()
        and network[FlowOrientation.COUNTER.name].map(type).apply(lambda x: isinstance(x, (FullInfo, None))).all()
    )


# Export methods ###################


def export_to_csv(network: gpd.GeoDataFrame, filename: Path):
    """Export a lookup table of link IDs to detector IDs"""
    import pandas as pd

    along = (
        network[["osmid", FlowOrientation.ALONG.name]]
        .dropna(how="any")
        .reset_index()
        .rename(columns={FlowOrientation.ALONG.name: "id"})
    )
    counter = (
        network[["osmid", FlowOrientation.COUNTER.name]]
        .dropna(how="any")
        .reset_index()
        .rename(columns={FlowOrientation.COUNTER.name: "id"})
    )

    # Reverse link start and end nodes to show that the detector goes against the flow
    counter[["u", "v"]] = counter[["v", "u"]]

    pd.concat([along, counter], ignore_index=True).drop(columns=["key"]).to_csv(filename, index=False)

    # network[[member.name for member in FlowOrientation]].dropna(how='all').to_csv(filename)
