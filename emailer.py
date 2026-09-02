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

MAP_CONTENT_ID = (
    "affected-area-map"
)


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
# ALERT INFORMATION
# ---------------------------------------------------------------------

def get_alert_title(
    alert
):
    """
    Build the primary title.

    Example:

        Hurricane Warning — Hurricane Gabrielle
    """

    title = safe_text(
        alert.get(
            "title"
        )
    )

    if title:
        return title

    event = safe_text(
        alert.get(
            "event"
        ),
        "Weather Alert"
    )

    storm_display_name = safe_text(
        alert.get(
            "storm_display_name"
        )
    )

    storm_name = safe_text(
        alert.get(
            "storm_name"
        )
    )

    if storm_display_name:

        return (
            f"{event} — "
            f"{storm_display_name}"
        )

    if storm_name:

        return (
            f"{event} — "
            f"{storm_name}"
        )

    return event


def get_display_storm_name(
    alert
):
    """
    Return the best available storm name.

    Preferred:

        Hurricane Gabrielle

    Fallback:

        Gabrielle
    """

    storm_name = safe_text(
        alert.get(
            "storm_display_name"
        )
    )

    if storm_name:
        return storm_name

    return safe_text(
        alert.get(
            "storm_name"
        )
    )


def get_states(
    alert
):
    """
    Return clean unique affected states.
    """

    states = alert.get(
        "affected_states",
        []
    )

    if isinstance(
        states,
        str
    ):

        states = [
            state.strip()
            for state in states.split(",")
            if state.strip()
        ]

    if not isinstance(
        states,
        (
            list,
            tuple,
            set
        )
    ):

        states = []

    return sorted(
        {
            safe_text(state)
            for state in states
            if safe_text(state)
        }
    )


def get_state_text(
    alert
):
    """
    Return affected states as one line.
    """

    states = get_states(
        alert
    )

    if states:

        return ", ".join(
            states
        )

    affected_area = safe_text(
        alert.get(
            "affected_area"
        )
    )

    if affected_area:

        return affected_area

    return (
        "Affected area unavailable"
    )


def get_storm_names(
    alert_summaries
):
    """
    Return unique storms included in the email.
    """

    storm_names = []

    seen = set()

    for alert in alert_summaries:

        name = get_display_storm_name(
            alert
        )

        if not name:
            continue

        key = name.lower()

        if key in seen:
            continue

        seen.add(
            key
        )

        storm_names.append(
            name
        )

    return storm_names


def get_all_states(
    alert_summaries
):
    """
    Return all unique states affected across the email.
    """

    states = set()

    for alert in alert_summaries:

        states.update(
            get_states(
                alert
            )
        )

    return sorted(
        states
    )


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


# ---------------------------------------------------------------------
# STORM FACTS
# ---------------------------------------------------------------------

def build_storm_facts(
    alert
):
    """
    Build concise facts for a storm.

    weather_api.py can supply:

        storm_status
        max_winds
        movement
        pressure

    Missing facts are simply omitted.
    """

    facts = []

    event = safe_text(
        alert.get(
            "event"
        ),
        "Weather Alert"
    )

    severity = safe_text(
        alert.get(
            "severity"
        ),
        "Unknown"
    )

    urgency = safe_text(
        alert.get(
            "urgency"
        )
    )

    storm_status = safe_text(
        alert.get(
            "storm_status"
        )
    )

    max_winds = safe_text(
        alert.get(
            "max_winds"
        )
    )

    movement = safe_text(
        alert.get(
            "movement"
        )
    )

    pressure = safe_text(
        alert.get(
            "pressure"
        )
    )

    affected_states = (
        get_state_text(
            alert
        )
    )

    effective = format_datetime(
        alert.get(
            "effective"
        )
    )

    expires = format_datetime(
        alert.get(
            "ends"
        )
        or alert.get(
            "expires"
        )
    )

    facts.append(
        (
            "Alert",
            event
        )
    )

    if storm_status:

        facts.append(
            (
                "Storm Status",
                storm_status
            )
        )

    facts.append(
        (
            "Severity",
            severity
        )
    )

    if urgency:

        facts.append(
            (
                "Urgency",
                urgency
            )
        )

    facts.append(
        (
            "Affected States",
            affected_states
        )
    )

    if max_winds:

        facts.append(
            (
                "Maximum Winds",
                max_winds
            )
        )

    if movement:

        facts.append(
            (
                "Movement",
                movement
            )
        )

    if pressure:

        facts.append(
            (
                "Pressure",
                pressure
            )
        )

    facts.append(
        (
            "Effective",
            effective
        )
    )

    facts.append(
        (
            "Expires",
            expires
        )
    )

    return facts


