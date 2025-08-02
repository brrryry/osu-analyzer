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
JUMP_DISTANCE_THRESHOLD = 120 # 120 units
JUMP_BEAT_THRESHOLD = 1 # 1 beats

STREAM_BEAT_THRESHOLD = 1/4 # 16th notes

SPEED_THRESHOLD = 185 #time in ms

FEATURES = [

    #"average_notes_per_second", #average notes per second

    "jump_confidence", #confidence in jumps
    "stream_confidence", #confidence in streams


    "overall_difficulty" #overall difficulty of the map
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
        
    #tsprint(f"Map {map_file.split("/")[1]} has {len(timing_points)} timing points and {len(hit_objects)} hit objects. Starting feature extraction...")


    ##############################
    # Features extraction setup
    ##############################

    features = {}

    # Overall features
   
    #features["hp_drain"] = float(diff["HPDrainRate"]) if "HPDrainRate" in diff else -1
    #features["circle_size"] = float(diff["CircleSize"]) if "CircleSize" in diff else -1
    features["overall_difficulty"] = float(diff["OverallDifficulty"]) if "OverallDifficulty" in diff else -1
    #features["approach_rate"] = float(diff["ApproachRate"]) if "ApproachRate" in diff else -1
    #features["slider_multiplier"] = float(diff["SliderMultiplier"]) if "SliderMultiplier" in diff else -1
    #features["slider_tick_rate"] = float(diff["SliderTickRate"]) if "SliderTickRate" in diff else -1


    # Feature extraction
    hit_times = [h["time"] for h in hit_objects]
    hit_distances = [((hit_objects[i]["x"] - hit_objects[i+1]["x"])**2 + (hit_objects[i]["y"] - hit_objects[i+1]["y"])**2)**0.5 for i in range(len(hit_objects)-1)]

    # Get timing points to calculate beat length at each hit object
    hit_beat_lengths = []
    found = False
    for h in hit_objects[::-1]: #don't include the very last note.
        for t in timing_points:
            if t["time"] > h["time"] and t["beat_length"] > 0:
                found = True
                hit_beat_lengths.append(t["beat_length"])
                break

        # If no timing point is found, use the last timing point
        if(not found):
            # If no timing point is found, use the last non-negative timing point
            for t in timing_points[::-1]:
                if t["beat_length"] > 0:
                    hit_beat_lengths.append(t["beat_length"])
                    break
    
    # Get the beat length at each hit object
    hit_beat_lengths = [hit_beat_lengths[i] for i in range(len(hit_beat_lengths)-1)]

    ##############################
    # Feature extraction
    ##############################

    time_diffs = [hit_times[i+1] - hit_times[i] for i in range(len(hit_times)-1)]

    # Jump features
    jumps = 0
    jumps_total = 0
    small_jumps = 0
    medium_jumps = 0
    large_jumps = 0

    jump_lengths = []

    for i in range(len(hit_distances)):
        if hit_distances[i] > JUMP_DISTANCE_THRESHOLD and time_diffs[i] < JUMP_BEAT_THRESHOLD * hit_beat_lengths[i]:
            jumps += 1
        else: 
            if jumps >= 12:
                large_jumps += 1
            elif jumps >= 8:
                medium_jumps += 1
            elif jumps >= 4:
                small_jumps += 1
            
            
            if jumps >= 4: 
                jumps_total += jumps
                jump_lengths.append(jumps)
        
            jumps = 0

    jump_density = jumps_total / len(hit_objects)
    total_jumps = small_jumps + medium_jumps + large_jumps
    large_jumps_density = large_jumps / total_jumps if total_jumps > 0 else 0
    average_jump_length = sum(jump_lengths) / len(jump_lengths) if len(jump_lengths) > 0 else 0
    max_jump_length = max(jump_lengths) if len(jump_lengths) > 0 else 0

    features["jump_confidence"] = min((jump_density * 0.3)
    + (large_jumps_density * 0.4)
    + (min(average_jump_length / 7.0, 1.0) * 0.3)
    + (min(max_jump_length / 8.0, 1.0) * 0.3)
    , 1.0)


    # Stream features
    streams = 0
    streams_total = 0
    mini_streams = 0
    small_streams = 0
    medium_streams = 0
    large_streams = 0

    stream_lengths = []

    for i in range(len(hit_distances)):
        if time_diffs[i] < STREAM_BEAT_THRESHOLD * hit_beat_lengths[i]:
            streams += 1
        else: 
            if streams >= 19:
                large_streams += 1
            elif streams >= 13:
                medium_streams += 1
            elif streams >= 7:
                small_streams += 1
            elif streams >= 3:
                mini_streams += 1
            
            if streams >= 3:
                streams_total += streams 
                stream_lengths.append(streams)
        
            streams = 0

    stream_density = streams_total / len(hit_objects)
    total_streams = small_streams + medium_streams + large_streams + mini_streams
    large_streams_density = large_streams / (total_streams) if total_streams > 0 else 0
    average_stream_length = sum(stream_lengths) / len(stream_lengths) if len(stream_lengths) > 0 else 0
    max_stream_length = max(stream_lengths) if len(stream_lengths) > 0 else 0

    features["stream_confidence"] = min((stream_density * 0.3)
    + (large_streams_density * 0.4)
    + (min(average_stream_length / 7.0, 1.0) * 0.3)
    + (min(max_stream_length / 13.0, 1.0) * 0.3)
    , 1.0)



    return features




if __name__ == "__main__":
    extract_features_from_folder(config.map_folder)



