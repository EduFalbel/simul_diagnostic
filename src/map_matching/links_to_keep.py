import pandas as pd
import geopandas as gpd

from time import perf_counter

import click

def filter_network(network: gpd.GeoDataFrame, detectors: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    detectors: gpd.GeoDataFrame = detectors.apply(find_nearest_link, network=network, axis=1)
    return network[network['fid'].isin(detectors['link_id'])]

def find_nearest_link(row, network: gpd.GeoDataFrame):
    distances = network[network['name'] == row["Achse"]][['fid', 'geometry']].assign(distance = lambda x: x['geometry'].distance(row['geometry']))
    # print(distances)
    # distances.apply(calc_distance, network=network, axis=1)
    try:
        row['link_id'] = distances.nsmallest(n=1, columns="distance", keep='first').iloc[0]['fid']
    except Exception as e:
        print(e)
        row['link_id'] = pd.NA
    print(row['link_id'])
    return row

@click.command()
@click.argument('osm_network_filename', type=click.Path(exists=True))
@click.argument('detector_db_filename', type=click.Path(exists=True))
@click.option('--out_filename', default='filtered_network.shp', help='Filename for shapefile output')
def links_to_keep(osm_network_filename, detector_db_filename, out_filename):
    start = perf_counter()
    network: gpd.GeoDataFrame = gpd.read_file(osm_network_filename)
    end = perf_counter()
    print(f"Time to read network: {end - start}")
    detectors: gpd.GeoDataFrame = gpd.read_file(detector_db_filename)

    filter_network(network, detectors).to_file(f"{out_filename}")

if __name__ == "__main__":
    links_to_keep()    
    
