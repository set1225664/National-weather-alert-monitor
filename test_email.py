"""Send a simulated hurricane email with an automatically generated map.

Run: python test_email.py
No live NWS requests or alert-history changes are made by this script.
"""
import logging
import os
from datetime import datetime, timedelta, timezone

import matplotlib
matplotlib.use("Agg")
import matplotlib.image as mpimg
import matplotlib.pyplot as plt

from emailer import send_weather_alert
from map_generator import generate_national_alert_map


def build_sample_alert(now):
    """Synthetic GeoJSON polygon for testing map rendering only."""
    return {
        "type": "Feature",
        "id": "TEST-ONLY-HURRICANE-EXAMPLE",
        "geometry": {
            "type": "MultiPolygon",
            "coordinates": [
                [[[-85.7, 29.3], [-82.1, 29.3], [-82.1, 31.3], [-85.7, 31.3], [-85.7, 29.3]]],
                [[[-82.4, 30.8], [-80.8, 30.8], [-80.8, 32.3], [-82.4, 32.3], [-82.4, 30.8]]]
            ],
        },
        "properties": {
            "event": "Hurricane Warning",
            "severity": "Severe",
            "areaDesc": "Florida; Georgia",
            "headline": "TEST ONLY — Simulated hurricane; not a real NWS alert",
            "effective": now.isoformat(),
            "expires": (now + timedelta(hours=24)).isoformat(),
            "affectedZones": [],
        },
    }


def label_test_map(source):
    """Prominently label the map as simulated to avoid confusion."""
    img = mpimg.imread(source)
    height, width = img.shape[:2]
    fig = plt.figure(figsize=(width / 140, height / 140), dpi=140)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.imshow(img)
    ax.axis("off")
    fig.text(0.5, 0.965, "TEST ONLY — SIMULATED STORM / NOT A REAL WEATHER WARNING",
             ha="center", va="top", fontsize=14, weight="bold", color="white",
             bbox={"facecolor": "#9b111e", "edgecolor": "none", "pad": 9})
    fig.text(0.5, 0.075, "Colored shapes are synthetic test polygons, NOT official NWS warning areas",
             ha="center", fontsize=11, weight="bold", color="#9b111e",
             bbox={"facecolor": "white", "edgecolor": "#9b111e", "pad": 5})
    output = os.path.join(os.path.dirname(source), "TEST_ONLY_" + os.path.basename(source))
    fig.savefig(output, dpi=140, facecolor="white")
    plt.close(fig)
    return output


def main():
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    now = datetime.now(timezone.utc)
    summary = {
        "title": "TEST ONLY — Hurricane Example (NOT A REAL STORM)",
        "event": "TEST — Hurricane Warning",
        "storm_name": "Example",
        "storm_display_name": "TEST ONLY — Hurricane Example (NOT A REAL STORM)",
        "storm_status": "Hurricane (simulated)",
        "hurricane_category": "Category 2 (simulated)",
        "max_winds": "105 mph (simulated)",
        "movement": "NW at 12 mph (simulated)",
        "pressure": "970 mb (simulated)",
        "affected_states": ["Florida", "Georgia"],
        "affected_area": "Florida, Georgia (sample only)",
        "severity": "Severe (simulated)",
        "urgency": "Immediate (simulated)",
        "headline": "TEST MESSAGE — No actual storm or weather warning is being reported.",
        "description": "Simulated impacts: strong winds, heavy rain, and coastal flooding. TEST ONLY.",
        "impacts": ["Strong winds (simulated)", "Heavy rainfall (simulated)", "Coastal flooding (simulated)"],
        "effective": now.isoformat(),
        "expires": (now + timedelta(hours=24)).isoformat(),
        "ends": (now + timedelta(hours=24)).isoformat(),
    }

    print("Generating sample hurricane map...")
    map_path = generate_national_alert_map([build_sample_alert(now)])
    if not map_path or not os.path.isfile(map_path) or os.path.getsize(map_path) == 0:
        raise SystemExit("Map generation failed; test email was NOT sent.")
    test_map = label_test_map(map_path)
    print(f"Generated test map: {test_map}")

    if not send_weather_alert([summary], test_map):
        raise SystemExit("Test email failed. Check SMTP credentials and workflow logs.")
    print("Test email accepted by SMTP with simulated map attached inline. Check Outlook inbox and junk.")


if __name__ == "__main__":
    main()
