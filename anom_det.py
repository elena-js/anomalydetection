# ANOMALY DETECTION - USING DIFFERENT METHODS ---------------------------------------------------------------------

# Libraries
import pickle
import os
import math
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from fastdtw import fastdtw
from sklearn.cluster import AgglomerativeClustering
from sklearn.ensemble import IsolationForest
from collections import Counter

print('\n*ANOMALY DETECTION*')

# Analyze the data of one specific user -----------------------------------------------------

### COMMON USERS OF ORIGINAL AND NEW FILES: 13 (hr, int and steps)
# 2022484408: 42 days (28), 2026352035: 5 days (0), 2347167796: 32 days (21), 4020332650: 27 days (6), 
# 4558609924: 42 days (9), 5553957443: 42 days (25), 5577150313: 39 days (27-error), 6117666160: 31 days (21), 
# 6775888955: 26 days (3), 6962181067: 44 days (17), 7007744171: 35 days (26), 8792009665: 29 days (18), 
# 8877689391: 42 days (37)

user = 8877689391
print(f'\nUSER {user}')

# Read the data and obtain the variables
with open(f'data_user{user}.pkl', 'rb') as f:
    data = pickle.load(f)
# Show all columns of the dataframe
pd.set_option('display.max_columns', None)
#print(data)

# Variables of the system
day_time = data['Time'].tolist()
day_hr = data['HeartRate'].tolist()
day_int = data['Intensity'].tolist()
day_steps = data['Steps'].tolist()

# Calculate number of days
n_days = len(day_time)
print(f'Number of days: {n_days}')

# Compute distance matrix (DTW distances)
distance_matrix = np.zeros((len(day_hr), len(day_hr)))
for i in range(len(day_hr)):
    for j in range(i, len(day_hr)):
        distance_matrix[i, j] = fastdtw(day_hr[i], day_hr[j])[0]
        distance_matrix[j, i] = distance_matrix[i, j]

# Store the average day of each cluster in a dataframe
av_profiles = pd.DataFrame()


# COMMON FUNCTIONS

# Function to apply format to the figures
def plot_format(fig_title, fig_name, folder=None, cl=None, k=None):

    if cl is not None:
        fig_title = f', Cluster {cl}{fig_title}'
        fig_name = f'_cluster_{cl}{fig_name}'

    # Format for the figure
    plt.xlabel('Time')
    plt.ylabel('Heart rate')
    if folder is None:
        plt.title(f'{fig_title}')
    elif k is None:
        plt.title(f'Isolation Forest{fig_title}')
    else:
        plt.title(f'Agglomerative Clustering k={k}{fig_title}')
    plt.xticks(rotation=45)

    # Format hh:mm
    plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))  
    plt.gca().xaxis.set_minor_formatter(mdates.DateFormatter('%H:%M'))  

    plt.ylim(30, 220)
    plt.grid(True)
    plt.legend()

    # Verify if the folder exists
    if folder and not os.path.exists(f'figures/user{user}/{folder}'):
        os.makedirs(f'figures/user{user}/{folder}')
    # Save the figure
    if folder is None:
        plt.savefig(f'figures/user{user}/{fig_name}.png', bbox_inches='tight')
    elif k is None:
        plt.savefig(f'figures/user{user}/{folder}/iso{fig_name}.png', bbox_inches='tight')
    else:
        plt.savefig(f'figures/user{user}/{folder}/{k}_agglom{fig_name}.png', bbox_inches='tight')
    #plt.show()
    plt.clf()
    return

