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
                "+00:00"
            )
        )

        formatted = parsed.strftime(
            "%b %d, %Y at %I:%M %p"
        )

        formatted = formatted.replace(
            " at 0",
            " at "
        )

        timezone_name = (
            parsed.tzname()
        )

        if timezone_name:

            formatted += (
                f" {timezone_name}"
            )

        return formatted

    except (
        ValueError,
        TypeError
    ):

        return value


# ---------------------------------------------------------------------
# SUBJECT
# ---------------------------------------------------------------------

def build_email_subject(
    alert_summaries
):
    """
    Create condensed subject.

    Examples:

        WEATHER ALERT: Hurricane Gabrielle — Florida

        WEATHER ALERT: Hurricane Gabrielle — Florida, Georgia

        WEATHER ALERT: 2 Tropical Systems — 5 States
    """

    if not alert_summaries:

        return (
            "WEATHER ALERT: "
            "Severe Tropical Weather"
        )

    storm_names = get_storm_names(
        alert_summaries
    )

    states = get_all_states(
        alert_summaries
    )

    if len(storm_names) == 1:

        primary = storm_names[0]

    elif len(storm_names) > 1:

        primary = (
            f"{len(storm_names)} "
            "Tropical Systems"
        )

    else:

        first_alert = (
            alert_summaries[0]
        )

        primary = safe_text(
            first_alert.get(
                "event"
            ),
            "Severe Tropical Weather"
        )

    if len(states) == 1:

        location = states[0]

    elif len(states) <= 3:

        location = ", ".join(
            states
        )

    elif states:

        location = (
            f"{len(states)} States/Territories"
        )

    else:

        location = ""

    subject = (
        f"WEATHER ALERT: "
        f"{primary}"
    )

    if location:

        subject += (
            f" — {location}"
        )

    return subject
    headline_html = ""

    if headline:

        headline_html = f"""
            <div
                style="
                    margin-top:18px;
                    padding:12px 14px;
                    background:#f5f5f5;
                    border-radius:6px;
                    font-size:14px;
                    line-height:1.5;
                "
            >
                <strong>
                    Latest NWS Update:
                </strong>

                <br>

                {escape(headline)}
            </div>
        """

    return f"""
        <div
            style="
                margin:0 0 24px 0;
                border:1px solid #d8d8d8;
                border-radius:8px;
                overflow:hidden;
            "
        >

            <div
                style="
                    padding:18px 20px;
                    background:#222222;
                    color:#ffffff;
                "
            >

                <div
                    style="
                        font-size:24px;
                        font-weight:bold;
                        line-height:1.3;
                    "
                >
                    {escape(title)}
                </div>

                <div
                    style="
                        margin-top:5px;
                        font-size:15px;
                    "
                >
                    {escape(event)}
                </div>

            </div>

            <div
                style="
                    padding:20px;
                "
            >

                <div
                    style="
                        margin-bottom:12px;
                        font-size:16px;
                        font-weight:bold;
                    "
                >
                    Storm Summary
                </div>

                <ul
                    style="
                        margin:0;
                        padding-left:22px;
                        font-size:14px;
                    "
                >
                    {bullet_html}
                </ul>

                {headline_html}

            </div>

        </div>
    """
