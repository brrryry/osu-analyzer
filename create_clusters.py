###########################
# This script will take extracted features and cluster them.
# The directories to each section can be edited in the config file.
###########################

# Python library imports
import os
import numpy as np 
import pandas as pd 
from matplotlib import pyplot as plt 
from sklearn.cluster import AgglomerativeClustering, KMeans, DBSCAN
from sklearn.preprocessing import StandardScaler
import seaborn as sns


# File-specific configurations
FEATURE_WEIGHTS = {
    
}

# take file and cluster
df = pd.read_csv("extracted_data.csv")

# drop map_id
df = df.drop(columns=["map_id"])

# drop all rows where overall difficulty < 5
df = df[df["overall_difficulty"] > 5]

df = df.drop(columns=["overall_difficulty"])
#df = df.drop(columns=["max_stream_length"])

print(f'Clustering based on {len(df.columns)} features')
print(f'Features: {df.columns}')

# normalize the data
df_scaled = df.copy()
scaler = StandardScaler()
df_scaled = scaler.fit_transform(df_scaled)

# print number of rows and columns
print(f"Rows: {df_scaled.shape[0]}")

# cluster the data
kmeans = DBSCAN(eps=0.5, min_samples=5)
kmeans_clusters = kmeans.fit_predict(df_scaled)


# only keep certain features for pair plot
#df = df[['jump_density', 'burst_density', 'stream_density']]

# add the clusters to the dataframe
df["kmeans_cluster"] = kmeans_clusters

# drop all rows where kmeans_cluster = -1
df = df[df["kmeans_cluster"] != -1]

# pair plot
sns.pairplot(df, hue="kmeans_cluster")
plt.show()

# get number of points in each cluster
print(df["kmeans_cluster"].value_counts())
