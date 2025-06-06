#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Utilitary functions to manage, check and preprocess large sampling data assiciated with passive acoustic monitoring

"""

import os
import matplotlib.pyplot as plt
from maad import sound, util
import pandas as pd
import numpy as np
import geopandas as gpd
import contextily as cx
import matplotlib.dates as mdates
import matplotlib as mpl
from matplotlib.colors import Normalize
import logging
from kedro_pamflow.pipelines.quality_control.utils import concat_audio
import datetime

logger = logging.getLogger(__name__)


def plot_sensor_performance(media):
    """Plots sensor performance to provide an overview of the sampling effort.

    This node visualizes the number of recordings per deployment over time.
    The input corresponds to the catalog entry `media@pamDP`, and the outputs
    are stored as a matplotlib figure summarizing the deployment activity and
    a processed DataFrame summarizing the number of recordings per deployment
    and day. The outputs are stored in the catalog as `sensor_deployment_plot@matplotlib`
    and `sensor_deployment_data@pandas`.

    Parameters
    ----------
    media : pandas.DataFrame
        A DataFrame containing metadata of media files, following the pamDP.media format.
        This is loaded from the catalog entry `media@pamDP`.

    Returns
    -------
    tuple
        - matplotlib.figure: A figure showing the deployment activity over time.
          This is stored in the catalog as `sensor_deployment_plot@matplotlib`.
        - pandas.DataFrame: A processed DataFrame summarizing the number of recordings
          per deployment and day. This is stored in the catalog as `sensor_deployment_data@pandas`.
    """

    # Group recordings by day
    media["timestamp"] = pd.to_datetime(media["timestamp"]).dt.date
    media_out = (
        media.groupby(["deploymentID", "timestamp"]).size().reset_index(name="count")
    )
    media_out.sort_values(by=["deploymentID", "timestamp"], inplace=True)

    # Sort the DataFrame based on the first date
    media_out["first_date"] = media_out.groupby("deploymentID")["timestamp"].transform(
        "min"
    )
    media_out = media_out.sort_values(by="first_date")

    # Plot settings
    # Dynamically adjust figure size
    unique_sensors = media_out["deploymentID"].nunique()
    unique_dates = media_out["timestamp"].nunique()
    width = min(max(6, unique_dates * 0.3), 12)
    height = min(max(4, unique_sensors * 0.3), 9)

    # Define scatter plot sizes based on 'count' (ensuring they match actual sizes)
    sizes = (media_out["count"] - media_out["count"].min() + 1) * 3  # Example scaling

    # Create a modified version of the 'Blues' colormap
    Blues_mod = mpl.colors.LinearSegmentedColormap.from_list(
        "Blues_mod", ["#b0c4de", "#08306b"]
    )
    x = "timestamp"
    y = "deploymentID"

    # Order dataframe to get ordered vertical axis
    media_out = media_out.sort_values(by=y, ascending=False)

    # Create a Normalize object for the count range
    count_min = media_out["count"].min()
    count_max = media_out["count"].max()

    # Handle the edge case where all values are equal
    if count_max == count_min:
        sizes = np.full(len(media_out), 50)
        colors = np.full(len(media_out), 1) 
        norm = None  # not needed in this case
    else:
        sizes = (media_out["count"] - count_min + 1) * 3
        norm = Normalize(vmin=count_min, vmax=count_max)
        colors = norm(media_out["count"])
    
    # Draw scatterplot
    fig, ax = plt.subplots(figsize=[width, height])
    scatter = ax.scatter(
        media_out[x],
        media_out[y],
        s=sizes,
        c=colors,
        cmap=Blues_mod,
        norm=norm if norm else None,
        alpha=1,
    )

    # Format date
    ax.xaxis.set_major_locator(mdates.DayLocator(interval=7))  # Every 7 days
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %d"))

    # Add title and set grid
    ax.grid(alpha=0.2)
    ax.set_title(
        f"Sensor Deployment: {media.deploymentID.nunique()} sites | {media.shape[0]} files"
    )
    
    # Create legend handles
    legend_values = np.linspace(
        media_out["count"].min(), media_out["count"].max(), num=4
    ).astype(int)
    if count_max == count_min:
        # All counts are equal — one legend handle with fixed size and color
        legend_handles = [
            plt.scatter(
                [],
                [],
                s=50,  # same as scatter plot
                color=Blues_mod(1),  # same as scatter plot
                label=f"{count_min}",
                alpha=1,
            )
        ]
    else:
        # Multiple values — create gradient-based legend handles
        legend_values = np.linspace(count_min, count_max, num=4).astype(int)
        legend_handles = [
            plt.scatter(
                [],
                [],
                s=(val - count_min + 1) * 3,
                color=Blues_mod(norm(val)),
                label=f"{int(val)}",
            )
            for val in legend_values
        ]
    
    # Adjust spines
    for spine in ax.spines.values():
        spine.set_linewidth(0.5)  # Adjust the thickness
        spine.set_color("gray")  # Change color to lighter gray

    # Add legend outside the plot
    ax.legend(
        handles=legend_handles, title="N. Rec", loc="upper left", bbox_to_anchor=(1, 1)
    )
    plt.xticks(rotation=45)
    plt.tight_layout()

    return fig, media_out


def plot_sensor_location(media_summary, deployments, plot_parameters):
    """Plots the geographic location of sensors and their recording activity.

    The inputs correspond to the catalog entries `media_summary@pandas` and
    `deployments@pamDP`. The output is stored in the catalog as
    `sensor_location_plot@matplotlib`.

    Parameters
    ----------
    media_summary : pandas.DataFrame
        A summary DataFrame for each deployment, including the start and end dates,
        number of recordings, and other statistics. Loaded from the catalog entry
        `media_summary@pandas`.

    deployments : pandas.DataFrame
        A DataFrame containing deployment metadata, including sensor locations
        (latitude and longitude). Loaded from the catalog entry `deployments@pamDP`.
        The DataFrame follows the pamDP.mdeployments format.

    plot_parameters : dict
        A dictionary containing parameters for the plot, such as colormap and figure size.

    Returns
    -------
    matplotlib.figure.Figure
        A figure showing the geographic distribution of sensors and their recording activity.
        Stored in the catalog as `sensor_location_plot@matplotlib`.
    """
    geo_info_microfonos = gpd.GeoDataFrame(
        deployments[["deploymentID", "latitude", "longitude"]],
        geometry=gpd.points_from_xy(
            deployments["longitude"],
            deployments["latitude"],
        ),
        crs="EPSG:4326",
    )

    geo_info_microfonos = geo_info_microfonos.merge(
        media_summary, on="deploymentID", how="left"
    )

    geo_info_microfonos = geo_info_microfonos.astype({"n_recordings": "float64"})

    fig, ax = plt.subplots(figsize=(10, 10))
    geo_info_microfonos.plot(
        ax=ax,
        # c=geo_info_microfonos['n_recordings'],
        column="n_recordings",
        cmap=plot_parameters["colormap"],
        legend=True,
    )

    # ax.legend(metadata_summary['n_recordings'])

    ax.set_title("Number of recordings per sensor")

    cx.add_basemap(
        ax,
        # source=xyz.OpenStreetMap.Mapnik,
        crs=geo_info_microfonos.crs.to_string(),
    )

    for x, y, label in zip(
        geo_info_microfonos.geometry.x,
        geo_info_microfonos.geometry.y,
        geo_info_microfonos.deploymentID,
    ):
        ax.annotate(
            label,
            xy=(x, y),
            xytext=(3, 3),
            textcoords="offset points",
            fontsize=0.15 * geo_info_microfonos["deploymentID"].nunique(),
            # rotation=np.random.choice([0,45,-45],p=[0.8,0.1,0.1])
        )
    return fig


def get_timelapse(
    sensor_deployment_data, media, sample_len, sample_period, plot_params
):
    """Generates audio timelapse spectrograms for each sensor deployment.

    This node processes media files and deployment data to create spectrograms
    summarizing the acoustic activity for a selected date. The inputs correspond
    to the catalog entries `sensor_deployment_data@pandas`, `media@pamDP`,
    `sample_len@int`, `sample_period@str`, and `plot_params@dict`. The outputs
    are stored as audio files and spectrogram figures in the catalog as
    `timelapse_audio@PartitionedAudio` and `timelapse_plot@matplotlib`.

    Parameters
    ----------
    sensor_deployment_data : pandas.DataFrame
        A DataFrame summarizing the number of recordings per deployment and day.
        Loaded from the catalog entry `sensor_deployment_data@pandas`.

    media : pandas.DataFrame
        A DataFrame containing metadata of media files, following the pamDP.media format.
        Loaded from the catalog entry `media@pamDP`.

    sample_len : int
        The length of each audio sample in seconds. Loaded from the catalog entry
        `sample_len@int`.

    sample_period : str
        The resampling period for the timelapse (e.g., '1T' for 1 minute). Loaded
        from the catalog entry `sample_period@str`.

    plot_params : dict
        A dictionary containing parameters for the spectrogram plot, such as
        `nperseg`, `noverlap`, `db_range`, `fig_width`, and `fig_height`. Loaded
        from the catalog entry `plot_params@dict`.

    Yields
    ------
    tuple
        - dict: A dictionary containing audio data for each deployment, stored in the catalog
          as `timelapse_audio@PartitionedAudio`.
        - dict: A dictionary containing spectrogram figures for each deployment, stored in the
          catalog as `timelapse_plot@matplotlib`.
    """
    # get selected date for calculating timelapse
    sensor_deployment_data["num_recordings_mean"] = sensor_deployment_data.groupby(
        "timestamp"
    )["count"].transform("mean")

    sensor_deployment_data["num_sensors_by_date"] = sensor_deployment_data.groupby(
        "timestamp"
    )["deploymentID"].transform("nunique")

    selected_date = sensor_deployment_data.sort_values(
        by=["num_sensors_by_date", "num_recordings_mean"], ascending=[False, False]
    )["timestamp"].unique()[0]
    # timelapse calculation
    media = media.astype({"timestamp": "datetime64[ns]"})

    df_timelapse = media[
        media["timestamp"].dt.date
        == datetime.datetime.strptime(selected_date, "%Y-%m-%d").date()
    ].copy()

    df_timelapse.loc[:, "day"] = df_timelapse["timestamp"].dt.date
    df_timelapse.set_index("timestamp", inplace=True)

    # Get parameters for plotting
    ngroups = df_timelapse.groupby(["deploymentID", "day"]).ngroups
    nperseg = plot_params["nperseg"]
    noverlap = plot_params["noverlap"]
    db_range = plot_params["db_range"]
    width = plot_params["fig_width"]
    height = plot_params["fig_height"]
    colormap = plot_params["colormap"]
    
    # Mix timelapse
    logger.info(f"Processing audio timelapse for {ngroups} devices:")

    for site, df_site in df_timelapse.groupby("deploymentID"):
        logger.info(f"Processing deployment: {site}...")

        # Adjust samples for timelapse
        df_site.sort_values("timestamp", inplace=True)
        df_site = df_site.resample(sample_period).first()

        # Compute timelapse
        long_wav, fs = concat_audio(
            df_site["filePath"],
            sample_len=sample_len,
        )

        # Plot spectrogram
        fig, ax = plt.subplots(figsize=(width, height))
        Sxx, tn, fn, ext = sound.spectrogram(
            long_wav,
            fs,
            nperseg=nperseg,
            noverlap=noverlap,  # nperseg*noverlap
        )
        util.plot_spectrogram(Sxx, ext, db_range, ax=ax, colorbar=False, cmap=colormap)

        # Return audio and figure
        file_name = f"{site}_timelapse_{selected_date}"
        yield {file_name: (long_wav, fs)}, {file_name: fig}
        
        # Close the plot to free up memory
        plt.close(fig)



