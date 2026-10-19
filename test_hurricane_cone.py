"""Standalone, fictional 5-day cone rendering smoke test.

Does not send email, modify alert history, or call NHC. The existing
`test_email.py` and its workflow are deliberately independent.
"""
import os
from datetime import datetime, timezone
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Patch
import cartopy.crs as ccrs
import cartopy.feature as cfeature
from shapely.geometry import LineString

# Fictional 0/12/24/36/48/72/96/120-hour positions (lon, lat, category).
TRACK = [
    (-66.0, 17.0, 'TS'), (-68.0, 18.0, 'TS'),
    (-70.5, 19.2, '1'), (-73.0, 20.8, '1'),
    (-75.5, 22.5, '2'), (-78.5, 25.0, '3'),
    (-81.0, 28.0, '3'), (-83.0, 31.0, '2'),
]
HOURS = [0, 12, 24, 36, 48, 72, 96, 120]
COLORS = {'TS': '#3b82f6', '1': '#facc15', '2': '#f97316', '3': '#dc2626'}


def render(output):
    # This geometry is deliberately illustrative, NOT an NHC uncertainty product.
    coords = [(lon, lat) for lon, lat, _ in TRACK]
    line = LineString(coords)
    # A widening illustrative corridor, assembled from overlapping buffers.
    from shapely.geometry import Point
    from shapely.ops import unary_union
    corridor = unary_union([
        Point(lon, lat).buffer(0.45 + i * 0.24, resolution=32)
        for i, (lon, lat, _) in enumerate(TRACK)
    ]).union(line.buffer(0.45, resolution=32))
    # Smooth gaps between buffered points by buffering the polyline too.
    corridor = corridor.union(line.buffer(0.8, resolution=32)).buffer(0.22).buffer(-0.22)
    proj = ccrs.PlateCarree()
    fig = plt.figure(figsize=(12, 8), facecolor='white')
    ax = fig.add_axes([0.07, 0.18, 0.86, 0.67], projection=proj)
    ax.set_extent([-91, -61, 13, 37], crs=proj)
    ax.add_feature(cfeature.OCEAN.with_scale('110m'), facecolor='#dbeafe', zorder=0)
    ax.add_feature(cfeature.LAND.with_scale('110m'), facecolor='#f2efe6', zorder=0)
    ax.add_feature(cfeature.COASTLINE.with_scale('110m'), linewidth=0.8, zorder=2)
    ax.add_feature(cfeature.BORDERS.with_scale('110m'), linewidth=0.6, zorder=2)
    ax.add_feature(cfeature.STATES.with_scale('110m'), linewidth=0.6, zorder=2)
    polygons = [corridor] if corridor.geom_type == 'Polygon' else list(corridor.geoms)
    for poly in polygons:
        x, y = poly.exterior.xy
        ax.fill(x, y, facecolor='#a5b4fc', edgecolor='#4338ca', linewidth=1.8,
                alpha=0.35, transform=proj, zorder=4)
    for (lon1, lat1, _), (lon2, lat2, intensity) in zip(TRACK, TRACK[1:]):
        ax.plot([lon1, lon2], [lat1, lat2], color=COLORS[intensity], linewidth=5,
                solid_capstyle='round', transform=proj, zorder=7)
    for (lon, lat, intensity), hour in zip(TRACK, HOURS):
        ax.scatter([lon], [lat], s=70, facecolor=COLORS[intensity],
                   edgecolor='#111827', linewidth=1, transform=proj, zorder=9)
        ax.annotate(f'{hour}h · {"Tropical Storm" if intensity == "TS" else "Cat " + intensity}',
                    (lon, lat), xytext=(6, 7), textcoords='offset points', fontsize=8,
                    weight='bold', color='#111827', zorder=10)
    fig.suptitle('TEST ONLY — SIMULATED 5-DAY HURRICANE FORECAST',
                 fontsize=17, weight='bold', color='#991b1b', y=0.97)
    fig.text(0.5, 0.915, 'FICTIONAL STORM — NOT AN OFFICIAL NHC FORECAST OR WARNING',
             ha='center', fontsize=11, weight='bold', color='#991b1b')
    handles = [Patch(facecolor='#a5b4fc', edgecolor='#4338ca', alpha=0.4,
                     label='Illustrative uncertainty corridor (NOT official cone)')]
    handles.extend(Line2D([0], [0], color=color, lw=4, label=label)
                   for label, color in [('Tropical Storm', COLORS['TS']),
                                        ('Category 1', COLORS['1']),
                                        ('Category 2', COLORS['2']),
                                        ('Category 3', COLORS['3'])])
    fig.legend(handles=handles, loc='lower center', ncol=3, fontsize=9,
               frameon=False, bbox_to_anchor=(0.5, 0.055))
    fig.text(0.5, 0.015, 'Synthetic demonstration only. Live maps must use official NHC cone products.',
             ha='center', fontsize=9, color='#991b1b')
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output, dpi=150, facecolor='white')
    plt.close(fig)
    if not output.is_file() or output.stat().st_size < 10000:
        raise RuntimeError('Cone image was not generated successfully')
    print(f'SUCCESS: simulated cone generated: {output} ({output.stat().st_size:,} bytes)')


if __name__ == '__main__':
    render(os.getenv('TEST_CONE_OUTPUT', 'artifacts/test_hurricane_cone.png'))