# Function for the anomaly detection of the modules - from clustering results
def anom_det_module(k, k_labels, anom_threshold, folder):

    print(f'Anomaly threshold: {anom_threshold}')

    # PLOT THE CLUSTERING RESULTS -----------------------------------------------------------

    # One figure for each cluster
    for cluster in np.unique(k_labels):

        # The ids of the arrays of the cluster
        cluster_ids = np.where(k_labels == cluster)[0]

        # Create the figure
        plt.figure(figsize=(20, 10))
        # Plot for each day
        for day_index in cluster_ids:
            days = day_time[day_index]
            # Store the date for each day
            day = days[0].strftime('%m-%d')
            # Put a common date for all the days - to make a representation of hh:min
            times = [dt.replace(year=2000, month=1, day=1) for dt in days]

            plt.plot(times, day_hr[day_index], label=f'{day}', alpha=0.5)    
        
        # Create a dataframe with the days of the cluster 
        df = pd.DataFrame({'Date': [day_time[i] for i in cluster_ids], 'HeartRate': [day_hr[i] for i in cluster_ids]})

        # Calculate the AVERAGE PROFILE of the cluster

        # Expand the values of dates and heartrates to have one sample for each date/hr
        df_expanded = df.explode(['Date', 'HeartRate'])
        # Put a common date for all the days - to take into consideration only hh:min
        df_expanded['Time'] = df_expanded['Date'].apply(lambda x: x.replace(year=2000, month=1, day=1))

        # Calculate an average value of hr for each value of time (each min)
        average_profile = df_expanded.groupby('Time')['HeartRate'].mean()
        # Maintain the names of the original columns
        average_profile = average_profile.reset_index()
        # Obtain the arrays with the time and hr values
        average_times = average_profile['Time'].tolist()
        average_hrs = average_profile['HeartRate'].tolist()

        # Store the average profile variables
        av_profiles[f'Cluster{cluster}Time'] = average_profile['Time']
        av_profiles[f'Cluster{cluster}HR'] = average_profile['HeartRate']

        # Plot the average profile (in the same figure)
        plt.plot(average_times, average_hrs, label='Average profile', linewidth=2, color='black')

        # Apply format to the figure
        plot_format(fig_title='', fig_name='', folder=folder, cl=cluster, k=k)

    # PLOT THE AVERAGE PROFILES OF ALL CLUSTERS ---------------------------------------------
    for cluster in np.unique(k_labels):
        plt.plot(av_profiles[f'Cluster{cluster}Time'], av_profiles[f'Cluster{cluster}HR'], label=f'Cluster {cluster}', alpha=0.5)  

    # Apply format to the figure
    plot_format(fig_title=', Average Profiles', fig_name='_avg', folder=folder, k=k)

# Calculate DISTANCES TO CLUSTER --------------------------------------------------------

    # Store distances from each day to its nearest cluster
    dist_to_cluster = []
    # Store hrs and times of all days in the clusters order
    dist_hrs = []
    dist_times = []

    for cluster in np.unique(k_labels):
        # The ids of the arrays for the cluster
        cluster_ids = np.where(k_labels == cluster)[0]
        # The variables with the days hr and time values
        cluster_days_hr = [day_hr[i] for i in cluster_ids]
        cluster_days_time = [day_time[i] for i in cluster_ids]
        # Heart rate vector of typical day in the cluster
        typical_day_hr = av_profiles[f'Cluster{cluster}HR'].tolist()
        # Calculate x most distant days from the typical one - using fastdtw distances
        dtw_dist = [fastdtw(typical_day_hr, day)[0] for day in cluster_days_hr]
        # Store the days with their distances in the dataframe
        dist_to_cluster.extend(dtw_dist)
        dist_hrs.extend(cluster_days_hr)
        dist_times.extend(cluster_days_time)

    # PLOT MOST DISTANT DAYS FROM ALL CLUSTERS ----------------------------------------------
    
    # Check the values of the distances to select a good anomaly threshold
    #print([int(x) for x in sorted(dist_to_cluster)])

    # Calculate the ids of the most distant days - using an anomaly threshold
    # If anomaly threshold is a % of days
    if anom_threshold < 1:
        # Number of anomalies - rounded up
        n_anom = math.ceil(n_days * anom_threshold)
        most_distant_days_ids = sorted(range(len(dist_to_cluster)), key=lambda i: dist_to_cluster[i], reverse=True)[:n_anom]
    # If anomaly threshold is max distance allowed
    else:
        most_distant_days_ids = [id for id, value in enumerate(dist_to_cluster) if value > anom_threshold]

    # Obtain dates of anomalous days
    anom_dates = [dist_times[i][0].date() for i in most_distant_days_ids]

    # If a cluster has less than 3 days it can be considered as an anomaly
    min_days_in_cluster = 2
    ids = [id for id, label in enumerate(k_labels) if np.bincount(k_labels)[label] <= min_days_in_cluster]
    anom_dates.extend([day_time[i][0].date()] for i in ids)

    # Obtain hr and time values for anomalous days
    most_distant_days_time = [day for day in day_time if day[0].date() in anom_dates]
    most_distant_days_hr = [hr for day, hr in zip(day_time, day_hr) if day[0].date() in anom_dates]

    # Print those days (month-day)
    print(f"Anomalies: {len(most_distant_days_ids)}")
    anom_days = [day[0].strftime('%m-%d') for day in most_distant_days_time]
    print(anom_days)

    # For each day from the list of most distants
    for day, hr in zip(most_distant_days_time, most_distant_days_hr):
        # Adjust the date to be the same in all vectors - only use of hh:min
        time = [dt.replace(year=2000, month=1, day=1) for dt in day]
        # Plot most distant days
        plt.plot(time, hr, label=f"{day[0].strftime('%m-%d')}", alpha=0.5)
    
    # Apply format to the figure
    plot_format(fig_title=', Most Distant Days', fig_name='_most_dist', folder=folder, k=k)

    return anom_days
    
