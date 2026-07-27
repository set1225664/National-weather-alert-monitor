```python
"""
National Weather Service API integration.

Retrieves active severe weather alerts
for the entire United States.
"""

import logging
import requests

from config import (
    NWS_API_URL,
    ACTIVE_ALERTS_ONLY,
    is_severe_alert
)


# Configure logging
logger = logging.getLogger(__name__)


# NWS requires a descriptive User-Agent header
HEADERS = {
    "User-Agent": (
        "Nationwide Severe Weather Alert System "
        "(contact: your_email@example.com)"
    ),
    "Accept": "application/geo+json"
}


def get_active_alerts():
    """
    Retrieve all active weather alerts from
    the National Weather Service.

    Returns:
        list: Active alert features
    """

    url = f"{NWS_API_URL}/alerts/active"

    try:
        response = requests.get(
            url,
            headers=HEADERS,
            timeout=30
        )

        response.raise_for_status()

        data = response.json()

        return data.get(
            "features",
            []
        )

    except requests.RequestException as error:
        logger.error(
            "Unable to retrieve NWS alerts: %s",
            error
        )

        return []


def filter_severe_alerts(alerts):
    """
    Filters alerts based on configured severity.

    Returns:
        list: Alerts meeting severity requirements
    """

    severe_alerts = []

    for alert in alerts:

        properties = alert.get(
            "properties",
            {}
        )

        severity = properties.get(
            "severity",
            ""
        )

        if is_severe_alert(severity):
            severe_alerts.append(alert)

    return severe_alerts


def get_national_severe_alerts():
    """
    Main function used by the monitoring system.

    Retrieves and filters nationwide alerts.
    """

    alerts = get_active_alerts()

    if ACTIVE_ALERTS_ONLY:
        alerts = [
            alert for alert in alerts
            if alert.get("properties", {})
            .get("status") == "Actual"
        ]

    return filter_severe_alerts(alerts)


def summarize_alert(alert):
    """
    Converts an NWS alert into a simple summary
    for emails and logging.
    """

    properties = alert.get(
        "properties",
        {}
    )

    return {
        "event": properties.get(
            "event",
            "Unknown Event"
        ),

        "headline": properties.get(
            "headline",
            ""
        ),

        "severity": properties.get(
            "severity",
            "Unknown"
        ),

        "certainty": properties.get(
            "certainty",
            "Unknown"
        ),

        "urgency": properties.get(
            "urgency",
            "Unknown"
        ),

        "area": properties.get(
            "areaDesc",
            "Unknown Area"
        ),

        "expires": properties.get(
            "expires",
            "Unknown"
        ),

        "description": properties.get(
            "description",
            ""
        )
    }


if __name__ == "__main__":
    """
    Test API connection when run directly.
    """

    alerts = get_national_severe_alerts()

    print(
        f"Active severe alerts found: {len(alerts)}"
    )

    for alert in alerts[:5]:
        print(
            summarize_alert(alert)
        )
```
