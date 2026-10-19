"""
Email Notification System.

Creates and sends condensed tropical weather alert emails.

Features:

1. Named storm shown prominently
2. Quick bullet-point storm summary
3. Affected states instead of county lists
4. Maximum winds when available
5. Storm movement when available
6. Pressure when available
7. Effective / expiration times
8. Short NWS headline
9. Generated affected-area map embedded directly in the email
10. Plain-text fallback
"""

import logging
import mimetypes
import os
import smtplib

from datetime import datetime
from email.message import EmailMessage
from email.utils import formataddr
from html import escape


# ---------------------------------------------------------------------
# CONFIGURATION
# ---------------------------------------------------------------------

try:
    from config import (
        SMTP_SERVER,
        SMTP_PORT,
        EMAIL_USER,
        EMAIL_PASSWORD,
        EMAIL_FROM,
        EMAIL_TO
    )

except ImportError:

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

    EMAIL_USER = os.getenv(
        "EMAIL_USER",
        ""
    )

    EMAIL_PASSWORD = os.getenv(
        "EMAIL_PASSWORD",
        ""
    )

    EMAIL_FROM = os.getenv(
        "EMAIL_FROM",
        EMAIL_USER
    )

    EMAIL_TO = os.getenv(
        "EMAIL_TO",
        ""
    )


logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------
# DISPLAY SETTINGS
# ---------------------------------------------------------------------

SYSTEM_NAME = (
    "Nationwide Severe Weather Alert System"
)

FROM_DISPLAY_NAME = (
    "National Weather Alert Monitor"
)

MAP_CONTENT_ID = "affected-area-map"
