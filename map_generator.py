"""Official NHC five-day forecast cone and intensity track map.

Reads active cone/track KMZ products linked by https://www.nhc.noaa.gov/gis/.
Never manufactures a cone from warning polygons or forecast points.
Compatible with generate_national_alert_map(alerts) used by main.py.
"""
import io
import logging
import os
import re
import zipfile
from datetime import datetime, timezone
from html import unescape
from urllib.parse import urljoin, urlparse
from xml.etree import ElementTree as ET

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Patch
import cartopy.crs as ccrs
import cartopy.feature as cfeature
import requests
from shapely.geometry import Polygon, MultiPolygon

from config import MAP_OUTPUT_DIR

logger = logging.getLogger(__name__)
GIS_URL = 'https://www.nhc.noaa.gov/gis/'
TIMEOUT = 25
MAX_DOWNLOAD = 18 * 1024 * 1024
COLORS = {
    'TD': '#93c5fd', 'TS': '#3b82f6', '1': '#facc15',
    '2': '#fb923c', '3': '#ef4444', '4': '#b91c1c', '5': '#7f1d1d',
    'POST': '#64748b', 'UNKNOWN': '#64748b'
}
HEADERS = {'User-Agent': os.getenv('NHC_USER_AGENT', 'NationalWeatherAlertMonitor/1.0 (weather-monitor)'), 'Accept': 'text/html, application/vnd.google-earth.kmz, */*'}
PROJ = ccrs.PlateCarree()


def _get(url):
    parsed = urlparse(url)
    if parsed.scheme != 'https' or parsed.hostname not in ('www.nhc.noaa.gov', 'nhc.noaa.gov'):
        raise ValueError('Refusing non-NHC forecast URL')
    response = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
    response.raise_for_status()
    if len(response.content) > MAX_DOWNLOAD:
        raise ValueError('NHC product exceeds size limit')
    return response.content


def _active_products():
    """Discover currently linked cone and track products, keyed by NHC storm ID."""
    page = _get(GIS_URL).decode('utf-8', errors='replace')
    # NHC site publishes KMZ links in the active GIS forecast row.
    anchors = re.findall(r'<a\b[^>]*href\s*=\s*["\']([^"\']+)["\'][^>]*>(.*?)</a>', page, re.I | re.S)
    products = {}
    for href, label_html in anchors:
        url = urljoin(GIS_URL, unescape(href))
        filename = urlparse(url).path.rsplit('/', 1)[-1]
        match = re.match(r'([A-Z]{2}\d{6})_(\d+[A]?)adv_(CONE|TRACK)\.kmz$', filename, re.I)
        if not match:
            continue
        storm_id, advisory, kind = match.groups()
        storm_id, kind = storm_id.upper(), kind.upper()
        item = products.setdefault(storm_id, {'name': None, 'cone': None, 'track': None, 'advisory': None})
        # Prefer the latest *matching* advisory; never combine products from different advisories.
        rank = (int(re.match(r'\d+', advisory).group()), 1 if advisory.upper().endswith('A') else 0)
        existing = item.setdefault('_versions', {})
        version = existing.setdefault(advisory, {'rank': rank})
        version[kind.lower()] = url
        label = re.sub(r'<[^>]+>', ' ', label_html).strip()
        if label and label.lower() not in ('cone', 'track', 'kmz'):
            item['name'] = label
        # Most NHC GIS links are simply labeled 'Cone'/'Track'; the storm
        # name appears in the enclosing table cell, not the anchor.
        if not item['name']:
            pos = page.find(href)
            if pos >= 0:
                context = re.sub(r'<[^>]+>', ' ', page[max(0, pos-600):pos])
                context = unescape(context)
                matches = re.findall(r'\b(?:Hurricane|Tropical Storm|Tropical Depression|Subtropical Storm|Typhoon)\s+([A-Za-z][A-Za-z-]+)', context, re.I)
                if matches:
                    item['name'] = matches[-1]
    for storm_id, item in products.items():
        versions = [ (v['rank'], a, v) for a, v in item['_versions'].items() if 'cone' in v and 'track' in v ]
        if versions:
            _, advisory, version = max(versions)
            item.update({'cone': version['cone'], 'track': version['track'], 'advisory': advisory})
        del item['_versions']
    return {k: v for k, v in products.items() if v['cone'] and v['track']}


def _read_kmz(url):
    raw = _get(url)
    with zipfile.ZipFile(io.BytesIO(raw)) as zf:
        names = [n for n in zf.namelist() if n.lower().endswith('.kml')]
        if not names:
            raise ValueError('NHC KMZ has no KML document')
        kml = zf.read(names[0])
    return ET.fromstring(kml)


