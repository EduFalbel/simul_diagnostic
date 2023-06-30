import geopandas as gpd

from map_matching.classes import Node, FlowOrientation

# OSM net methods ###################

def get_osm_net(place: str):
    import osmnx

    return osmnx.graph_to_gdfs(osmnx.graph_from_place(place))

def prep_net_from_file(nodes: gpd.GeoDataFrame, links: gpd.GeoDataFrame):
    nodes.set_index('osmid', inplace=True)
    links.set_index(['u', 'v', 'key'], inplace=True)
    return prep_network(nodes, links)

def prep_network(nodes: gpd.GeoDataFrame, links: gpd.GeoDataFrame, from_crs="WGS84", to_crs="LV95") -> gpd.GeoDataFrame:
    """Properly setup the network so it can be used in the algorithm"""
    nodes["node"] = nodes.to_crs(to_crs).apply(lambda x: Node(x.name, x.geometry), axis=1)
    links = (
        links.to_crs(to_crs)[~links["name"].isna()][["name", "oneway", "geometry", "osmid", "highway"]]
        .merge(nodes["node"], left_on="u", right_index=True)
        .merge(nodes["node"], left_on="v", right_index=True, suffixes=["_from", "_to"])
    )  # \
    # .droplevel('key')
    links[FlowOrientation.ALONG.name] = None
    links[FlowOrientation.COUNTER.name] = None

    return links

# Shapefiles from MATSim net

# Create network from node and link geodataframes ######################
def create_network_from_matsim(nodes: gpd.GeoDataFrame, links: gpd.GeoDataFrame):
    nodes["node"] = nodes.apply(lambda x: Node(x.index, x.geometry), axis=1)
    network = (
        links[~links["osm:way:name"].isna()][["osm:way:name", "geometry", "link_id", "from_node", "to_node", "osm:way:highway"]]
        .merge(nodes["node"], left_on="to_node", right_index=True)
        .merge(nodes["node"], left_on="from_node", right_index=True, suffixes=['_to', '_from'])
        .drop(columns=["from_node", "to_node"])
        .rename(
            columns={
                "osm:way:name": "name",
                "ID": "link_id",
                "osm:way:highway": "highway"
            }
        )
        .assign(oneway=1) # MATSim links are only oneway, always
    )
    network[FlowOrientation.ALONG.name] = None
    network[FlowOrientation.COUNTER.name] = None

    print(network)
    print(type(network))
    return gpd.GeoDataFrame(network)

def create_network_from_matsim_shapefiles(nodes: gpd.GeoDataFrame, links: gpd.GeoDataFrame):
    nodes = nodes.set_index('ID')
    links = links.rename(
            columns={
                "osm:way:na": "osm:way:name",
                "ID": "link_id",
                "TO": "to_node",
                "FROM": "from_node",
                "osm:way:hi": "osm:way:highway"
            }
        )
    return create_network_from_matsim(nodes, links)

# Create network from MATSim output with link and node geometries as well as the custom link attributes ######################

def create_network_from_matsim_network(network_filename: str):
    import matsim
    import shapely as shp

    network = matsim.read_network(network_filename)

    links = merge_links_with_attributes(network)
    print(links)
    print(links.columns)
    nodes = gpd.GeoDataFrame(
        network.nodes.assign(geometry=lambda x: shp.points(x["x"], x["y"]))
        )\
        .set_crs(epsg=2056)\
        .rename(columns={'node_id': 'ID'})\
        .set_index("ID")
    print(nodes)

    return create_network_from_matsim(nodes, links)


def merge_links_with_attributes(net) -> gpd.GeoDataFrame:
    links = net.as_geo().set_crs(epsg=2056)
    link_attrs = net.link_attrs.pivot(index="link_id", columns="name", values="value")
    assert set(links["link_id"].to_list()) == set(link_attrs.index.to_list())
    return links.merge(link_attrs, on="link_id").astype({'link_id': 'int64'})

# Geocoding #####################

def get_coordinates_geopy(detectors: gpd.GeoDataFrame, direction_col: str = "Richtung", einwerts: gpd.GeoDataFrame = None) -> gpd.GeoDataFrame:

    geocoded = gpd.GeoDataFrame(
        detectors[[direction_col]]\
            .drop_duplicates()
            .drop(["auswärts", "einwärts"], errors='ignore')
            .assign(geometry=lambda x: gpd.tools.geocode(x[direction_col])["geometry"])
    )
    if einwerts is not None:
        import pandas as pd
        geocoded = gpd.GeoDataFrame(
            pd.concat(
                [geocoded, einwerts],
                ignore_index=True,
            )
        )
    return geocoded