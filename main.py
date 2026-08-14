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
from copy import deepcopy

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


def _get_properties(alert):
    """
    Safely return the NWS properties dictionary.
    """

    return alert.get("properties", alert)


def _split_areas(area_desc):
    """
    Convert an NWS areaDesc string into individual affected areas.

    NWS normally separates areas with semicolons.
    """

    if not area_desc:
        return []

    return [
        area.strip()
        for area in area_desc.split(";")
        if area.strip()
    ]


def _get_group_key(alert):
    """
    Determine which alerts belong in the same consolidated notice.

    Alerts with the same event type, headline, timing, and issuing
    office are treated as parts of the same weather notice.

    Examples:
        Hurricane Warning -> one notice
        Storm Surge Warning -> one notice
        Tropical Storm Warning -> one notice

    Different alert types remain separate.
    """

    properties = _get_properties(alert)

    event = properties.get("event", "").strip()
    headline = properties.get("headline", "").strip()
    effective = properties.get("effective", "")
    expires = properties.get("expires", "")
    sender = properties.get("senderName", "").strip()

    return (
        event,
        headline,
        effective,
        expires,
        sender
    )


def consolidate_alerts(alerts):
    """
    Combine related NWS alerts into condensed notices.

    All affected areas for the same warning/watch are merged into
    one alert.

    Original alert IDs are retained so the alert history can still
    track every NWS alert that contributed to the notice.
    """

    grouped = {}

    for alert in alerts:

        properties = _get_properties(alert)

        group_key = _get_group_key(alert)

        if group_key not in grouped:

            consolidated = deepcopy(alert)

            consolidated_properties = _get_properties(
                consolidated
            )

            consolidated_properties["affectedAreas"] = []

            consolidated["_source_alert_ids"] = []
            consolidated["_source_alerts"] = []

            grouped[group_key] = consolidated

        consolidated = grouped[group_key]

        consolidated_properties = _get_properties(
            consolidated
        )

        # Keep a copy of every original alert
        consolidated["_source_alerts"].append(
            alert
        )

        # Save original NWS IDs
        alert_id = alert.get("id")

        if alert_id:
            consolidated["_source_alert_ids"].append(
                alert_id
            )

        # Collect affected areas
        area_desc = properties.get(
            "areaDesc",
            ""
        )

        areas = _split_areas(
            area_desc
        )

        consolidated_properties[
            "affectedAreas"
        ].extend(areas)

    consolidated_alerts = []

    for consolidated in grouped.values():

        properties = _get_properties(
            consolidated
        )

        # Remove duplicate affected areas while preserving
        # alphabetical order.
        unique_areas = sorted(
            set(
                properties.get(
                    "affectedAreas",
                    []
                )
            )
        )

        properties[
            "affectedAreas"
        ] = unique_areas

        properties[
            "areaDesc"
        ] = "; ".join(
            unique_areas
        )

        # Remove duplicate source IDs
        consolidated[
            "_source_alert_ids"
        ] = list(
            dict.fromkeys(
                consolidated.get(
                    "_source_alert_ids",
                    []
                )
            )
        )

        consolidated_alerts.append(
            consolidated
        )

    return consolidated_alerts


def get_groups_requiring_notification(
    all_alerts,
    new_alerts
):
    """
    Return complete consolidated alert groups when at least one
    underlying NWS alert in that group is new.

    This is important because if a hurricane warning expands into
    additional counties, the next email should contain ALL areas
    currently affected by that warning rather than only the newly
    added counties.
    """

    if not new_alerts:
        return []

    new_alert_ids = {
        alert.get("id")
        for alert in new_alerts
        if alert.get("id")
    }

    new_group_keys = {
        _get_group_key(alert)
        for alert in new_alerts
    }

    consolidated = consolidate_alerts(
        all_alerts
    )

    groups_to_send = []

    for alert in consolidated:

        group_key = _get_group_key(
            alert
        )

        source_ids = set(
            alert.get(
                "_source_alert_ids",
                []
            )
        )

        # Send the complete group if:
        # 1. its grouping key contains a newly detected alert, OR
        # 2. one of its source IDs is new.
        if (
            group_key in new_group_keys
            or source_ids.intersection(
                new_alert_ids
            )
        ):
            groups_to_send.append(
                alert
            )

    return groups_to_send