def _coords(text):
    result = []
    for item in (text or '').strip().split():
        values = item.split(',')
        if len(values) >= 2:
            try:
                result.append((float(values[0]), float(values[1])))
            except ValueError:
                pass
    return result


def _placemarks(root):
    for placemark in root.findall('.//{*}Placemark'):
        name = placemark.findtext('{*}name') or ''
        description = re.sub(r'<[^>]*>', ' ', placemark.findtext('{*}description') or '')
        fields = {}
        for data in placemark.findall('.//{*}Data'):
            key = (data.attrib.get('name') or '').upper()
            fields[key] = data.findtext('{*}value') or ''
        for data in placemark.findall('.//{*}SimpleData'):
            fields[(data.attrib.get('name') or '').upper()] = data.text or ''
        yield placemark, name, description, fields


def _cone_polygons(root):
    polygons = []
    for placemark, _, _, _ in _placemarks(root):
        for poly in placemark.findall('.//{*}Polygon'):
            outer = poly.find('.//{*}outerBoundaryIs/{*}LinearRing/{*}coordinates')
            if outer is None:
                continue
            shell = _coords(outer.text)
            holes = []
            for inner in poly.findall('.//{*}innerBoundaryIs/{*}LinearRing/{*}coordinates'):
                coords = _coords(inner.text)
                if len(coords) >= 4:
                    holes.append(coords)
            if len(shell) >= 4:
                polygon = Polygon(shell, holes)
                if polygon.is_valid and not polygon.is_empty:
                    polygons.append(polygon)
    return polygons


def _intensity(fields, text):
    """Use forecast maximum wind (kt) or explicit storm category; never infer from cone width."""
    for key in ('MAXWIND', 'MAX_WIND', 'VMAX', 'WIND', 'INTENSITY', 'MAX_WIND_KT'):
        match = re.search(r'\d+(?:\.\d+)?', str(fields.get(key, '')))
        if match:
            wind = float(match.group())
            if wind < 34: return 'TD'
            if wind < 64: return 'TS'
            if wind < 83: return '1'
            if wind < 96: return '2'
            if wind < 113: return '3'
            if wind < 137: return '4'
            return '5'
    combined = ' '.join([text] + list(fields.values()))
    match = re.search(r'\b(?:CAT(?:EGORY)?\s*|HURRICANE\s+CAT\s*)([1-5])\b', combined, re.I)
    if match: return match.group(1)
    if re.search(r'\bTROPICAL STORM\b', combined, re.I): return 'TS'
    if re.search(r'\bTROPICAL DEPRESSION\b', combined, re.I): return 'TD'
    return 'UNKNOWN'


def _track_points(root):
    points = []
    for placemark, name, description, fields in _placemarks(root):
        # Official TRACK KMZ point placemarks contain the forecast positions.
        for point in placemark.findall('.//{*}Point'):
            coord = point.findtext('{*}coordinates')
            parsed = _coords(coord)
            if not parsed:
                continue
            hours = None
            for key in ('FCST_HR', 'TAU', 'FHOUR', 'FORECAST_HOUR', 'FCSTHR'):
                value = fields.get(key, '')
                match = re.search(r'\b\d{1,3}\b', str(value))
                if match:
                    hours = int(match.group())
                    break
            if hours is None:
                match = re.search(r'\b(0|12|24|36|48|60|72|96|120)\s*(?:H|HR|HRS|HOURS)\b', name + ' ' + description, re.I)
                if match: hours = int(match.group(1))
            if hours is not None and hours > 120:
                continue
            points.append({'xy': parsed[0], 'hours': hours, 'level': _intensity(fields, name + ' ' + description), 'name': name})
    if points and all(p['hours'] is not None for p in points):
        points.sort(key=lambda p: p['hours'])
    # Deduplicate positions while retaining forecast order.
    unique, seen = [], set()
    for p in points:
        key = (p['xy'], p['hours'])
        if key not in seen:
            unique.append(p)
            seen.add(key)
    return unique


def _storm_names(alerts):
    try:
        from weather_api import extract_storm_name
    except ImportError:
        return set()
    names = set()
    for alert in alerts or []:
        name = extract_storm_name(alert)
        if name:
            names.add(name.lower())
    return names


def _match_storms(products, alerts):
    """Only plot storms positively matched to named NWS alerts."""
    names = _storm_names(alerts)
    if not names:
        return {}
    selected = {}
    for storm_id, product in products.items():
        label = product.get('name') or ''
        if any(re.search(r'(?<![a-z])' + re.escape(n) + r'(?![a-z])', label.lower()) for n in names):
            selected[storm_id] = product
    return selected


def _render_cone(ax, polygons):
    for polygon in polygons:
        ax.add_geometries([polygon], crs=PROJ, facecolor='#a5b4fc', edgecolor='#3730a3', alpha=0.28, linewidth=1.5, zorder=3)