print('\nANOMALY DETECTION SYSTEMS:')

# -----------------------------------------------------------------------------------------------------------
# ANOMALY DETECTION - AGGLOMERATIVE CLUSTERING AND DTW DISTANCES --------------------------------------------
## USING HEART RATE

# Function to detect anomalies with clustering by heart rate data
def anom_det_hr(k, anom_threshold):
    
    # CLUSTERING using Agglomerative Clustering ---------------------------------------------
    
    # Clustering with heart rate distance matrix
    def cluster_dst_mtx():
        # For introducing distance matrix - affinity='precomputed'
        clustering = AgglomerativeClustering(n_clusters=k, affinity='precomputed', linkage='ward')
        k_labels = clustering.fit_predict(distance_matrix)
        print('Features used: HeartRate (distance matrix)')
        return k_labels

    # Clustering with heart rate vectors
    def cluster_hr_vectors():
        clustering = AgglomerativeClustering(n_clusters=k, linkage='ward')
        X = np.array(day_hr)
        k_labels = clustering.fit_predict(X)
        print('\nFeatures used: HeartRate (vectors)')
        return k_labels
    
    # Clustering with statistics of heart rate
    def cluster_stats():
        clustering = AgglomerativeClustering(n_clusters=k, linkage='ward')
        X = data[['Max', 'Min', 'Mean', 'Median', 'Std_dev']]
        X = np.array(X)
        k_labels = clustering.fit_predict(X)
        print('\nFeatures used: HeartRate (Max, Min, Mean, Median, Std_dev)')
        return k_labels

    # Clustering with all statistics of heart rate (including medical ones)
    def cluster_all_stats():
        clustering = AgglomerativeClustering(n_clusters=k, linkage='ward')
        X = data[['Max', 'Min', 'Mean', 'Median', 'Std_dev', 'RMSSD', 'pNN50']]
        X = np.array(X)
        k_labels = clustering.fit_predict(X)
        print('\nFeatures used: HeartRate (Max, Min, Mean, Median, Std_dev, RMSSD, pNN50)')
        return k_labels

    # ANOMALY DETECTION from clustering results  --------------------------------------------
    k_labels_1 = cluster_hr_vectors()
    anom_days_1 = anom_det_module(k, k_labels_1, anom_threshold, '1_hr_vec')

    k_labels_2 = cluster_all_stats()
    anom_days_2 = anom_det_module(k, k_labels_2, anom_threshold, '2_hr_stats')

    return anom_days_1, anom_days_2

# Clustering with k = 3, 10% of anomalies
anom_days_hr_1, anom_days_hr_2 = anom_det_hr(k=4, anom_threshold=0.1)

# -----------------------------------------------------------------------------------------------------------
## USING INTENSITIES ----------------------------------------------------------------------------------------

# Function to detect anomalies with clustering by intensity data
def anom_det_int(k, anom_threshold):
    
    # CLUSTERING using Agglomerative Clustering ---------------------------------------------

    # Clustering with intensity vectors
    def cluster_int_vectors():
        clustering = AgglomerativeClustering(n_clusters=k, linkage='ward')
        X = np.array(day_int)
        k_labels = clustering.fit_predict(X)
        print('\nFeatures used: Intensity (vectors)')
        return k_labels
    k_labels = cluster_int_vectors()

    # ANOMALY DETECTION from clustering results  --------------------------------------------
    anom_days = anom_det_module(k, k_labels, anom_threshold, '3_int')

    return anom_days
    
# Clustering with k = 3
anom_days_int = anom_det_int(k=4, anom_threshold=0.1)

# -----------------------------------------------------------------------------------------------------------
## USING STEPS ----------------------------------------------------------------------------------------------

# Function to detect anomalies with clustering by steps data
def anom_det_steps(k, anom_threshold):
    
    # CLUSTERING using Agglomerative Clustering ---------------------------------------------

    # Clustering with steps vectors
    def cluster_step_vectors():
        clustering = AgglomerativeClustering(n_clusters=k, linkage='ward')
        X = np.array(day_steps)
        k_labels = clustering.fit_predict(X)
        print('\nFeatures used: Steps (vectors)')
        return k_labels
    k_labels = cluster_step_vectors()

    # ANOMALY DETECTION from clustering results  --------------------------------------------
    anom_days = anom_det_module(k, k_labels, anom_threshold, '4_steps')

    return anom_days
    