def get_original_alerts(
    consolidated_alerts
):
    """
    Extract all original NWS alerts from consolidated alerts.

    These are passed to update_alert_history() so every underlying
    alert ID is marked as processed.
    """

    original_alerts = []

    seen_ids = set()

    for consolidated in consolidated_alerts:

        for alert in consolidated.get(
            "_source_alerts",
            []
        ):

            alert_id = alert.get("id")

            if alert_id:

                if alert_id in seen_ids:
                    continue

                seen_ids.add(
                    alert_id
                )

            original_alerts.append(
                alert
            )

    return original_alerts


def process_weather_alerts():
    """
    Executes one complete hurricane monitoring cycle.
    """

    logger.info(
        "Checking National Weather Service hurricane alerts..."
    )

    # Retrieve all currently active hurricane alerts
    alerts = get_national_hurricane_alerts()

    logger.info(
        "Hurricane alerts detected: %s",
        len(alerts)
    )

    if not alerts:

        logger.info(
            "No hurricane alerts found."
        )

        return

    # Determine which underlying NWS alerts have not already
    # triggered an email.
    new_alerts = get_new_alerts(
        alerts
    )

    logger.info(
        "New hurricane alerts requiring notification: %s",
        len(new_alerts)
    )

    if not new_alerts:

        logger.info(
            "No new hurricane alerts to send."
        )

        return

    # Consolidate the full active warning groups.
    #
    # If a warning has expanded since the previous check,
    # the email will contain ALL currently affected areas,
    # not just the newly added ones.
    consolidated_alerts = (
        get_groups_requiring_notification(
            alerts,
            new_alerts
        )
    )

    logger.info(
        "Consolidated notices being sent: %s",
        len(consolidated_alerts)
    )

    if not consolidated_alerts:

        logger.info(
            "No consolidated hurricane notices to send."
        )

        return

    # Log the size of each consolidated notice
    for alert in consolidated_alerts:

        properties = _get_properties(
            alert
        )

        logger.info(
            "%s: %s affected areas",
            properties.get(
                "event",
                "Weather Alert"
            ),
            len(
                properties.get(
                    "affectedAreas",
                    []
                )
            )
        )

    # Convert consolidated alerts into the format expected
    # by the email template.
    alert_summaries = [
        summarize_alert(alert)
        for alert in consolidated_alerts
    ]

    # Generate one map covering all consolidated warnings.
    map_file = None

    if GENERATE_MAPS:

        logger.info(
            "Generating consolidated hurricane alert map..."
        )

        map_file = generate_national_alert_map(
            consolidated_alerts
        )

    # Send one notification email.
    logger.info(
        "Sending condensed hurricane notification..."
    )

    email_sent = send_weather_alert(
        alert_summaries,
        map_file
    )

    if email_sent:

        logger.info(
            "Condensed hurricane notification sent successfully."
        )

        # Mark all original NWS alerts contained in the
        # consolidated notices as processed.
        alerts_to_record = get_original_alerts(
            consolidated_alerts
        )

        update_alert_history(
            alerts_to_record
        )

        logger.info(
            "%s underlying NWS alerts added to history.",
            len(alerts_to_record)
        )

    else:

        logger.error(
            "Notification failed. Alerts will be retried."
        )


def run_monitor():
    """
    Runs continuous monitoring loop.
    """

    logger.info(
        "Starting Nationwide Severe Weather Monitoring System"
    )

    while True:

        try:

            clear_old_alerts()

            process_weather_alerts()

        except Exception as error:

            logger.exception(
                "Monitoring cycle failed: %s",
                error
            )

        logger.info(
            "Waiting %s minutes until next check...",
            CHECK_INTERVAL
        )

        time.sleep(
            CHECK_INTERVAL * 60
        )


if __name__ == "__main__":

    setup_logging(
        LOG_LEVEL
    )

    process_weather_alerts()
