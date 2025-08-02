###########################
# This script will take osu! maps and extract features from them.
# The directories to each section can be edited in the config file. 
###########################

# Python library imports
import os
import sys
import random
import datetime
import pandas as pd
import config

# File-specific configurations
JUMP_DISTANCE_THRESHOLD = 120
JUMP_BEAT_THRESHOLD = 1 # 1 beat

BURST_DISTANCE_THRESHOLD = 60
BURST_BEAT_THRESHOLD = 1/4 # 16th notes

SPEED_THRESHOLD = 185 #time in ms

FEATURES = [
    "jump_count",
    "small_jumps_instances",
    "medium_jumps_instances",
    "large_jumps_instances",
    "total_jump_instances",
    "jump_density",

    "burst_count",
    "burst_instances",
    "burst_density",

    "stream_count",
    "stream_instances",
    "stream_density",

    "fast_density",

    "hp_drain",
    "circle_size",
    "overall_difficulty",
    "approach_rate",
    "slider_multiplier",
    "slider_tick_rate"
]

# Function to print with timestamp
def tsprint(s):
    print("[" + datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S") + "] " + s)


def extract_features_from_folder(maps_path):
    # Get all the maps
    tsprint("Extracting features from maps...")
    maps = os.listdir(maps_path)

    # Generate pandas dataframe
    df = pd.DataFrame(columns = ["map_id"] + FEATURES)

    # Loop through the maps
    for m in maps:
        # Get the map path
        map_file = os.path.join(maps_path, m)
        features = extract_features(map_file)

        # Add the map and its features to the dataframe
        df.loc[len(df)] = [m] + [features[f] for f in FEATURES]
    
    # Save the dataframe to a csv file
    df.to_csv(config.extraction_file, index=False)