# Clustering with k = 3
anom_days_steps = anom_det_steps(k=5, anom_threshold=0.1)

# -----------------------------------------------------------------------------------------------------------
## USING HEART RATE / STEPS ---------------------------------------------------------------------------------

# Function to detect anomalies with clustering by steps data
def anom_det_hr_steps(k, anom_threshold):
    
    # CLUSTERING using Agglomerative Clustering ---------------------------------------------

    # Clustering with steps vectors
    def cluster_hr_step_vectors():
        day_hr_steps = [ [hr / step if step != 0 else hr for hr, step in zip(hrs, steps)]
                        for hrs, steps in zip(day_hr, day_steps) ]
        clustering = AgglomerativeClustering(n_clusters=k, linkage='ward')
        X = np.array(day_hr_steps)
        k_labels = clustering.fit_predict(X)
        print('\nFeatures used: HeartRate/Steps (vectors)')
        return k_labels
    k_labels = cluster_hr_step_vectors()

    # ANOMALY DETECTION from clustering results  --------------------------------------------
    anom_days = anom_det_module(k, k_labels, anom_threshold, '5_hr_steps')

    return anom_days
    
# Clustering with k = 3
anom_days_hr_steps = anom_det_hr_steps(k=3, anom_threshold=0.1)


# -----------------------------------------------------------------------------------------------------------
# ANOMALY DETECTION - ISOLATION FOREST ----------------------------------------------------------------------

# Isolation Forest with heart rate distance matrix
def isol_forest_dist_mtx(x): 
    
    print("\nIsolation Forest with distance matrix:")

    # Create the model IsolationForest
    model = IsolationForest()
        # n_estimators - number of trees in the forest
        # contamination - % of outliers in data

    # Fit the model to the distance matrix
    model.fit(distance_matrix)

    # Predict the anomaly scores for each data point
    anomaly_scores = model.decision_function(distance_matrix)

    # Calculate the ids of the most distant days (in order of higher to smaller anomaly scores)
    most_distant_days_ids = sorted(range(len(anomaly_scores)), key=lambda i: anomaly_scores[i], reverse=True)[:x]
    # Obtain hr and time values for those days
    most_distant_days_time = [day_time[i] for i in most_distant_days_ids]
    most_distant_days_hr = [day_hr[i] for i in most_distant_days_ids]

    # Create the figure
    plt.figure(figsize=(20, 10))
    
    # For each day from the list of most distants
    for day, hr in zip(most_distant_days_time, most_distant_days_hr):
        # Adjust the date to be the same in all vectors - only use of hh:min
        time = [dt.replace(year=2000, month=1, day=1) for dt in day]
        # Plot most distant days
        plt.plot(time, hr, label=f"{day[0].strftime('%m-%d')}", alpha=0.5)
        
    # Apply format to the figure
    plot_format(fig_title=f', {x} Most Distant Days', fig_name='_most_dist')

    # Print the anomalous days (month-day)
    print(f"Anomalies: {x}")
    anom_days = [day[0].strftime('%m-%d') for day in most_distant_days_time]
    print(anom_days)

# Select the number of days to plot - x
#isol_forest_dist_mtx(3)

# Isolation Forest with heart rate vectors
def isol_forest_only_vec():
    
    print("\nIsolation Forest with HR vectors:")

    # Create the model IsolationForest
    model = IsolationForest(random_state=42)
        # n_estimators - number of trees in the forest
        # contamination - % of outliers in data

    # To obtain also the indexes
    length = 500
    day_ids, day_hr_updated = zip(*[(index, hr) for index, hr in enumerate(day_hr) if len(hr) >= length])
    day_hr_updated = [[hr for hr in arr[:length]] for arr in day_hr_updated]
    day_time_updated = [day_time[id] for id in day_ids]
    day_time_updated = [[time for time in arr[:length]] for arr in day_time_updated]

    # Create a new dataframe with the updated info (same length vectors)
    data_updated = pd.DataFrame()
    data_updated['Time'] = day_time_updated
    data_updated['HeartRate'] = day_hr_updated
    #data_updated['Max'] = [data['Max'].values[id] for id in day_ids]
    #data_updated['Min'] = [data['Min'].values[id] for id in day_ids]
    #data_updated['Mean'] = [data['Mean'].values[id] for id in day_ids]
    #data_updated['Median'] = [data['Median'].values[id] for id in day_ids]
    #data_updated['Std_dev'] = [data['Std_dev'].values[id] for id in day_ids]
    #data_updated['RMSSD'] = [data['RMSSD'].values[id] for id in day_ids]
    #data_updated['pNN50'] = [data['pNN50'].values[id] for id in day_ids]

    X = day_hr_updated

    # Train the model and predict the anomalies
    anomalies = model.fit_predict(X)

    # Select only the info of the anomalous days
    anomalies_ids = np.where(anomalies == -1)[0]

    anom_days = [day_time_updated[id][0].strftime('%m-%d') for id in anomalies_ids]

    print(f"Anomalies: {len(anomalies_ids)}")
    print(anom_days)

