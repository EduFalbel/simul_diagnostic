import json
import click

import pandas as pd
import geopandas as gpd
import shapely as shp

import matsim

def get_coordinates_geopy(directions: pd.DataFrame, col_name: str = 'Richtung', city: str = 'Zurich'):
    return directions.assign(direction_coord = gpd.tools.geocode(directions[col_name] + ", " + city)['geometry'])

def associate_to_link(detectors: gpd.GeoDataFrame, links: pd.DataFrame, nodes: pd.DataFrame) -> gpd.GeoDataFrame:

    links_nodes = gpd.GeoDataFrame(
        links\
        .merge(nodes, left_on='to_node', right_on='node_id')\
        .assign(node_coord = lambda x: shp.points(x['x'], x['y']))\
        .drop(columns=['x', 'y'])
    )
    associated = detectors.apply(closest_link, links_nodes, axis=1)

    return associated

def closest_link(row, links_nodes: gpd.GeoDataFrame):
    possible_links: gpd.GeoDataFrame = \
        links_nodes[links_nodes['name'] == row['street_name']][['id', 'geometry', 'node_coord']]\
        .assign(distance = lambda x: x['geometry'].distance(row['geometry']))\
        .nsmallest(1, columns='distance', keep='all')
    if len(possible_links) == 1:
        # Nothing else we need to do
        pass
    elif len(possible_links) == 2:
        # We have superimposed links (due to the street being bi-directional)
        possible_links = possible_links\
            .assign(node_to_direction = lambda x: x.set_geometry('node_coord').distance(row.set_geometry('direction_coord')))\
            .nsmallest(1, columns='node_to_direction', keep='first')
    else:
        # This shouldn't be possible
        row['link_id'] = pd.NA
        return row
        # raise Exception('Reconsider your assumptions')
    row['link_id'] = possible_links.iloc[0]['link_id']
    return row

@click.command()
@click.argument('detectors_filename', type=click.Path(exists=True))
@click.argument('network_filename', type=click.Path(exists=True))
@click.option('--direction_col', type=click.STRING, default='Richtung')
@click.option('--geocoded_directions_filename', type=click.Path(exists=True), default=None)
@click.option('--filter_link_col', type=click.STRING, is_flag=False, flag_value='Filtered')
@click.option('--output_filename', type=click.STRING, is_flag=False, flag_value='detector_with_network.shp')
def cli(detectors_filename, network_filename, direction_col, geocoded_directions_filename, filter_link_col, output_filename):
    detectors = gpd.read_file(detectors_filename)
    if geocoded_directions_filename is not None:
        directions = detectors[[direction_col]].drop_duplicates().drop(["auswärts", "einwärts"])
        
        geocoded = get_coordinates_geopy(directions)

        zurich_hb_location = shp.Point(8.540323, 47.377858)
        geocoded.loc[len(geocoded)] = pd.DataFrame({'Richtung': "einwärts", 'geometry': zurich_hb_location})
    else:
        detectors = detectors.merge(geocoded, on=direction_col)
    
    network = matsim.read_network(network_filename)
    links, nodes = network.links, network.nodes
    
    if filter_link_col:
        links = links[links[filter_link_col] == True]
        
    nodes = nodes[nodes['id'].isin(links['from_node']) | nodes['id'].isin(links['to_node'])]

    associate_to_link(detectors, links, nodes).to_file(output_filename)
    
    return

if __name__ == '__main__':
    cli()