def _render_track(ax, points):
    for left, right in zip(points, points[1:]):
        xs = [left['xy'][0], right['xy'][0]]
        ys = [left['xy'][1], right['xy'][1]]
        ax.plot(xs, ys, color=COLORS[right['level']], linewidth=4, transform=PROJ, zorder=5)
    for p in points:
        x, y = p['xy']
        ax.plot(x, y, 'o', color=COLORS[p['level']], markeredgecolor='white', markersize=8, transform=PROJ, zorder=6)
        if p['hours'] is not None:
            ax.text(x + .25, y + .25, f"+{p['hours']}h", fontsize=8, weight='bold', transform=PROJ, zorder=7)


def generate_national_alert_map(alerts):
    """Return a PNG path for matching official active NHC forecast cones, or None.

    A None result means no official cone could be matched/downloaded. It is safer
    than presenting a synthetic or stale cone as a current forecast.
    """
    try:
        products = _match_storms(_active_products(), alerts)
    except Exception as exc:
        logger.warning('NHC forecast discovery unavailable: %s', exc)
        return None
    if not products:
        logger.warning('No current NHC forecast cone matched the named storms in the NWS alerts.')
        return None
    datasets = []
    for storm_id, item in products.items():
        try:
            cone = _cone_polygons(_read_kmz(item['cone']))
            track = _track_points(_read_kmz(item['track']))
            if not cone or len(track) < 2:
                logger.warning('Incomplete cone or forecast positions for %s', storm_id)
                continue
            datasets.append((storm_id, item, cone, track))
        except Exception as exc:
            logger.warning('Unable to load official forecast for %s: %s', storm_id, exc)
    if not datasets:
        return None
    os.makedirs(MAP_OUTPUT_DIR, exist_ok=True)
    fig = plt.figure(figsize=(13, 9), dpi=170)
    ax = fig.add_subplot(111, projection=PROJ)
    ax.add_feature(cfeature.OCEAN, facecolor='#dbeafe')
    ax.add_feature(cfeature.LAND, facecolor='#f4f1e5')
    ax.add_feature(cfeature.COASTLINE, linewidth=.7)
    ax.add_feature(cfeature.BORDERS, linewidth=.5)
    ax.add_feature(cfeature.STATES, linewidth=.35)
    bounds = []
    for storm_id, item, cone, points in datasets:
        _render_cone(ax, cone)
        _render_track(ax, points)
        for poly in cone:
            bounds.extend([(poly.bounds[0], poly.bounds[1]), (poly.bounds[2], poly.bounds[3])])
        bounds.extend([p['xy'] for p in points])
        label = item.get('name') or storm_id
        first = points[0]['xy']
        ax.text(first[0], first[1] - .8, label, weight='bold', fontsize=10, transform=PROJ)
    xs, ys = zip(*bounds)
    pad_x = max(3, (max(xs) - min(xs)) * .18)
    pad_y = max(3, (max(ys) - min(ys)) * .18)
    ax.set_extent([max(-179, min(xs)-pad_x), min(179, max(xs)+pad_x), max(-70, min(ys)-pad_y), min(75, max(ys)+pad_y)], crs=PROJ)
    legend = [Patch(facecolor='#a5b4fc', edgecolor='#3730a3', alpha=.5, label='Official NHC center-position uncertainty cone')]
    legend.extend(Line2D([0], [0], color=color, linewidth=4, label=label) for label, color in [
        ('Tropical depression', COLORS['TD']), ('Tropical storm', COLORS['TS']),
        ('Category 1', COLORS['1']), ('Category 2', COLORS['2']),
        ('Category 3', COLORS['3']), ('Category 4', COLORS['4']),
        ('Category 5', COLORS['5']), ('Intensity unavailable', COLORS['UNKNOWN'])])
    ax.legend(handles=legend, loc='lower left', fontsize=8, framealpha=.95)
    fig.suptitle('Official NHC 5-Day Forecast Cone and Intensity Track', fontsize=16, weight='bold')
    fig.text(.5, .04, 'Cone = uncertainty in storm CENTER location, NOT the full impact area. Track colors = forecast intensity when available.', ha='center', fontsize=9)
    fig.text(.5, .015, 'Source: NOAA/NHC GIS active forecast products | Generated ' + datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC'), ha='center', fontsize=8)
    filename = 'nhc_5day_forecast_' + datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S') + '.png'
    path = os.path.join(MAP_OUTPUT_DIR, filename)
    fig.savefig(path, bbox_inches='tight', facecolor='white')
    plt.close(fig)
    logger.info('Created official NHC 5-day cone map: %s (%d storms)', path, len(datasets))
    return path


if __name__ == '__main__':
    print('NHC 5-day forecast generator ready. Call generate_national_alert_map(alerts).')
