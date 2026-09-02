"""
Email Notification System.

Creates and sends condensed severe tropical weather notifications.

Designed to work with:

    main.py
    weather_api.py
    map_generator.py

Email format includes:

1. Named storm / hurricane
2. Alert type
3. Severity
4. Affected states
5. Effective and expiration times
6. Condensed NWS headline / description
7. Safety instructions
8. Generated weather alert map attachment

County and zone lists are intentionally NOT displayed in the email.
The email displays affected states instead.
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
    # Fallback configuration allows environment variables to be used
    # if the names above are not defined in config.py.

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
# EMAIL APPEARANCE
# ---------------------------------------------------------------------

SYSTEM_NAME = "Nationwide Severe Weather Alert System"

FROM_DISPLAY_NAME = "National Weather Alert Monitor"


# ---------------------------------------------------------------------
# GENERAL HELPERS
# ---------------------------------------------------------------------

def safe_text(value, default=""):
    """
    Safely convert a value into displayable text.
    """

    if value is None:
        return default

    value = str(value).strip()

    if not value:
        return default

    return value


def normalize_recipient_list(recipients):
    """
    Convert EMAIL_TO into a clean list of recipient email addresses.

    Supports:

        "one@example.com"

        "one@example.com,two@example.com"

        ["one@example.com", "two@example.com"]
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


def format_datetime(value):
    """
    Convert an ISO NWS date/time string into a cleaner display format.

    Example:

        2026-09-02T14:00:00-04:00

    becomes approximately:

        Sep 02, 2026 at 2:00 PM EDT

    If parsing fails, the original value is returned.
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

        timezone_name = parsed.tzname()

        formatted = parsed.strftime(
            "%b %d, %Y at %I:%M %p"
        )

        # Remove leading zero from hour.
        formatted = formatted.replace(
            " at 0",
            " at "
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


def get_alert_title(alert):
    """
    Build the primary display title for an alert.

    Preferred result:

        Hurricane Warning — Hurricane Gabrielle
    """

    title = safe_text(
        alert.get("title")
    )

    if title:
        return title

    event = safe_text(
        alert.get("event"),
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


def get_states(alert):
    """
    Return a clean list of affected states.

    The updated weather_api.py provides affected_states directly.
    """

    states = alert.get(
        "affected_states",
        []
    )

    if isinstance(states, str):

        states = [
            state.strip()
            for state in states.split(",")
            if state.strip()
        ]

    if not isinstance(
        states,
        (list, tuple, set)
    ):

        states = []

    cleaned_states = sorted(
        {
            safe_text(state)
            for state in states
            if safe_text(state)
        }
    )

    return cleaned_states


def get_state_text(alert):
    """
    Return affected states as one concise display string.

    Example:

        Florida, Georgia, South Carolina
    """

    states = get_states(
        alert
    )

    if states:

        return ", ".join(
            states
        )

    # Fallback to weather_api's condensed affected_area field.
    affected_area = safe_text(
        alert.get(
            "affected_area"
        )
    )

    if affected_area:

        return affected_area

    return "Affected area unavailable"


def get_storm_names(alert_summaries):
    """
    Return all unique named storms appearing in this notification.
    """

    names = []

    seen = set()

    for alert in alert_summaries:

        name = safe_text(
            alert.get(
                "storm_display_name"
            )
        )

        if not name:

            name = safe_text(
                alert.get(
                    "storm_name"
                )
            )

        if not name:
            continue

        lower_name = name.lower()

        if lower_name in seen:
            continue

        seen.add(
            lower_name
        )

        names.append(
            name
        )

    return names


def get_all_states(alert_summaries):
    """
    Return all unique states represented across the entire email.
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
# SUBJECT LINE
# ---------------------------------------------------------------------

