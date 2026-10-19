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


# ---------------------------------------------------------------------
# BASIC HELPERS
# ---------------------------------------------------------------------

def safe_text(
    value,
    default=""
):
    """
    Return clean display text.
    """

    if value is None:
        return default

    value = str(
        value
    ).strip()

    if not value:
        return default

    return value


def normalize_recipient_list(
    recipients
):
    """
    Convert EMAIL_TO into a list of email addresses.

    Supports:

        one@example.com

        one@example.com,two@example.com

        [
            "one@example.com",
            "two@example.com"
        ]
    """

    if not recipients:
        return []

    if isinstance(
        recipients,
        (list, tuple, set)
    ):

        return [
            str(address).strip()
            for address in recipients
            if str(address).strip()
        ]

    return [
        address.strip()
        for address in str(recipients).split(",")
        if address.strip()
    ]


# ---------------------------------------------------------------------
# DATE FORMATTING
# ---------------------------------------------------------------------

def format_datetime(
    value
):
    """
    Format NWS ISO timestamps into a readable form.

    Example:

        2026-09-02T14:00:00-04:00

    becomes:

        Sep 02, 2026 at 2:00 PM EDT
    """

    value = safe_text(
        value
    )

    if not value:
        return "Not specified"

    try:

        parsed = datetime.fromisoformat(
            value.replace(
                "Z",
