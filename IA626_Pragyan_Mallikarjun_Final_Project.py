#IA626 Final Project
#Author: Pragyan Kadel, Mallikarjun Banelli Reddy
#Date: 12-11-2025

import csv
import requests
import datetime
import numpy as np
import matplotlib.pyplot as plt
import cartopy.crs as ccrs
import cartopy.io.img_tiles as cimgt
import matplotlib.pyplot as plt



#Function that gets the list of Latitude and Longitude of the complaints for the supplied date range
def get_311_points_range(start_date: str, end_date: str):
    url = "https://data.cityofnewyork.us/resource/erm2-nwe9.json"
    start = f"{start_date}T00:00:00"
    end   = f"{end_date}T23:59:59"
    params = {"$select": "created_date, latitude, longitude","$where": (f"created_date BETWEEN '{start}' AND '{end}' ""AND latitude IS NOT NULL AND longitude IS NOT NULL"),"$limit": 50000}
    resp = requests.get(url, params=params)
    data = resp.json()
    lats = []
    lons = []
    for item in data:
        lats.append(float(item["latitude"]))
        lons.append(float(item["longitude"]))
    return np.array(lats), np.array(lons)



#Function that gets the list of Latitude and Longitude of the arrests for the supplied date range
def get_arrests_points_range(csv_file: str, start_date: str, end_date: str):
    start_dt = datetime.datetime.strptime(start_date, "%Y-%m-%d")
    end_dt = datetime.datetime.strptime(end_date, "%Y-%m-%d")
    lats = []
    lons = []
    with open(csv_file, newline='') as infile:
        reader = csv.DictReader(infile)
        for row in reader:
            arrest_date = row.get("ARREST_DATE")
            if arrest_date:
                arrest_dt = datetime.datetime.strptime(arrest_date, "%m/%d/%Y")
                if start_dt <= arrest_dt <= end_dt:
                    lat = row.get("Latitude")
                    lon = row.get("Longitude")
                    if lat and lon:
                        lats.append(float(lat))
                        lons.append(float(lon))
    return np.array(lats), np.array(lons)



#Function to count the Arrests and Complaints for each grid in the map and plot the ratio of (Arrests/Complaints) for each grid cell over a date range
def plot_grid_range(csv_file: str, start_date: str, end_date: str, bins: int = 60):
    #Getting the Latitudes and Longitudes of the Complaints
    lat_311, lon_311 = get_311_points_range(start_date, end_date)

    #Getting the Latitudes and Longitudes of the Arrests
    lat_arr, lon_arr = get_arrests_points_range(csv_file, start_date, end_date)

    #Getting the maximum and minimum Latitude and Longitude to Plot
    all_lats = np.concatenate([lat_311, lat_arr])
    all_lons = np.concatenate([lon_311, lon_arr])
    lat_min, lat_max = all_lats.min(), all_lats.max()
    lon_min, lon_max = all_lons.min(), all_lons.max()

    #Plotting the Grid boundary based on the max and min Latitude and Longitude Obtained
    arrests_hist, y_edges, x_edges = np.histogram2d(lat_arr, lon_arr, bins=bins, range=[[lat_min, lat_max], [lon_min, lon_max]])
    complaints_hist, _, _ = np.histogram2d(lat_311, lon_311, bins=[y_edges, x_edges])

    #Caluclating the Ratio of Arrests to Compalints for each grid cell in the map
    ratio = np.zeros_like(arrests_hist, dtype=float)

    #Masking the grids that have 0 complaints to avoid divided by zero error
    nonzero = complaints_hist > 0
    ratio[nonzero] = arrests_hist[nonzero] / complaints_hist[nonzero]
    mask = (complaints_hist == 0) & (arrests_hist == 0)
    ratio_masked = np.ma.array(ratio, mask=mask)
    ratio_masked.set_fill_value(np.nan)

    #Plotting the grid superimposed on the map of NYC
    tiler = cimgt.OSM()
    mercator = tiler.crs
    fig = plt.figure(figsize=(8, 8))
    ax = plt.axes(projection=mercator)
    ax.set_extent([lon_min, lon_max, lat_min, lat_max], crs=ccrs.PlateCarree())
    ax.add_image(tiler, 12, alpha=0.4)
    vmax = np.nanpercentile(ratio_masked.compressed(), 95)
    cmap = plt.cm.inferno
    cmap.set_bad(alpha=0.0)
    im = ax.imshow(ratio_masked,origin="lower",extent=[lon_min, lon_max, lat_min, lat_max],transform=ccrs.PlateCarree(),cmap=cmap,alpha=1.0,interpolation="nearest",vmin=0,vmax=vmax,)
    cbar = fig.colorbar(im, ax=ax, orientation="vertical", shrink=0.7)
    cbar.set_label("Arrests / Complaints")
    ax.set_title(f"Proportion of Arrests by 311 Complaints\n{start_date} to {end_date}")
    plt.show()



# Get number of days in a month
def days_in_month(year: int, month: int) -> int:
    if month == 12:
        next_month = datetime.date(year + 1, 1, 1)
    else:
        next_month = datetime.date(year, month + 1, 1)
    this_month = datetime.date(year, month, 1)
    return (next_month - this_month).days



# Function to plot daily counts of arrests and complaints for a given month/year
def plot_daily(csv_file: str, year: int, month: int):
    # Build list of all dates in the month
    n_days = days_in_month(year, month)
    dates = [datetime.date(year, month, d) for d in range(1, n_days + 1)]
    date_strs_api = [d.strftime("%Y-%m-%d") for d in dates]       # for 311 API
    date_strs_csv = [d.strftime("%m/%d/%Y") for d in dates]       # for NYPD CSV

    # Count complaints per day
    complaints_counts = []
    for ds in date_strs_api:
        lat_311, lon_311 = get_311_points_range(ds)
        complaints_counts.append(len(lat_311))

    # Count arrests per day
    arrests_counts = [0] * n_days
    with open(csv_file, newline="") as infile:
        reader = csv.DictReader(infile)
        for row in reader:
            arrest_date = row.get("ARREST_DATE")
            if arrest_date in date_strs_csv:
                idx = date_strs_csv.index(arrest_date)
                arrests_counts[idx] += 1

    # Plot
    days = list(range(1, n_days + 1))
    plt.figure(figsize=(10, 6))
    width = 0.4
    plt.bar([d - width / 2 for d in days], arrests_counts, width=width, label="Arrests", alpha=0.7)
    plt.bar([d + width / 2 for d in days], complaints_counts, width=width, label="311 Complaints", alpha=0.7)
    plt.xlabel("Day of Month")
    plt.ylabel("Count")
    plt.title(f"Daily Arrests and 311 Complaints in NYC - {year}-{month:02d}")
    plt.xticks(days)
    plt.legend()
    plt.tight_layout()
    plt.show()



#Unit Test
csv_file = "NYPD_Arrests_Data.csv"
plot_grid_range(csv_file, "2020-01-01", "2020-12-31", bins=50)
plot_grid_range(csv_file, "2021-01-01", "2021-12-31", bins=50)
plot_grid_range(csv_file, "2022-01-01", "2022-12-31", bins=50)
plot_daily("NYPD_Arrests_Data.csv", year=2022, month=11)