def build_email_subject(alert_summaries):
    """
    Create a useful condensed subject line.

    Examples:

        WEATHER ALERT: Hurricane Gabrielle — Florida, Georgia

        WEATHER ALERT: Hurricane Warning — Florida

        WEATHER ALERT: Hurricane Gabrielle — 4 States
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

        event_types = []

        seen_events = set()

        for alert in alert_summaries:

            event = safe_text(
                alert.get("event")
            )

            if not event:
                continue

            if event.lower() in seen_events:
                continue

            seen_events.add(
                event.lower()
            )

            event_types.append(
                event
            )

        if len(event_types) == 1:

            primary = event_types[0]

        else:

            primary = (
                "Severe Tropical Weather"
            )

    if len(states) == 1:

        location = states[0]

    elif 1 < len(states) <= 3:

        location = ", ".join(
            states
        )

    elif len(states) > 3:

        location = (
            f"{len(states)} States/Territories"
        )

    else:

        location = ""

    subject = (
        f"WEATHER ALERT: {primary}"
    )

    if location:

        subject += (
            f" — {location}"
        )

    return subject


# ---------------------------------------------------------------------
# HTML EMAIL
# ---------------------------------------------------------------------

def severity_badge_html(severity):
    """
    Return a simple severity badge.
    """

    severity = safe_text(
        severity,
        "Unknown"
    )

    return f"""
        <span
            style="
                display:inline-block;
                padding:5px 10px;
                border-radius:4px;
                background:#eeeeee;
                font-size:13px;
                font-weight:bold;
            "
        >
            {escape(severity)}
        </span>
    """


def build_alert_html(alert):
    """
    Build one condensed alert section.

    County and zone details are deliberately excluded.
    """

    title = get_alert_title(
        alert
    )

    event = safe_text(
        alert.get("event"),
        "Weather Alert"
    )

    storm_name = safe_text(
        alert.get(
            "storm_display_name"
        )
    )

    if not storm_name:

        storm_name = safe_text(
            alert.get(
                "storm_name"
            )
        )

    severity = safe_text(
        alert.get("severity"),
        "Unknown"
    )

    urgency = safe_text(
        alert.get("urgency")
    )

    states = get_state_text(
        alert
    )

    headline = safe_text(
        alert.get("headline")
    )

    description = safe_text(
        alert.get("description")
    )

    instruction = safe_text(
        alert.get("instruction")
    )

    effective = format_datetime(
        alert.get("effective")
    )

    onset = format_datetime(
        alert.get("onset")
    )

    expires_value = (
        alert.get("ends")
        or alert.get("expires")
    )

    expires = format_datetime(
        expires_value
    )

    # -------------------------------------------------------------
    # NAMED STORM
    # -------------------------------------------------------------

    storm_html = ""

    if storm_name:

        storm_html = f"""
            <div
                style="
                    margin-bottom:16px;
                    padding:12px 14px;
                    background:#f2f2f2;
                    border-radius:6px;
                "
            >
                <div
                    style="
                        font-size:12px;
                        font-weight:bold;
                        text-transform:uppercase;
                        letter-spacing:0.5px;
                        margin-bottom:4px;
                    "
                >
                    Named Storm
                </div>

                <div
                    style="
                        font-size:21px;
                        font-weight:bold;
                    "
                >
                    {escape(storm_name)}
                </div>
            </div>
        """

    # -------------------------------------------------------------
    # HEADLINE
    # -------------------------------------------------------------

    headline_html = ""

    if (
        headline
        and headline.lower()
        != title.lower()
    ):

        headline_html = f"""
            <p
                style="
                    font-size:15px;
                    font-weight:bold;
                    line-height:1.5;
                    margin:18px 0 8px 0;
                "
            >
                {escape(headline)}
            </p>
        """

    # -------------------------------------------------------------
    # DESCRIPTION
    # -------------------------------------------------------------

    description_html = ""

    if description:

        description_html = f"""
            <div
                style="
                    margin-top:14px;
                    font-size:14px;
                    line-height:1.6;
                    white-space:pre-line;
                "
            >
                {escape(description)}
            </div>
        """

    # -------------------------------------------------------------
    # INSTRUCTIONS
    # -------------------------------------------------------------

    instruction_html = ""

    if instruction:

        instruction_html = f"""
            <div
                style="
                    margin-top:18px;
                    padding:14px;
                    border-left:4px solid #555555;
                    background:#f7f7f7;
                "
            >
                <div
                    style="
                        font-weight:bold;
                        margin-bottom:6px;
                    "
                >
                    Safety Instructions
                </div>

                <div
                    style="
                        font-size:14px;
                        line-height:1.6;
                        white-space:pre-line;
                    "
                >
                    {escape(instruction)}
                </div>
            </div>
        """

    urgency_html = ""

    if urgency:

        urgency_html = f"""
            <tr>
                <td
                    style="
                        padding:6px 10px 6px 0;
                        font-weight:bold;
                        vertical-align:top;
                    "
                >
                    Urgency
                </td>

                <td
                    style="
                        padding:6px 0;
                    "
                >
                    {escape(urgency)}
                </td>
            </tr>
        """

    return f"""
        <div
            style="
                margin-bottom:28px;
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
                        font-size:22px;
                        font-weight:bold;
                        line-height:1.3;
                    "
                >
                    {escape(title)}
                </div>

                <div
                    style="
                        margin-top:8px;
                    "
                >
                    {severity_badge_html(severity)}
                </div>

            </div>

            <div
                style="
                    padding:20px;
                "
            >

                {storm_html}

                <table
                    width="100%"
                    cellpadding="0"
                    cellspacing="0"
                    style="
                        border-collapse:collapse;
                        font-size:14px;
                    "
                >

                    <tr>
                        <td
                            style="
                                padding:6px 10px 6px 0;
                                font-weight:bold;
                                vertical-align:top;
                                width:135px;
                            "
                        >
                            Alert Type
                        </td>

                        <td
                            style="
                                padding:6px 0;
                            "
                        >
                            {escape(event)}
                        </td>
                    </tr>

                    <tr>
                        <td
                            style="
                                padding:6px 10px 6px 0;
                                font-weight:bold;
                                vertical-align:top;
                            "
                        >
                            Affected States
                        </td>

                        <td
                            style="
                                padding:6px 0;
                                font-weight:bold;
                            "
                        >
                            {escape(states)}
                        </td>
                    </tr>

                    <tr>
                        <td
                            style="
                                padding:6px 10px 6px 0;
                                font-weight:bold;
                                vertical-align:top;
                            "
                        >
                            Severity
                        </td>

                        <td
                            style="
                                padding:6px 0;
                            "
                        >
                            {escape(severity)}
                        </td>
                    </tr>

                    {urgency_html}

                    <tr>
                        <td
                            style="
                                padding:6px 10px 6px 0;
                                font-weight:bold;
                                vertical-align:top;
                            "
                        >
                            Effective
                        </td>

                        <td
                            style="
                                padding:6px 0;
                            "
                        >
                            {escape(effective)}
                        </td>
                    </tr>

                    <tr>
                        <td
                            style="
                                padding:6px 10px 6px 0;
                                font-weight:bold;
                                vertical-align:top;
                            "
                        >
                            Onset
                        </td>

                        <td
                            style="
                                padding:6px 0;
                            "
                        >
                            {escape(onset)}
                        </td>
                    </tr>

                    <tr>
                        <td
                            style="
                                padding:6px 10px 6px 0;
                                font-weight:bold;
                                vertical-align:top;
                            "
                        >
                            Expires
                        </td>

                        <td
                            style="
                                padding:6px 0;
                            "
                        >
                            {escape(expires)}
                        </td>
                    </tr>

                </table>

                {headline_html}

                {description_html}

                {instruction_html}

            </div>

        </div>
    """


def build_email_html(
    alert_summaries,
    map_attached=False
):
    """
    Build the complete HTML notification.
    """

    storm_names = get_storm_names(
        alert_summaries
    )

    all_states = get_all_states(
        alert_summaries
    )

    alert_count = len(
        alert_summaries
    )

    # -------------------------------------------------------------
    # TOP SUMMARY
    # -------------------------------------------------------------

    if len(storm_names) == 1:

        top_title = storm_names[0]

    elif len(storm_names) > 1:

        top_title = (
            "Multiple Tropical Systems"
        )

    else:

        top_title = (
            "Severe Tropical Weather"
        )

    if all_states:

        state_text = ", ".join(
            all_states
        )

    else:

        state_text = (
            "See alert details below"
        )

    storm_summary_html = ""

    if storm_names:

        storm_summary_html = f"""
            <div
                style="
                    margin-top:10px;
                    font-size:17px;
                    font-weight:bold;
                "
            >
                {escape(", ".join(storm_names))}
            </div>
        """

    map_message = ""

    if map_attached:

        map_message = """
            <div
                style="
                    margin:0 0 22px 0;
                    padding:12px 14px;
                    background:#f5f5f5;
                    border-radius:6px;
                    font-size:13px;
                "
            >
                A national alert / prediction map is attached to this
                notification.
            </div>
        """

    alert_sections = "".join(
        build_alert_html(alert)
        for alert in alert_summaries
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
                        font-size:28px;
                        font-weight:bold;
                        margin-top:8px;
                    "
                >
                    {escape(top_title)}
                </div>

                {storm_summary_html}

            </div>

            <div
                style="
                    padding:24px;
                "
            >

                <div
                    style="
                        margin-bottom:22px;
                        padding-bottom:18px;
                        border-bottom:1px solid #dddddd;
                    "
                >

                    <div
                        style="
                            font-size:14px;
                            margin-bottom:5px;
                        "
                    >
                        <strong>Affected States:</strong>
                        {escape(state_text)}
                    </div>

                    <div
                        style="
                            font-size:14px;
                        "
                    >
                        <strong>Active Notices:</strong>
                        {alert_count}
                    </div>

                </div>

                {map_message}

                {alert_sections}

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
                    Weather information is provided from active
                    National Weather Service products. Conditions and
                    warnings may change rapidly. Follow official local
                    emergency-management and National Weather Service
                    instructions.
                </div>

            </div>

        </div>

    </div>

</body>
</html>
    """


