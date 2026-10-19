"""
Main Application Controller.

Runs the Nationwide Severe Weather Alert System.

Workflow:

1. Check National Weather Service alerts
2. Filter severe and extreme alerts
3. Detect newly issued alerts
4. Consolidate related alerts and affected areas
5. Generate alert map
6. Send one condensed notification email
7. Update alert history
"""

import time
import logging
from collections import defaultdict

from weather_api import extract_storm_name, extract_affected_states

from config import (
    CHECK_INTERVAL,
    LOG_LEVEL,
    GENERATE_MAPS
)

from utils import setup_logging

from weather_api import (
    get_national_hurricane_alerts,
    summarize_alert
)

from alert_manager import (
    get_new_alerts,
    update_alert_history,
    clear_old_alerts
)

from map_generator import (
    generate_national_alert_map
)

from emailer import (
    send_weather_alert
)


logger = logging.getLogger(__name__)


def group_alerts_by_storm(alerts):
    """Only associate alerts with a storm explicitly named in NWS text.

    Unnamed alerts are not assigned to a storm based on geography alone.
    """
    groups = defaultdict(list)
    for alert in alerts:
        name = extract_storm_name(alert)
        if name:
            groups[name.casefold()].append(alert)
        else:
            logger.info("Skipping alert without confirmed storm name: %s",
                        alert.get("properties", {}).get("event", "Unknown"))
    return groups


def summarize_storm(name, alerts):
    """Create one email summary for a named storm, including all its impacts."""
    summaries = [summarize_alert(alert) for alert in alerts]
    states = sorted({state for item in summaries for state in item.get("affected_states", [])})
    events = sorted({item.get("event", "") for item in summaries if item.get("event")})
    # Prefer actual tropical-cyclone statements for meteorological details.
    def priority(item):
        event = item.get("event", "").lower()
        return ("tropical cyclone" in event or "hurricane" in event or "tropical storm" in event,
                bool(item.get("max_winds")), bool(item.get("movement")))
    primary = max(summaries, key=priority).copy()
    primary["storm_name"] = name
    primary["storm_display_name"] = primary.get("storm_display_name") or name
    primary["title"] = primary["storm_display_name"]
    primary["affected_states"] = states
    primary["affected_area"] = ", ".join(states) if states else "Not specified"
    primary["events"] = events
    primary["impacts"] = [label for keyword, label in (
        ("hurricane", "Hurricane-force winds possible in warned areas"),
        ("tropical storm", "Tropical-storm-force winds possible in warned areas"),
        ("storm surge", "Coastal storm surge and inundation risk"),
        ("flash flood", "Flash flooding risk"),
        ("flood", "Flooding risk"),
        ("tornado", "Tornado risk"),
        ("extreme wind", "Extreme wind risk"),
    ) if any(keyword in event.lower() for event in events)]
    primary["source_alert_count"] = len(alerts)