</html>
    """


# ---------------------------------------------------------------------
# PLAIN TEXT VERSION
# ---------------------------------------------------------------------

def build_plain_text_email(
    alert_summaries
):
    """
    Build plain-text fallback.
    """

    storm_names = get_storm_names(
        alert_summaries
    )

    all_states = get_all_states(
        alert_summaries
    )

    lines = [
        SYSTEM_NAME,
        "=" * 60,
        ""
    ]

    if storm_names:

        lines.append(
            "STORM:"
        )

        lines.append(
            ", ".join(
                storm_names
            )
        )

        lines.append(
            ""
        )

    if all_states:

        lines.append(
            "AFFECTED STATES:"
        )

        lines.append(
            ", ".join(
                all_states
            )
        )

        lines.append(
            ""
        )

    for alert in alert_summaries:

        storm_name = (
            get_display_storm_name(
                alert
            )
        )

        title = (
            storm_name
            or get_alert_title(
                alert
            )
        )

        lines.extend([
            title,
            "-" * len(title),
            "",
            "STORM SUMMARY"
        ])

        facts = build_storm_facts(
            alert
        )

        for label, value in facts:

            lines.append(
                f"• {label}: {value}"
            )

        headline = safe_text(
            alert.get(
                "headline"
            )
        )

        if headline:

            lines.extend([
                "",
                (
                    "Latest NWS Update: "
                    f"{headline}"
                )
            ])

        lines.extend([
            "",
            "=" * 60,
            ""
        ])

    lines.extend([
        "A generated affected-area map is included "
        "in the HTML version of this email.",
        "",
        (
            "Follow official National Weather Service "
            "and local emergency-management instructions."
        )
    ])

    return "\n".join(
        lines
    )

        logger.info(
            "No alerts supplied to emailer."
        )

        return False

    if not validate_email_configuration():

        return False

    recipients = (
        normalize_recipient_list(
            EMAIL_TO
        )
    )

    subject = (
        build_email_subject(
            alert_summaries
        )
    )

    map_available = bool(
        map_file
        and os.path.exists(
            map_file
        )
    )

    plain_body = (
        build_plain_text_email(
            alert_summaries
        )
    )

    html_body = (
        build_email_html(
            alert_summaries,
            map_available=map_available
        )
    )

    message = EmailMessage()

    message["Subject"] = (
        subject
    )

    message["From"] = (
        formataddr(
            (
                FROM_DISPLAY_NAME,
                EMAIL_FROM
            )
        )
    )

    message["To"] = (
        ", ".join(
            recipients
        )
    )

    # Plain-text fallback.
    message.set_content(
        plain_body
    )

    # Add HTML alternative.
    message.add_alternative(
        html_body,
        subtype="html"
    )

    # EmailMessage now contains:
    #
    # multipart/alternative
    #   text/plain
    #   text/html
    #
    # Retrieve the HTML part so the generated map can be
    # attached as a related CID image.

    if map_available:

        try:

            html_part = (
                message.get_payload()[-1]
            )

            attach_inline_map(
                html_part,
                map_file
            )

        except Exception as error:

            logger.exception(
                "Unable to prepare inline map: %s",
                error
            )

    logger.info(
        "Sending weather alert to %s recipient(s).",
        len(
            recipients
        )
    )

    logger.info(
        "Email subject: %s",
        subject
    )

    try:

        # ---------------------------------------------------------
        # SMTP SSL - PORT 465
        # ---------------------------------------------------------

        if int(
            SMTP_PORT
        ) == 465:

            with smtplib.SMTP_SSL(
                SMTP_SERVER,
                int(
                    SMTP_PORT
                ),
                timeout=30
            ) as smtp:

                smtp.login(
                    EMAIL_USER,
                    EMAIL_PASSWORD
                )

                smtp.send_message(
                    message,
                    from_addr=EMAIL_FROM,
                    to_addrs=recipients
                )

        # ---------------------------------------------------------
        # STARTTLS - PORT 587 / OTHER
        # ---------------------------------------------------------

        else:

            with smtplib.SMTP(
                SMTP_SERVER,
                int(
                    SMTP_PORT
                ),
                timeout=30
            ) as smtp:

                smtp.ehlo()

                smtp.starttls()

                smtp.ehlo()

                smtp.login(
                    EMAIL_USER,
                    EMAIL_PASSWORD
                )

                smtp.send_message(
                    message,
                    from_addr=EMAIL_FROM,
                    to_addrs=recipients
                )

        logger.info(
            "Weather alert email sent successfully."
        )

        return True

    except smtplib.SMTPAuthenticationError:

        logger.exception(
            "SMTP authentication failed. "
            "Check EMAIL_USER and EMAIL_PASSWORD."
        )

        return False

    except smtplib.SMTPException as error:

        logger.exception(
            "SMTP error while sending weather alert: %s",
            error
        )

        return False

    except Exception as error:

        logger.exception(
            "Unexpected email delivery error: %s",
            error
        )

        return False