#isol_forest_only_vec()

# Isolation Forest with all heart rate statistics (including medical ones)
def isol_forest_all_stats():
    
    print("\nIsolation Forest with all features:")

    # Create the model IsolationForest
    model = IsolationForest()
        # n_estimators - number of trees in the forest
        # contamination - % of outliers in data

    X = data[['Max', 'Min', 'Mean', 'Median', 'Std_dev', 'RMSSD', 'pNN50']]

    # Train the model and predict the anomalies
    anomalies = model.fit_predict(X)

    # Select only the info of the anomalous days (dataframe)
    anomalies_ids = np.where(anomalies == -1)[0]
    anomalies_data = data.iloc[anomalies_ids]
    #print(anomalies_data)

    # Print the anomalous days (month-day)
    print(f"Anomalies: {len(anomalies_ids)}")
    anom_days = [anomalies_data['Time'][id][0].strftime('%m-%d') for id in anomalies_ids]
    print(anom_days)

#isol_forest_all_stats()

# Isolation Forest with basic heart rate statistics (max,min,mean,median,std)
def isol_forest_basic_stats():
    
    print("\nIsolation Forest with basic features:")

    # Create the model IsolationForest
    model = IsolationForest()
        # n_estimators - number of trees in the forest
        # contamination - % of outliers in data

    X = data[['Max', 'Min', 'Mean', 'Median', 'Std_dev']]

    # Train the model and predict the anomalies
    anomalies = model.fit_predict(X)

    # Select only the info of the anomalous days
    anomalies_ids = np.where(anomalies == -1)[0]
    anomalies_data = data.iloc[anomalies_ids]
    #print(anomalies_data)

    # Print the anomalous days (month-day)
    print(f"Anomalies: {len(anomalies_ids)}")
    anom_days = [anomalies_data['Time'][id][0].strftime('%m-%d') for id in anomalies_ids]
    print(anom_days)

#isol_forest_basic_stats()


# -----------------------------------------------------------------------------------------------------------
# VOTING SYSTEM ---------------------------------------------------------------------------------------------

# As we have different methods, we have to get the best results considering all

def voting(anom_days_1, anom_days_2, anom_days_3, anom_days_4, anom_days_5):
    print('\nVOTING SYSTEM')
    # Combine the lists with all the possible anomalous days
    poss_anom_days = anom_days_1 + anom_days_2 + anom_days_3 + anom_days_4 + anom_days_5
    # Count the frequency of each day
    day_counts = Counter(poss_anom_days)
    # Consider as anomaly if a day appears at least 3 times (majority)
    anom_days = sorted([day for day, count in day_counts.items() if count >= 3])
    print(f'\nAnomalies found:\n{anom_days}')
    return anom_days

anom_days = voting(anom_days_hr_1,anom_days_hr_2, anom_days_int, anom_days_steps, anom_days_hr_steps)

# Create a figure with the anomalies
def plot_anomalies(anom_days):
    hr_anom = [hr for day, hr in zip(day_time, day_hr) if day[0].strftime('%m-%d') in anom_days]
    time_anom = [day for day in day_time if day[0].strftime('%m-%d') in anom_days]
    # Create the figure
    #plt.figure(figsize=(20, 10))
    for day, hr in zip(time_anom, hr_anom):
        # Adjust the date to be the same in all vectors - only use of hh:min
        time = [dt.replace(year=2000, month=1, day=1) for dt in day]
        # Plot most distant days
        plt.plot(time, hr, label=f"{day[0].strftime('%m-%d')}", alpha=0.5)
    # Apply format to the figure
    plot_format(fig_title='Anomalous Days', fig_name='_anom_days')

plot_anomalies(anom_days)

print()

# -----------------------------------------------------------------------------------------------------------------