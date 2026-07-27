```python
"""
Weather Alert Map Generator.

Creates U.S. national maps showing active
National Weather Service severe weather alerts.
"""

import os
import logging
from datetime import datetime

import matplotlib.pyplot as plt
import cartopy.crs as ccrs
import cartopy.feature as cfeature

from config import MAP_DPI


logger = logging.getLogger(__name__)


# Output directory for generated maps
MAP_OUTPUT_DIR = "maps"


def create_output_directory():
    """
    Ensures map output directory exists.
    """

    if not os.path.exists(MAP_OUTPUT_DIR):
        os.makedirs(MAP_OUTPUT_DIR)


def get_alert_color(severity):
    """
    Returns map styling based on alert severity.

    Note:
    Colors are intentionally simple because
    the alert type is communicated primarily
    through labels and polygons.
    """

    severity_map = {
        "Extreme": "red",
        "Severe": "orange",
        "Moderate": "yellow",
        "Minor": "green"
    }

    return severity_map.get(
        severity,
        "gray"
    )


def generate_national_alert_map(alerts):
    """
    Generates a nationwide U.S. weather alert map.

    Args:
        alerts (list):
            NWS alert feature objects

    Returns:
        str:
            Path to generated image
    """

    create_output_directory()

    timestamp = datetime.utcnow().strftime(
        "%Y%m%d_%H%M%S"
    )

    filename = (
        f"{MAP_OUTPUT_DIR}/"
        f"severe_weather_map_{timestamp}.png"
    )


    fig = plt.figure(
        figsize=(12, 8),
        dpi=MAP_DPI
    )

    ax = plt.axes(
        projection=ccrs.LambertConformal()
    )


    # United States viewing area
    ax.set_extent(
        [
            -130,
            -60,
            20,
            55
        ],
        crs=ccrs.PlateCarree()
    )


    # Base map layers
    ax.add_feature(
        cfeature.STATES
    )

    ax.add_feature(
        cfeature.BORDERS
    )

    ax.add_feature(
        cfeature.COASTLINE
    )


    alert_count = 0


    for alert in alerts:

        properties = alert.get(
            "properties",
            {}
        )

        geometry = alert.get(
            "geometry"
        )


        if not geometry:
            continue


        severity = properties.get(
            "severity",
            "Unknown"
        )

        color = get_alert_color(
            severity
        )


        try:
            coordinates = geometry.get(
                "coordinates",
                []
            )

            if geometry.get(
                "type"
            ) == "Polygon":

                for polygon in coordinates:

                    longitude = [
                        point[0]
                        for point in polygon
                    ]

                    latitude = [
                        point[1]
                        for point in polygon
                    ]

                    ax.fill(
                        longitude,
                        latitude,
                        transform=ccrs.PlateCarree(),
                        alpha=0.35,
                        label=severity
                    )

                    alert_count += 1


            elif geometry.get(
                "type"
            ) == "MultiPolygon":

                for multipolygon in coordinates:

                    for polygon in multipolygon:

                        longitude = [
                            point[0]
                            for point in polygon
                        ]

                        latitude = [
                            point[1]
                            for point in polygon
                        ]

                        ax.fill(
                            longitude,
                            latitude,
                            transform=ccrs.PlateCarree(),
                            alpha=0.35,
                            label=severity
                        )

                        alert_count += 1


        except Exception as error:

            logger.warning(
                "Unable to plot alert polygon: %s",
                error
            )


    plt.title(
        "National Severe Weather Alerts\n"
        f"Active Alerts: {alert_count}"
    )


    plt.savefig(
        filename,
        bbox_inches="tight"
    )

    plt.close()


    logger.info(
        "Weather map created: %s",
        filename
    )


    return filename



if __name__ == "__main__":

    print(
        "Map generator module loaded."
    )
```
