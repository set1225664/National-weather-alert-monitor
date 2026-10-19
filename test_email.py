"""Send a clearly simulated hurricane email with a highlighted test map.

Run: python test_email.py
Does not query live NWS alerts or modify alert history.
"""
import logging
import os
from datetime import datetime, timedelta, timezone

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon as MplPolygon, Patch
import cartopy.crs as ccrs
import cartopy.feature as cfeature

from config import MAP_OUTPUT_DIR
from emailer import send_weather_alert

logger = logging.getLogger(__name__)

# Geographic coordinates (longitude, latitude). These are fictional test zones,
# not official warning boundaries or a forecast of any real storm.
TEST_ZONES = {
    'Florida (simulated warning area)': [
        (-85.7, 29.3), (-82.1, 29.3), (-82.1, 30.8), (-85.7, 30.8)
    ],
    'Georgia (simulated warning area)': [
        (-82.4, 30.8), (-80.8, 30.8), (-80.8, 32.3), (-82.4, 32.3)
    ],
}


def generate_test_map():
    """Create an independently rendered, visually highlighted test map."""
    os.makedirs(MAP_OUTPUT_DIR, exist_ok=True)
    filename = os.path.join(MAP_OUTPUT_DIR, 'TEST_ONLY_hurricane_example.png')
    projection = ccrs.PlateCarree()
    fig = plt.figure(figsize=(11, 8), dpi=160, facecolor='white')
    ax = fig.add_axes([0.08, 0.18, 0.84, 0.66], projection=projection)
    ax.set_extent([-89, -78, 24, 36], crs=projection)
    ax.add_feature(cfeature.OCEAN.with_scale('110m'), facecolor='#dbeafe', zorder=0)
    ax.add_feature(cfeature.LAND.with_scale('110m'), facecolor='#f3f0e4', zorder=0)
    ax.add_feature(cfeature.COASTLINE.with_scale('110m'), linewidth=0.8, zorder=2)
    ax.add_feature(cfeature.STATES.with_scale('110m'), edgecolor='#555555', linewidth=0.8, zorder=2)

    plotted = 0
    for name, coords in TEST_ZONES.items():
        if len(coords) < 3:
            raise ValueError(f'Invalid simulated polygon: {name}')
        # Explicitly plot lon/lat coordinates in the map's PlateCarree projection.
        patch = MplPolygon(coords, closed=True, transform=projection,
                           facecolor='#ef4444', edgecolor='#991b1b',
                           linewidth=2.5, alpha=0.65, zorder=20)
        ax.add_patch(patch)
        lon = sum(point[0] for point in coords) / len(coords)
        lat = sum(point[1] for point in coords) / len(coords)
        ax.text(lon, lat, name.split(' ')[0].upper(), transform=projection,
                ha='center', va='center', fontsize=11, fontweight='bold',
                color='#4c0519', zorder=21,
                bbox={'facecolor': 'white', 'alpha': 0.85, 'edgecolor': 'none', 'pad': 2})
        plotted += 1

    if plotted != len(TEST_ZONES):
        raise RuntimeError(f'Expected {len(TEST_ZONES)} test areas, rendered {plotted}')
    fig.suptitle('TEST ONLY — SIMULATED HURRICANE EXAMPLE',
                 fontsize=18, fontweight='bold', y=0.96, color='#991b1b')
    fig.text(0.5, 0.905, 'NOT A REAL STORM OR NATIONAL WEATHER SERVICE WARNING',
             ha='center', fontsize=11, fontweight='bold', color='#991b1b')
    fig.legend(handles=[Patch(facecolor='#ef4444', edgecolor='#991b1b', alpha=0.65,
                              label='Simulated warning area (Florida and Georgia)')],
               loc='lower center', bbox_to_anchor=(0.5, 0.11), frameon=False)
    fig.text(0.5, 0.055, 'Illustrative boundaries only — NOT official NWS alert polygons',
             ha='center', color='#991b1b', fontsize=11, weight='bold')
    fig.savefig(filename, dpi=160, facecolor='white')
    plt.close(fig)
    if not os.path.isfile(filename) or os.path.getsize(filename) < 1000:
        raise RuntimeError('Test map image was not saved correctly')
    logger.info('Created test map with %d highlighted areas: %s', plotted, filename)
    return filename


def main():
    logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
    now = datetime.now(timezone.utc)
    summary = {
        'title': 'TEST ONLY — Hurricane Example (NOT A REAL STORM)',
        'event': 'TEST — Hurricane Warning',
        'storm_name': 'Example',
        'storm_display_name': 'TEST ONLY — Hurricane Example (NOT A REAL STORM)',
        'storm_status': 'Hurricane (simulated)',
        'hurricane_category': 'Category 2 (simulated)',
        'max_winds': '105 mph (simulated)',
        'movement': 'NW at 12 mph (simulated)',
        'pressure': '970 mb (simulated)',
        'affected_states': ['Florida', 'Georgia'],
        'affected_area': 'Florida, Georgia (sample only)',
        'severity': 'Severe (simulated)',
        'urgency': 'Immediate (simulated)',
        'headline': 'TEST ONLY — This is not a real storm or weather warning.',
        'description': 'Simulated impacts: strong winds, heavy rain, coastal flooding.',
        'impacts': ['Strong winds (simulated)', 'Heavy rainfall (simulated)',
                    'Coastal flooding (simulated)'],
        'effective': now.isoformat(),
        'expires': (now + timedelta(hours=24)).isoformat(),
        'ends': (now + timedelta(hours=24)).isoformat(),
    }
    map_path = generate_test_map()
    if not send_weather_alert([summary], map_path):
        raise SystemExit('Test email failed. Check GitHub Actions SMTP logs.')
    print('Test email submitted to SMTP with a simulated highlighted map.')


if __name__ == '__main__':
    main()