# ---------------------------------------------------------------------
# PLAIN-TEXT EMAIL
# ---------------------------------------------------------------------

def build_plain_text_email(alert_summaries):
    """
    Build a plain-text fallback version of the notification.
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
            "NAMED STORM:"
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

        title = get_alert_title(
            alert
        )

        storm_name = safe_text(
            alert.get(
                "storm_display_name"
            )
        )

        if not storm_name:

            storm_name = safe_text(
                alert.get(
                    "storm_name"
                )
            )

        lines.extend([
            title,
            "-" * len(title),
            ""
        ])

        if storm_name:

            lines.append(
                f"Storm: {storm_name}"
            )

        lines.extend([
            (
                "Alert Type: "
                f"{safe_text(alert.get('event'), 'Weather Alert')}"
            ),
            (
                "Severity: "
                f"{safe_text(alert.get('severity'), 'Unknown')}"
            ),
            (
                "Affected States: "
                f"{get_state_text(alert)}"
            ),
            (
                "Effective: "
                f"{format_datetime(alert.get('effective'))}"
            ),
            (
                "Expires: "
                f"{format_datetime(alert.get('ends') or alert.get('expires'))}"
            ),
            ""
        ])

        headline = safe_text(
            alert.get("headline")
        )

        if headline:

            lines.extend([
                headline,
                ""
            ])

        description = safe_text(
            alert.get("description")
        )

        if description:

            lines.extend([
                description,
                ""
            ])

        instruction = safe_text(
            alert.get("instruction")
        )

        if instruction:

            lines.extend([
                "SAFETY INSTRUCTIONS:",
                instruction,
                ""
            ])

        lines.extend([
            "=" * 60,
            ""
        ])

    lines.extend([
        (
            "Weather information is based on active "
            "National Weather Service products."
        ),
        (
            "Follow official local emergency-management "
            "instructions."
        )
    ])

    return "\n".join(
        lines
    )


# ---------------------------------------------------------------------
# FILE ATTACHMENT
# ---------------------------------------------------------------------

def attach_map(
    message,
    map_file
):
    """
    Attach the generated weather map to the email.

    Returns True when an attachment was successfully added.
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

        mime_type, _ = mimetypes.guess_type(
            map_file
        )

        if mime_type:

            main_type, sub_type = mime_type.split(
                "/",
                1
            )

        else:

            main_type = "application"
            sub_type = "octet-stream"

        with open(
            map_file,
            "rb"
        ) as file_handle:

            file_data = file_handle.read()

        message.add_attachment(
            file_data,
            maintype=main_type,
            subtype=sub_type,
            filename=os.path.basename(
                map_file
            )
        )

        logger.info(
            "Attached weather map: %s",
            map_file
        )

        return True

    except Exception as error:

        logger.exception(
            "Unable to attach map file: %s",
            error
        )

        return False


