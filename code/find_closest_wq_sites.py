import pandas as pd
import geopandas as gpd
from shapely.geometry import Point
import os
import networkx as nx
import matplotlib.pyplot as plt


# Load the MTBS data CSV
mtbs_df = pd.read_csv('output.csv')
mtbs_df['geometry'] = mtbs_df.apply(lambda row: Point(row['center_lon'], row['center_lat']), axis=1)
mtbs_gdf = gpd.GeoDataFrame(mtbs_df, geometry='geometry', crs="EPSG:4326")


# Load the USGS water quality sites CSV
usgs_df = pd.read_csv('water_quality/station.csv')

# Rename columns for easier access
usgs_df = usgs_df.rename(columns={
    'MonitoringLocationIdentifier': 'site_id',
    'LatitudeMeasure': 'lat',
    'LongitudeMeasure': 'long'
})

# Create a geometry column
usgs_df['geometry'] = usgs_df.apply(lambda row: Point(row['long'], row['lat']), axis=1)

# Convert to GeoDataFrame
usgs_gdf = gpd.GeoDataFrame(usgs_df, geometry='geometry', crs="EPSG:4326")


# Load NHD flowline shapefiles
nhd_directory = 'nhd'
shapefiles = []
for root, dirs, files in os.walk(nhd_directory):
    for file in files:
        if file.endswith('.shp'):
            shapefiles.append(os.path.join(root, file))

# Load and concatenate all shapefiles
flowlines_list = [gpd.read_file(shapefile) for shapefile in shapefiles]
nhd_flowlines = gpd.GeoDataFrame(pd.concat(flowlines_list, ignore_index=True))

# Ensure all GeoDataFrames have the same CRS
mtbs_gdf = mtbs_gdf.to_crs(nhd_flowlines.crs)
usgs_gdf = usgs_gdf.to_crs(nhd_flowlines.crs)

# Function to find the closest flowline segment to a given point
def find_closest_flowline(point, flowlines):
    return flowlines.distance(point).idxmin()

# Function to trace the downstream path from a given flowline segment
def trace_downstream(flowline_id, graph):
    downstream_path = []
    current_id = flowline_id
    
    while current_id in graph:
        downstream_path.append(current_id)
        try:
            current_id = list(graph.successors(current_id))[0]
        except IndexError:
            break
    
    return downstream_path

# Example function to map flowline IDs to downstream flowline IDs
# Note: Adjust this based on actual flow direction attributes
def map_flow_directions(flowlines):
    flow_direction = {}
    for idx, row in flowlines.iterrows():
        try:
            next_downstream_id = row['ToHydroID']  # Replace with actual flow direction attribute
            flow_direction[row['HydroID']] = next_downstream_id if next_downstream_id != -1 else None
        except KeyError as e:
            print(f"Error: {e}. The attribute 'ToHydroID' or 'HydroID' was not found.")
            return None
    return flow_direction


# Map the flow directions
flow_direction = map_flow_directions(nhd_flowlines)

# Create a directed graph for the flowlines
G = nx.DiGraph()
for idx, row in nhd_flowlines.iterrows():
    if row['ToHydroID'] != -1:
        G.add_edge(row['HydroID'], row['ToHydroID'])

# Find the downstream water quality site for each fire site
results = []

for fire in mtbs_gdf.itertuples():
    closest_flowline_id = find_closest_flowline(fire.geometry, nhd_flowlines)
    downstream_path_ids = trace_downstream(closest_flowline_id, G)
    downstream_flowlines = nhd_flowlines[nhd_flowlines['HydroID'].isin(downstream_path_ids)]
    
    # Find the closest downstream water quality site
    closest_downstream_site = usgs_gdf[usgs_gdf.intersects(downstream_flowlines.unary_union)].distance(fire.geometry).idxmin()
    closest_site_info = usgs_gdf.loc[closest_downstream_site]
    
    results.append({
        'fire_id': fire.Index,
        'center_lat': fire.center_lat,
        'center_lon': fire.center_lon,
        'downstream_site_id': closest_site_info['site_id'],
        'downstream_site_lat': closest_site_info['lat'],
        'downstream_site_lon': closest_site_info['long']
    })

# Convert results to DataFrame and merge with MTBS data
results_df = pd.DataFrame(results)
final_mtbs_df = mtbs_df.merge(results_df[['fire_id', 'downstream_site_id']], left_index=True, right_on='fire_id')

# Save the updated MTBS data to a new CSV file
final_mtbs_df.to_csv('updated_mtbs_output.csv', index=False)

print("MTBS data has been updated with the nearest downstream water quality site IDs.")