# ---------------------------------------------------------------------
# HTML ALERT SECTION
# ---------------------------------------------------------------------

def build_alert_html(
    alert
):
    """
    Build a concise alert card containing quick storm facts.
    """

    storm_name = (
        get_display_storm_name(
            alert
        )
    )

    event = safe_text(
        alert.get(
            "event"
        ),
        "Weather Alert"
    )

    title = (
        storm_name
        or get_alert_title(
            alert
        )
    )

    headline = safe_text(
        alert.get(
            "headline"
        )
    )

    facts = build_storm_facts(
        alert
    )

    bullet_html = ""

    for label, value in facts:

        bullet_html += f"""
            <li
                style="
                    margin:0 0 9px 0;
                    padding:0;
                    line-height:1.5;
                "
            >
                <strong>
                    {escape(label)}:
                </strong>

                {escape(value)}
            </li>
        """

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


# ---------------------------------------------------------------------
# MAP HTML
# ---------------------------------------------------------------------

def build_map_html(
    map_available
):
    """
    Build inline map area.

    Map is referenced using CID and added to the HTML part
    later by attach_inline_map().
    """

    if not map_available:

        return """
            <div
                style="
                    margin:0 0 24px 0;
                    padding:14px;
                    background:#f5f5f5;
                    border-radius:6px;
                    font-size:13px;
                "
            >
                An affected-area map was not available for this alert.
            </div>
        """

    return f"""
        <div
            style="
                margin:0 0 28px 0;
            "
        >

            <div
                style="
                    margin-bottom:10px;
                    font-size:17px;
                    font-weight:bold;
                "
            >
                Affected Area Map
            </div>

            <div
                style="
                    border:1px solid #dddddd;
                    border-radius:8px;
                    overflow:hidden;
                    background:#ffffff;
                "
            >

                <img
                    src="cid:{MAP_CONTENT_ID}"
                    alt="Map of affected weather alert areas"
                    style="
                        width:100%;
                        max-width:720px;
                        height:auto;
                        display:block;
                    "
                >

            </div>

        </div>
    """


# ---------------------------------------------------------------------
# COMPLETE HTML EMAIL
# ---------------------------------------------------------------------