# ---------------------------------------------------------------------
# CONFIG VALIDATION
# ---------------------------------------------------------------------

def validate_email_configuration():
    """
    Validate required email settings before attempting SMTP delivery.

    Returns:
        bool
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
            ", ".join(missing)
        )

        return False

    return True


# ---------------------------------------------------------------------
# EMAIL DELIVERY
# ---------------------------------------------------------------------

def send_weather_alert(
    alert_summaries,
    map_file=None
):
    """
    Send one condensed notification email containing all consolidated
    weather alerts.

    This function is called from main.py as:

        send_weather_alert(
            alert_summaries,
            map_file
        )

    Args:
        alert_summaries:
            List of dictionaries produced by
            weather_api.summarize_alert().

        map_file:
            Optional path to generated map image.

    Returns:
        bool:
            True if the email was sent successfully.
            False if sending failed.
    """

    if not alert_summaries:

        logger.info(
            "No weather alerts supplied to emailer."
        )

        return False

    if not validate_email_configuration():

        logger.error(
            "Email configuration is incomplete."
        )

        return False

    recipients = normalize_recipient_list(
        EMAIL_TO
    )

    subject = build_email_subject(
        alert_summaries
    )

    # Determine whether the map exists before creating the HTML
    # message so the body can mention the attachment accurately.
    map_available = bool(
        map_file
        and os.path.exists(
            map_file
        )
    )

    plain_text_body = build_plain_text_email(
        alert_summaries
    )

    html_body = build_email_html(
        alert_summaries,
        map_attached=map_available
    )

    message = EmailMessage()

    message["Subject"] = subject

    message["From"] = formataddr(
        (
            FROM_DISPLAY_NAME,
            EMAIL_FROM
        )
    )

    message["To"] = ", ".join(
        recipients
    )

    # Plain-text fallback.
    message.set_content(
        plain_text_body
    )

    # HTML version.
    message.add_alternative(
        html_body,
        subtype="html"
    )

    # Attach generated map.
    if map_available:

        attach_map(
            message,
            map_file
        )

    logger.info(
        "Preparing weather notification for %s recipient(s).",
        len(recipients)
    )

    logger.info(
        "Email subject: %s",
        subject
    )

    try:

        # Port 465 normally uses implicit SSL.
        if int(SMTP_PORT) == 465:

            with smtplib.SMTP_SSL(
                SMTP_SERVER,
                int(SMTP_PORT),
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

        else:

            # Port 587 normally uses STARTTLS.
            with smtplib.SMTP(
                SMTP_SERVER,
                int(SMTP_PORT),
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
