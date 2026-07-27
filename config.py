```python
"""
Configuration module for Nationwide Severe Weather Alert System.

Loads environment variables from .env and provides
application-wide settings.
"""

import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


# ==================================
# National Weather Service API
# ==================================

NWS_API_URL = os.getenv(
    "NWS_API_URL",
    "https://api.weather.gov"
)


# ==================================
# Geographic Monitoring
# ==================================

# Nationwide monitoring mode
MONITOR_SCOPE = os.getenv(
    "MONITOR_SCOPE",
    "UNITED_STATES"
)


# ==================================
# Alert Filtering
# ==================================

MIN_ALERT_SEVERITY = os.getenv(
    "MIN_ALERT_SEVERITY",
    "Severe"
)

ACTIVE_ALERTS_ONLY = os.getenv(
    "ACTIVE_ALERTS_ONLY",
    "true"
).lower() == "true"

MONITOR_ALL_HAZARDS = os.getenv(
    "MONITOR_ALL_HAZARDS",
    "true"
).lower() == "true"


# ==================================
# Email Configuration
# ==================================

SMTP_SERVER = os.getenv(
    "SMTP_SERVER",
    "smtp.gmail.com"
)

SMTP_PORT = int(
    os.getenv(
        "SMTP_PORT",
        "587"
    )
)

EMAIL_FROM = os.getenv(
    "EMAIL_FROM"
)

EMAIL_TO = os.getenv(
    "EMAIL_TO"
)

EMAIL_PASSWORD = os.getenv(
    "EMAIL_PASSWORD"
)


# ==================================
# Weather Map Configuration
# ==================================

GENERATE_MAPS = os.getenv(
    "GENERATE_MAPS",
    "true"
).lower() == "true"

INCLUDE_ALERT_MAPS = os.getenv(
    "INCLUDE_ALERT_MAPS",
    "true"
).lower() == "true"

MAP_DPI = int(
    os.getenv(
        "MAP_DPI",
        "150"
    )
)


# ==================================
# Monitoring Schedule
# ==================================

CHECK_INTERVAL = int(
    os.getenv(
        "CHECK_INTERVAL",
        "15"
    )
)


# ==================================
# Logging
# ==================================

LOG_LEVEL = os.getenv(
    "LOG_LEVEL",
    "INFO"
)


# ==================================
# Alert Severity Priority
# ==================================

SEVERITY_PRIORITY = {
    "Extreme": 4,
    "Severe": 3,
    "Moderate": 2,
    "Minor": 1
}


def is_severe_alert(severity: str) -> bool:
    """
    Determines whether an alert meets
    the configured severity threshold.
    """

    minimum = SEVERITY_PRIORITY.get(
        MIN_ALERT_SEVERITY,
        3
    )

    alert_level = SEVERITY_PRIORITY.get(
        severity,
        0
    )

    return alert_level >= minimum
```
