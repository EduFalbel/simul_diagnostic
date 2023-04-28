import json
import click

import pandas as pd
import geopandas as gpd
import shapely as shp
from fiona.errors import DriverError

import matsim

def get_coordinates_geopy(directions: pd.DataFrame, col_name: str = 'Richtung', city: str = 'Zurich') -> gpd.GeoDataFrame:
    return gpd.GeoDataFrame(directions.assign(direction_coord = gpd.tools.geocode(directions[col_name] + ", " + city)['geometry']))

def create_links_nodes(links: pd.DataFrame, nodes: pd.DataFrame) -> gpd.GeoDataFrame:

    links_nodes = gpd.GeoDataFrame(
        links\
        .merge(nodes, left_on='to_node', right_on='node_id')\
        .assign(node_coord = lambda x: shp.points(x['x'], x['y']))\
        .drop(columns=['x', 'y'])
    )

    return links_nodes

def closest_link(row, links_nodes: gpd.GeoDataFrame, net_name_col: str = "osm:way:name", detect_name_col: str = "Achse"):
    # print(f"Row: {row}")

    possible_links: gpd.GeoDataFrame = \
        links_nodes[links_nodes[net_name_col] == row[detect_name_col]][['link_id', 'geometry', 'node_coord']]\
        .assign(distance = lambda x: x['geometry'].distance(row['geometry']))\
        .nsmallest(1, columns='distance', keep='all')
    if len(possible_links) == 1:
        # Nothing else we need to do
        pass
    elif len(possible_links) == 2:
        # We have superimposed links (due to the street being bi-directional)
        print(type(possible_links))
        possible_links = possible_links\
            .set_geometry('node_coord')\
            .assign(node_to_direction = lambda x: x.distance(row['direction_coord']))\
            .nsmallest(1, columns='node_to_direction', keep='first')
    else:
        # This shouldn't be possible
        row['link_id'] = pd.NA
        return row
        # raise Exception('Reconsider your assumptions')
    row['link_id'] = possible_links.iloc[0]['link_id']
    return row

def get_full_links(net: matsim.Network) -> gpd.GeoDataFrame:
    links = net.as_geo().set_crs(epsg=2056)
    link_attrs = net.link_attrs.pivot(index='link_id', columns='name', values='value')
    assert set(links['link_id'].to_list()) == set(link_attrs.index.to_list())
    return links.merge(link_attrs, on='link_id')

@click.command()
@click.argument('detectors_filename', type=click.Path(exists=True))
@click.argument('network_filename', type=click.Path(exists=True))
@click.option('--direction_col', type=click.STRING, default='Richtung')
@click.option('--geocoded_directions_filename', type=click.Path(), default=None)
@click.option('--filter_link_col', type=click.STRING, is_flag=False, flag_value='Filtered')
@click.option('--output_filename', type=click.STRING, default='detector_with_network.shp')
def cli(detectors_filename, network_filename, direction_col, geocoded_directions_filename, filter_link_col, output_filename):
    detectors = gpd.read_file(detectors_filename)
    detectors.set_crs(epsg=2056)
    
    try:
        geocoded = gpd.read_file(geocoded_directions_filename).set_crs(epsg=4326)
    except DriverError:
        directions = detectors[[direction_col]].drop_duplicates()[~detectors[direction_col].drop_duplicates().isin(["auswärts", "einwärts"])]
        print(directions)
        
        geocoded = get_coordinates_geopy(directions)
        print(geocoded)

        zurich_hb_location = shp.Point(8.540323, 47.377858)
        geocoded = gpd.GeoDataFrame(pd.concat([geocoded, gpd.GeoDataFrame({'Richtung': ["einwärts"], 'direction_coord': [zurich_hb_location]})], ignore_index=True))
        geocoded.set_geometry('direction_coord').set_crs(epsg=4326).to_file(geocoded_directions_filename)

    geocoded = geocoded.to_crs(epsg=2056)

    detectors = detectors.merge(geocoded, on=direction_col).rename({"geometry_x": "geometry", "geometry_y": "direction_coord"}, axis=1)
    detectors = detectors[detectors["direction_coord"] != None]
    print(detectors)
    
    network = matsim.read_network(network_filename)
    nodes = network.nodes
    full_links = get_full_links(network)
    full_links.to_file("full_links.shp")
    
    if filter_link_col:
        full_links = full_links[full_links[filter_link_col] == True]    
        nodes = nodes[nodes['id'].isin(full_links['from_node']) | nodes['id'].isin(full_links['to_node'])]

    links_nodes = create_links_nodes(full_links, nodes)

    associated_detectors = gpd.GeoDataFrame(detectors.apply(closest_link, links_nodes=links_nodes, axis=1)).drop(columns=["direction_coord"])
    # associated_detectors.to_file(output_filename)

    associated_links = links_nodes.merge(associated_detectors, how='inner', on='link_id').set_geometry("geometry_x")
    associated_nodes = associated_links.drop(columns=["geometry_y", "geometry_x"]).set_geometry("node_coord")
    print(associated_links.columns)
    # associated_links.drop(columns=["geometry_y", "node_coord"]).to_file('link_with_network.shp')
    # associated_nodes.to_file('nodes.shp')
    
if __name__ == '__main__':
    cli()