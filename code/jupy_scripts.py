# Load NHD flowline shapefiles
nhd_directory = 'NHD_Watershed_Shapefiles'

shapefiles = []
for root, dirs, files in os.walk(nhd_directory):
    for file in files:
        if file.endswith('.shp'):
            base_name = os.path.splitext(os.path.join(root, file))[0]
            # Check for the presence of .shp, .shx, and .dbf files
            if os.path.exists(base_name + '.shx') and os.path.exists(base_name + '.dbf'):
                shapefiles.append(os.path.join(root, file))
                print("Adding shapefile")
    
# Load and concatenate all valid shapefiles
flowlines_list = [gpd.read_file(shapefile) for shapefile in shapefiles]
nhd_flowlines = gpd.GeoDataFrame(pd.concat(flowlines_list, ignore_index=True))

# Check for valid geometries
nhd_flowlines = nhd_flowlines[nhd_flowlines.is_valid]

# Remove rows with missing geometries
nhd_flowlines = nhd_flowlines.dropna(subset=['geometry'])

# Set the plot size
fig, ax = plt.subplots(figsize=(15, 15))

# Convert GeoDataFrame to the correct CRS (EPSG:3857)
nhd_flowlines = nhd_flowlines.to_crs(epsg=3857)

# Check for NaN values in the geometry coordinates
if nhd_flowlines.is_empty.any() or nhd_flowlines.geometry.isnull().any():
    print("There are invalid geometries in the GeoDataFrame.")
else:
    print("All geometries are valid.")

# Plot the GeoDataFrame
nhd_flowlines.plot(ax=ax, color='blue', linewidth=0.5)

# Manually set the extent
minx, miny, maxx, maxy = nhd_flowlines.total_bounds
ax.set_xlim(minx, maxx)
ax.set_ylim(miny, maxy)

# Add basemap using contextily
ctx.add_basemap(ax, crs=nhd_flowlines.crs.to_string(), source=ctx.providers.OpenStreetMap.Mapnik)

# Show the plot
plt.show()