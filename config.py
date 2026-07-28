"""
Configuration Module.

Loads environment variables and provides
configuration settings for the Nationwide
Hurricane Alert Monitoring System.
"""

import os

from dotenv import load_dotenv


# Load .env file when running locally
# GitHub Actions will provide variables
# through repository secrets.
load_dotenv()



# -------------------------------------------------
# Weather Monitoring Configuration
# -------------------------------------------------

NWS_API_URL = os.getenv(
    "NWS_API_URL",
    "https://api.weather.gov"
)


MONITOR_SCOPE = os.getenv(
    "MONITOR_SCOPE",
    "UNITED_STATES"
)


# Only hurricane-related events
HURRICANE_EVENTS = [
    "Hurricane Warning",
    "Hurricane Watch",
    "Tropical Storm Warning",
    "Tropical Storm Watch",
    "Storm Surge Warning",
    "Storm Surge Watch"
]



# -------------------------------------------------
# Monitoring Schedule
# -------------------------------------------------

CHECK_INTERVAL = int(
    os.getenv(
        "CHECK_INTERVAL",
        "15"
    )
)



# -------------------------------------------------
# Alert Filtering
# -------------------------------------------------

MIN_ALERT_SEVERITY = os.getenv(
    "MIN_ALERT_SEVERITY",
    "Severe"
)


TEST_MODE = os.getenv(
    "TEST_MODE",
    "false"
).lower() == "true"



# -------------------------------------------------
# Map Generation
# -------------------------------------------------

GENERATE_MAPS = os.getenv(
    "GENERATE_MAPS",
    "true"
).lower() == "true"


MAP_OUTPUT_DIR = os.getenv(
    "MAP_OUTPUT_DIR",
    "maps"
)


MAP_DPI = int(
    os.getenv(
        "MAP_DPI",
        "300"
    )
)



# -------------------------------------------------
# Email Configuration
# -------------------------------------------------

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



# -------------------------------------------------
# Logging
# -------------------------------------------------

LOG_LEVEL = os.getenv(
    "LOG_LEVEL",
    "INFO"
)



# -------------------------------------------------
# Alert History
# -------------------------------------------------

ALERT_HISTORY_FILE = os.getenv(
    "ALERT_HISTORY_FILE",
    "alert_history.json"
)



# -------------------------------------------------
# Application Information
# -------------------------------------------------

APP_NAME = (
    "Nationwide Hurricane Alert Monitor"
)


APP_VERSION = (
    "1.0.0"
)