def extract_features(map_file):
    flag = False
    with open(map_file, "r", encoding="utf-8") as f:
        lines = f.readlines()

    # Get the bpms (and their switches)
    timing_points = []
    for line in lines:
        if line.startswith("[TimingPoints]"):
            flag = True
            continue
        
        if(flag):
            if line.startswith("[") or line == "\n" or line == " \n":
                flag = False
                break
            timing_point = {}
            timing_point["time"] = float(line.split(",")[0])
            timing_point["beat_length"] = float(line.split(",")[1])
            timing_point["meter"] = int(line.split(",")[2])

            timing_points.append(timing_point)
    
    # Get difficulty stats
    diff = {}
    for line in lines:
        if line.startswith("[Difficulty]"):
            flag = True
            continue

        if(flag):
            if line.startswith("[") or line == "\n" or line == " \n":
                flag = False
                break
            diff[line.split(":")[0]] = line.split(":")[1].strip()

        
    # Get the hit objects
    hit_objects = []
    for line in lines:
        if line.startswith("[HitObjects]"):
            flag = True
            continue

        if(flag):
            if line.startswith("[") or line == "\n" or line == " \n":
                flag = False
                break
            hit_object = {}
            hit_object["x"] = int(line.split(",")[0])
            hit_object["y"] = int(line.split(",")[1])
            hit_object["time"] = int(line.split(",")[2])
            hit_object["type"] = int(line.split(",")[3])
            hit_object["is_hitcircle"] = hit_object["type"] & 1
            hit_object["is_slider"] = hit_object["type"] & 2
            hit_object["is_spinner"] = hit_object["type"] & 8

            hit_objects.append(hit_object)
        
    tsprint(f"Map {map_file.split("/")[1]} has {len(timing_points)} timing points and {len(hit_objects)} hit objects. Starting feature extraction...")


    ##############################
    # Features to extract
    ##############################


    features = {}

    # Overall features
    features["hp_drain"] = float(diff["HPDrainRate"]) if "HPDrainRate" in diff else -1
    features["circle_size"] = float(diff["CircleSize"]) if "CircleSize" in diff else -1
    features["overall_difficulty"] = float(diff["OverallDifficulty"]) if "OverallDifficulty" in diff else -1
    features["approach_rate"] = float(diff["ApproachRate"]) if "ApproachRate" in diff else -1
    features["slider_multiplier"] = float(diff["SliderMultiplier"]) if "SliderMultiplier" in diff else -1
    features["slider_tick_rate"] = float(diff["SliderTickRate"]) if "SliderTickRate" in diff else -1

    # Jump features
    jump_count = 0
    small_jumps_instances = 0
    medium_jumps_instances = 0
    large_jumps_instances = 0
    total_jump_instances = 0
    jump_density = 0

    # deep copy timing points
    timing_points_copy = []
    for tp in timing_points:
        timing_points_copy.append(tp.copy())

    timing_points_copy = list(filter(lambda x: x["beat_length"] > 0, timing_points_copy))
    
    jumps = 0

    i = 0
    while i < len(hit_objects) - 1:

        while hit_objects[i]["time"] > timing_points_copy[0]["time"]:
            if len(timing_points_copy) == 1:
                break
            timing_points_copy.pop(0)

        current_beat_length = timing_points_copy[0]["beat_length"]

        distance = ((hit_objects[i]["x"] - hit_objects[i + 1]["x"]) ** 2 + (hit_objects[i]["y"] - hit_objects[i + 1]["y"]) ** 2) ** 0.5 # use euclidean distance
        time = hit_objects[i + 1]["time"] - hit_objects[i]["time"]

        # if a jump is found, keep checking for more consecutive jumps
        while distance > JUMP_DISTANCE_THRESHOLD and time < JUMP_BEAT_THRESHOLD * current_beat_length and i < len(hit_objects) - 2:
            jumps += 1
            jump_count += 1
            i += 1
            
            distance = ((hit_objects[i]["x"] - hit_objects[i + 1]["x"]) ** 2 + (hit_objects[i]["y"] - hit_objects[i + 1]["y"]) ** 2) ** 0.5
            time = hit_objects[i + 1]["time"] - hit_objects[i]["time"]

        if jumps > 0:
            if jumps < 3:
                small_jumps_instances += 1
            elif jumps < 6:
                medium_jumps_instances += 1
            else:
                large_jumps_instances += 1
        
        jumps = 0
        i += 1
    
    jump_density = jump_count / len(hit_objects)

    features["jump_count"] = jump_count
    features["small_jumps_instances"] = small_jumps_instances
    features["medium_jumps_instances"] = medium_jumps_instances
    features["large_jumps_instances"] = large_jumps_instances
    features["total_jump_instances"] = small_jumps_instances + medium_jumps_instances + large_jumps_instances
    features["jump_density"] = jump_density

    # Burst/Stream features
    bursts = 0
    burst_count = 0
    burst_instances = 0
    burst_density = 0

    stream_count = 0
    stream_instances = 0
    stream_density = 0
    
    timing_points_copy = []
    for tp in timing_points:
        timing_points_copy.append(tp.copy())

    timing_points_copy = list(filter(lambda x: x["beat_length"] > 0, timing_points_copy))

    i = 0
    while i < len(hit_objects) - 1:

        while hit_objects[i]["time"] > timing_points_copy[0]["time"]:
            if len(timing_points_copy) == 1:
                break
            timing_points_copy.pop(0)
        
        current_beat_length = timing_points_copy[0]["beat_length"]

        distance = ((hit_objects[i]["x"] - hit_objects[i + 1]["x"]) ** 2 + (hit_objects[i]["y"] - hit_objects[i + 1]["y"]) ** 2) ** 0.5
        time = hit_objects[i + 1]["time"] - hit_objects[i]["time"]

        while distance < BURST_DISTANCE_THRESHOLD and time < JUMP_BEAT_THRESHOLD * current_beat_length and i < len(hit_objects) - 2:
            bursts += 1
            i += 1

            distance = ((hit_objects[i]["x"] - hit_objects[i + 1]["x"]) ** 2 + (hit_objects[i]["y"] - hit_objects[i + 1]["y"]) ** 2) ** 0.5
            time = hit_objects[i + 1]["time"] - hit_objects[i]["time"]
        
        if bursts > 8:
            stream_count += bursts
            stream_instances += 1
        elif bursts >= 3:
            burst_count += bursts
            burst_instances += 1
        

        bursts = 0
        i += 1

    burst_density = burst_count / len(hit_objects)
    stream_density = stream_count / len(hit_objects)

    features["burst_count"] = burst_count
    features["burst_instances"] = burst_instances
    features["burst_density"] = burst_density
    
    features["stream_count"] = stream_count
    features["stream_instances"] = stream_instances
    features["stream_density"] = stream_density


    # Speed features
    fast_density = 0
    i = 0

    while i < len(hit_objects) - 1:
        distance = ((hit_objects[i]["x"] - hit_objects[i + 1]["x"]) ** 2 + (hit_objects[i]["y"] - hit_objects[i + 1]["y"]) ** 2) ** 0.5
        time = hit_objects[i + 1]["time"] - hit_objects[i]["time"]

        if time < SPEED_THRESHOLD:
            fast_density += 1
        
        i += 1
    
    fast_density = fast_density / len(hit_objects)

    features["fast_density"] = fast_density


    return features




if __name__ == "__main__":
    extract_features_from_folder(config.map_folder)



