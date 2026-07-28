"""
Hurricane Map Generator.

Creates detailed hurricane alert maps from
National Weather Service alert data.
"""

import os
import logging
from datetime import datetime

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt

import cartopy.crs as ccrs
import cartopy.feature as cfeature

from shapely.geometry import shape

from config import MAP_OUTPUT_DIR


logger = logging.getLogger(__name__)


def create_output_directory():
    """
    Creates map output directory if needed.
    """

    if not os.path.exists(MAP_OUTPUT_DIR):
        os.makedirs(MAP_OUTPUT_DIR)



def add_base_map(ax):
    """
    Adds map background layers.
    """

    ax.set_extent(
        [
            -100,
            -60,
            15,
            55
        ],
        crs=ccrs.PlateCarree()
    )


    ax.add_feature(
        cfeature.OCEAN
    )

    ax.add_feature(
        cfeature.LAND
    )

    ax.add_feature(
        cfeature.COASTLINE,
        linewidth=0.8
    )

    ax.add_feature(
        cfeature.BORDERS,
        linewidth=0.8
    )


    states = cfeature.NaturalEarthFeature(
        category="cultural",
        name="admin_1_states_provinces_lines",
        scale="50m",
        facecolor="none"
    )


    ax.add_feature(
        states,
        linewidth=0.5
    )



def add_grid(ax):
    """
    Adds latitude and longitude grid.
    """

    grid = ax.gridlines(
        draw_labels=True,
        linewidth=0.5,
        linestyle="--"
    )


    grid.top_labels = False
    grid.right_labels = False



def plot_alert_geometry(ax, alerts):
    """
    Draws hurricane alert polygons.

    Args:
        ax:
            Cartopy axis

        alerts:
            List of NWS alerts
    """

    plotted = 0


    for alert in alerts:

        properties = alert.get(
            "properties",
            {}
        )


        geometry = alert.get(
            "geometry"
        )


        if geometry is None:
            continue


        try:

            polygon = shape(
                geometry
            )


            x, y = polygon.exterior.xy


            ax.fill(
                x,
                y,
                alpha=0.35,
                transform=ccrs.PlateCarree()
            )


            ax.plot(
                x,
                y,
                linewidth=1.5,
                transform=ccrs.PlateCarree()
            )


            plotted += 1


        except Exception as error:

            logger.warning(
                "Unable to plot alert geometry: %s",
                error
            )


    return plotted



def generate_national_alert_map(alerts):
    """
    Generates hurricane alert map.

    Args:
        alerts:
            NWS hurricane alerts

    Returns:
        str:
            Generated PNG path
    """

    create_output_directory()


    timestamp = datetime.utcnow().strftime(
        "%Y%m%d_%H%M%S"
    )


    filename = (
        f"hurricane_alert_map_{timestamp}.png"
    )


    filepath = os.path.join(
        MAP_OUTPUT_DIR,
        filename
    )


    figure = plt.figure(
        figsize=(12, 9),
        dpi=300
    )


    axis = plt.axes(
        projection=ccrs.PlateCarree()
    )


    add_base_map(
        axis
    )


    add_grid(
        axis
    )


    polygons = plot_alert_geometry(
        axis,
        alerts
    )


    title = (
        "National Hurricane Alert Map\n"
        f"Active Alerts: {len(alerts)}"
    )


    plt.title(
        title,
        fontsize=16
    )


    plt.figtext(
        0.5,
        0.02,
        (
            f"Generated "
            f"{datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}"
        ),
        ha="center",
        fontsize=10
    )


    plt.savefig(
        filepath,
        bbox_inches="tight"
    )


    plt.close(
        figure
    )


    logger.info(
        "Hurricane map created: %s | Alert polygons plotted: %s",
        filepath,
        polygons
    )


    return filepath



if __name__ == "__main__":

    print(
        "Hurricane map generator loaded."
    )
