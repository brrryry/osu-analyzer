###########################
# This script will collect osu! maps from an osu! API (beatconnect.io) and extract them.
# The directories to each section can be edited in the config file. 
###########################


# Python library imports
import requests
import zipfile
import io
import os
import random
import datetime
from concurrent.futures import ThreadPoolExecutor

# Osu API
import osu
from osu import Client

# import config
import config

# file-specific configurations!!
NUM_MAPS = 5000 #number of maps to fetch (including what is already there)


# Set up the osu! API client
client = Client.from_credentials(config.osu_api_client_id, config.osu_api_client_secret, config.osu_api_redirect_uri)


# Function to print with timestamp
def tsprint(s):
    print("[" + datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S") + "] " + s)


# Fetcher function to fetch a map
def fetch_map(map_id, difficulty_threshold = 5.0):
    tsprint(f'Fetching map {map_id}...')

    # Check if that map is already in the folder
    if os.path.exists(config.map_folder + map_id + "_0.osu"):
        tsprint(f'Map {map_id} is already in the folder!')
        return

    # Try to fetch the map
    try:
        # Fetch the map
        response = requests.get(os.path.join(config.api_link, map_id))
        response.raise_for_status()
        tsprint(f'Successfully fetched map {map_id}!')
    except:
        tsprint(f'Failed to fetch map {map_id} - got status code {response.status_code}')
        return
    
    # Extract the map in memory
    try:
        zip_file = zipfile.ZipFile(io.BytesIO(response.content))
    except:
        tsprint(f'Failed to extract map {map_id} - not a valid zip file')
        return
    
    count = 0 #count the number of osu files extracted from the zip

    # Loop through the files in the zip and extract the .osu files
    for file in zip_file.namelist():
        if file.endswith('.osu'):
            zip_file.extract(file, config.map_folder)


            # Confirm that the file is the right type of map (not mania or taiko)
            with open(config.map_folder + file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                
                # find the line that specifies the mode
                mode_line = [line for line in lines if line.startswith("Mode:")]
                if len(mode_line) == 0:
                    tsprint(f'Failed to find mode line in {file}')
                    os.remove(config.map_folder + file)
                    return
                
                # check if the mode is standard
                mode = int(mode_line[0].split(":")[1].strip())
                if mode != 0:
                    tsprint(f'Map {file} is not a standard map')
                    os.remove(config.map_folder + file)
                    return

                difficulty = [line for line in lines if line.startswith("OverallDifficulty:")]
                difficulty = int(difficulty[0].split(":")[1].strip())
                if difficulty < difficulty_threshold: 
                    os.remove(config.map_folder + file)
                    return
            
            # Rename the file to the map_id + count + .osu
            try:
                os.rename(config.map_folder + file, config.map_folder + map_id + "_" + str(count) + ".osu")
                count += 1
            except:
                tsprint(f'Failed to rename file {file} to {map_id}_{count}.osu')
                os.remove(config.map_folder + file) #remove the file if it cannot be renamed
                return

    tsprint(f'Successfully extracted {count} osu files from map {map_id}!')
    return



# Function to fetch maps!
def fetch_maps(num_maps = 100, difficulty_threshold = 5.0):
    page = 0
    while True:
        file_count = os.listdir(config.map_folder)
        if len(file_count) >= num_maps:
            break

        # fetch maps in batches
        filter = osu.util.BeatmapsetSearchFilter()
        filter.set_mode(osu.GameModeInt.STANDARD)
        filter.set_status(osu.BeatmapsetSearchStatus.RANKED)  
        filter.set_sort(osu.BeatmapsetSearchSort.PLAYS)

        tsprint(f'Fetched page {page} of maps...')

        beatmapsearchresult = client.search_beatmapsets(filters=filter)


        map_ids = [beatmapset.id for beatmapset in beatmapsearchresult.beatmapsets]

        # use concurrent threads to fetch maps
        with ThreadPoolExecutor() as executor:

            # call fetcher function on each map id concurrently
            futures = [executor.submit(fetch_map, str(map_id), difficulty_threshold) for map_id in map_ids]

            # wait for all threads to finish
            for future in futures:
                future.result()
            
        page += 1
    
    tsprint(f'Successfully fetched {num_maps} maps!')

# Main function...that's it
if __name__ == "__main__":

    # create maps folder if it does not exist
    if not os.path.exists(config.map_folder):
        os.makedirs(config.map_folder)

    #fetch this stuff
    fetch_maps(NUM_MAPS)