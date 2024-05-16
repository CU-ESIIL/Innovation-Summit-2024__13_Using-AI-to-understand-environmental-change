import os
import zipfile
import rasterio
import numpy as np
import pandas as pd
import xml.etree.ElementTree as ET

def extract_and_calculate_average(tif_file_path):
    try:
        with rasterio.open(tif_file_path) as src:
            data = src.read(1)  # Read the first band
            data = np.ma.masked_equal(data, src.nodata)  # Mask out no-data values
            average_severity = data.mean()  # Calculate average severity
        return average_severity
    except Exception as e:
        print(f'Error processing {tif_file_path}: {e}')
        return None

def extract_fire_details(xml_file_path):
    try:
        tree = ET.parse(xml_file_path)
        root = tree.getroot()
        namespace = {'': 'http://www.w3.org/1999/xhtml'}  # Namespace for the XML

        date = root.find('.//caldate').text.strip()
        westbc = float(root.find('.//westbc').text.strip())
        eastbc = float(root.find('.//eastbc').text.strip())
        northbc = float(root.find('.//northbc').text.strip())
        southbc = float(root.find('.//southbc').text.strip())

        center_lat = (northbc + southbc) / 2
        center_lon = (westbc + eastbc) / 2

        return date, center_lat, center_lon
    except Exception as e:
        print(f'Error processing {xml_file_path}: {e}')
        return None, None, None

def list_all_files_and_dirs(base_path):
    for root, dirs, files in os.walk(base_path):
        print(f'Current directory: {root}')
        print(f'Subdirectories: {dirs}')
        print(f'Files: {files}')

def process_fire_folders(zip_folder_path, output_csv_path):
    results = []
    with zipfile.ZipFile(zip_folder_path, 'r') as zip_ref:
        zip_ref.extractall('extracted_data')
    
    base_dir = 'extracted_data/mtbs'
    print(f'Processing base directory: {base_dir}')
    list_all_files_and_dirs(base_dir)
    
    for year in os.listdir(base_dir):
        year_path = os.path.join(base_dir, year)
        if os.path.isdir(year_path):
            print(f'Processing year directory: {year_path}')
            for fire_zip in os.listdir(year_path):
                fire_zip_path = os.path.join(year_path, fire_zip)
                if fire_zip_path.endswith('.zip'):
                    with zipfile.ZipFile(fire_zip_path, 'r') as fire_zip_ref:
                        fire_extracted_path = os.path.join(year_path, fire_zip[:-4])
                        fire_zip_ref.extractall(fire_extracted_path)
                        print(f'Extracted {fire_zip_path} to {fire_extracted_path}')
                    
                    tif_files = []
                    xml_file = None
                    for file_name in os.listdir(fire_extracted_path):
                        if file_name.endswith('.tif'):
                            tif_file_path = os.path.join(fire_extracted_path, file_name)
                            tif_files.append(tif_file_path)
                            print(f'Found TIF file: {tif_file_path}')
                        elif file_name.endswith('.xml'):
                            xml_file = os.path.join(fire_extracted_path, file_name)
                            print(f'Found XML file: {xml_file}')
                    
                    if xml_file:
                        fire_date, center_lat, center_lon = extract_fire_details(xml_file)
                    
                    if tif_files and fire_date is not None and center_lat is not None and center_lon is not None:
                        for tif_file in tif_files:
                            average_severity = extract_and_calculate_average(tif_file)
                            if average_severity is not None:
                                fire_id = fire_zip.split('_')[0]
                                results.append({
                                    'fire_id': fire_id,
                                    'file_name': os.path.basename(tif_file),
                                    'average_severity': average_severity,
                                    'fire_date': fire_date,
                                    'center_lat': center_lat,
                                    'center_lon': center_lon
                                })
                                print(f'Fire ID: {fire_id}, File: {os.path.basename(tif_file)}, Average Severity: {average_severity}, Date: {fire_date}, Center: ({center_lat}, {center_lon})')
    
    if results:
        df = pd.DataFrame(results)
        df.to_csv(output_csv_path, index=False)
        print(f'Results saved to {output_csv_path}')
    else:
        print('No results to save.')

# Example usage
zip_folder_path = 'Fire_data_bundles_vH1T2jxVNv7CtqPrPd4P.zip'
output_csv_path = 'output.csv'
process_fire_folders(zip_folder_path, output_csv_path)