def build_email_html(
    alert_summaries,
    map_available=False
):
    """
    Build the complete HTML email.
    """

    storm_names = get_storm_names(
        alert_summaries
    )

    all_states = get_all_states(
        alert_summaries
    )

    if len(storm_names) == 1:

        header_title = (
            storm_names[0]
        )

    elif len(storm_names) > 1:

        header_title = (
            "Multiple Tropical Systems"
        )

    else:

        header_title = (
            "Severe Tropical Weather"
        )

    if all_states:

        states_text = ", ".join(
            all_states
        )

    else:

        states_text = (
            "See alert details"
        )

    alert_sections = "".join(
        build_alert_html(
            alert
        )
        for alert in alert_summaries
    )

    map_html = build_map_html(
        map_available
    )

    return f"""
<!DOCTYPE html>

<html>

<head>
    <meta charset="UTF-8">
</head>

<body
    style="
        margin:0;
        padding:0;
        background:#f1f1f1;
        font-family:Arial, Helvetica, sans-serif;
        color:#222222;
    "
>

    <div
        style="
            max-width:760px;
            margin:0 auto;
            padding:24px 12px;
        "
    >

        <div
            style="
                background:#ffffff;
                border-radius:8px;
                overflow:hidden;
            "
        >

            <div
                style="
                    background:#111111;
                    color:#ffffff;
                    padding:24px;
                "
            >

                <div
                    style="
                        font-size:12px;
                        font-weight:bold;
                        text-transform:uppercase;
                        letter-spacing:1px;
                    "
                >
                    Nationwide Severe Weather Alert
                </div>

                <div
                    style="
                        margin-top:8px;
                        font-size:29px;
                        font-weight:bold;
                        line-height:1.25;
                    "
                >
                    {escape(header_title)}
                </div>

                <div
                    style="
                        margin-top:10px;
                        font-size:15px;
                        line-height:1.5;
                    "
                >
                    <strong>
                        Affected States:
                    </strong>

                    {escape(states_text)}
                </div>

            </div>

            <div
                style="
                    padding:24px;
                "
            >

                {alert_sections}

                {map_html}

                <div
                    style="
                        margin-top:20px;
                        padding-top:18px;
                        border-top:1px solid #dddddd;
                        color:#666666;
                        font-size:12px;
                        line-height:1.5;
                    "
                >

                    Weather information is based on active
                    National Weather Service products.

                    Conditions may change rapidly.

                    Follow all official National Weather Service
                    and local emergency-management instructions.

                </div>

            </div>

        </div>

    </div>

</body>

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


# ---------------------------------------------------------------------
# INLINE MAP
# ---------------------------------------------------------------------

def attach_inline_map(
    html_part,
    map_file
):
    """
    Embed the generated map directly into the HTML email.

    The HTML references it as:

        cid:affected-area-map

    Returns:
        bool
    """

    if not map_file:

        return False

    if not os.path.exists(
        map_file
    ):

        logger.warning(
            "Map file does not exist: %s",
            map_file
        )

        return False

    try:

        mime_type, _ = (
            mimetypes.guess_type(
                map_file
            )
        )

        if mime_type:

            main_type, sub_type = (
                mime_type.split(
                    "/",
                    1
                )
            )

        else:

            main_type = "image"
            sub_type = "png"

        # Inline content should be an image.
        if main_type != "image":

            logger.warning(
                "Generated map is not an image: %s",
                map_file
            )

            return False

        with open(
            map_file,
            "rb"
        ) as file_handle:

            map_data = (
                file_handle.read()
            )

        html_part.add_related(
            map_data,
            maintype=main_type,
            subtype=sub_type,
            cid=f"<{MAP_CONTENT_ID}>",
            filename=os.path.basename(
                map_file
            ),
            disposition="inline"
        )

        logger.info(
            "Embedded affected-area map: %s",
            map_file
        )

        return True

    except Exception as error:

        logger.exception(
            "Unable to embed map in email: %s",
            error
        )

        return False


# ---------------------------------------------------------------------
# CONFIG VALIDATION
# ---------------------------------------------------------------------

def validate_email_configuration():
    """
    Verify required SMTP settings.
    """

    missing = []

    if not SMTP_SERVER:

        missing.append(
            "SMTP_SERVER"
        )

    if not SMTP_PORT:

        missing.append(
            "SMTP_PORT"
        )

    if not EMAIL_USER:

        missing.append(
            "EMAIL_USER"
        )

    if not EMAIL_PASSWORD:

        missing.append(
            "EMAIL_PASSWORD"
        )

    if not EMAIL_FROM:

        missing.append(
            "EMAIL_FROM"
        )

    if not normalize_recipient_list(
        EMAIL_TO
    ):

        missing.append(
            "EMAIL_TO"
        )

    if missing:

        logger.error(
            "Missing email configuration: %s",
            ", ".join(
                missing
            )
        )

        return False

    return True


# ---------------------------------------------------------------------
# SEND EMAIL
# ---------------------------------------------------------------------

def send_weather_alert(
    alert_summaries,
    map_file=None
):
    """
    Send one consolidated weather alert email.

    Expected usage from main.py:

        send_weather_alert(
            alert_summaries,
            map_file
        )

    Returns:
        True  -> email sent
        False -> email failed
    """

    if not alert_summaries:

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
