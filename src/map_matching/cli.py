import logging

logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

import click

import geopandas as gpd

from map_matching.match_detector_osm import iterate, export_to_csv, prep_network, get_osm_net, perform_sanity_checks
from map_matching.classes import FlowOrientation


@click.group()
@click.argument("detectors-filename", type=click.Path(exists=True))
@click.option("-directions", "--geocoded-directions-filename", default=None, type=click.Path(exists=True))
@click.option("-out", "--output-filename", default="detector-with-network.shp", type=click.Path())
@click.option("--direction-col", default="Richtung", type=click.STRING)
@click.option("--col-dict", default=None, type=click.STRING)
@click.option("--to-csv", default=None, type=click.Path())
@click.option("--sanity-checks", is_flag=True)
@click.pass_context
def cli(
    ctx,
    detectors_filename,
    geocoded_directions_filename,
    output_filename,
    direction_col,
    col_dict: str,
    to_csv,
    sanity_checks,
):
    detectors: gpd.GeoDataFrame = gpd.read_file(detectors_filename).set_crs(epsg=2056)

    logging.info("Read detectors")

    if geocoded_directions_filename is not None:
        logging.info("Geocoded directions option")
        geocoded = gpd.read_file(geocoded_directions_filename).set_crs(epsg=4326).to_crs(epsg=2056)

        logging.info("Read geocoded directions")

        detectors = detectors.merge(geocoded, on=direction_col).rename(
            {"geometry_x": "geometry", "geometry_y": "direction_coordinates"}, axis=1
        )
        detectors = detectors[detectors["direction_coordinates"] != None]

        logging.info("Merged dfs")

    if col_dict is not None:
        logging.info("Column dictionary option")
        col_dict = {key: y for key, y in [col.split(":") for col in col_dict.split(" ")]}
        detectors = detectors.rename(col_dict, axis="columns")

    detectors.sort_values(by=["ID"], inplace=True)

    ctx.obj = detectors


@cli.result_callback()
@click.pass_obj
def process(detectors: gpd.GeoDataFrame, network: gpd.GeoDataFrame, output_filename, to_csv, sanity_checks, **kwargs):
    print(detectors)
    print(network)

    # TEMPORARY
    network = network[network["name"].apply(lambda x: isinstance(x, str))]

    network = iterate(detectors, network)

    if sanity_checks:
        print("Passed sanity checks") if perform_sanity_checks(network) else print("Failed sanity checks")

    for flow in FlowOrientation:
        network.loc[:, flow.name] = network[flow.name].apply(lambda x: x if x is None else x.detector.ID)

    if False:
        filtered = network[~network[FlowOrientation.COUNTER.name].isna() | ~network[FlowOrientation.ALONG.name].isna()]
        filtered.drop(columns=["node_from", "node_to"]).to_file("filtered.shp")
        nodes = (
            pd.concat([filtered["node_from"], filtered["node_to"]])
            .reset_index()
            .drop(columns=["u", "v", "key"])
            .assign(osmid=lambda x: x.apply(lambda y: y.iloc[0].ID, axis=1))
            .assign(geometry=lambda x: x.apply(lambda y: y.iloc[0].geometry, axis=1))
        )
        # .drop_duplicates()\
        gpd.GeoDataFrame(nodes).drop(columns=[0]).to_file("nodes.shp")

    network.drop(columns=["node_from", "node_to", "osmid"]).to_file(output_filename)

    if to_csv:
        export_to_csv(network, to_csv)


@cli.command()
@click.option("--from-place", default="Zurich", type=click.STRING)
@click.option("--from-bbox")
@click.option("--save-net", nargs=2, default=None, type=click.Path())
def from_osm(from_place, from_bbox, save_net):
    if from_place:
        nodes, links = get_osm_net(from_place)
    if save_net is not None:
        nodes.to_file(save_net[0])
        links.to_file(save_net[1])
    network = prep_network(nodes, links)

    logging.info("Got OSM data")

    return network


@cli.command()
@click.argument("nodes-filename", type=click.Path(exists=True))
@click.argument("links-filename", type=click.Path(exists=True))
def from_file(nodes_filename, links_filename):
    nodes = gpd.read_file(nodes_filename)
    logging.info("Read nodes")

    links = gpd.read_file(links_filename)
    logging.info("Read links")

    return prep_network(nodes, links)


if __name__ == "__main__":
    cli()
