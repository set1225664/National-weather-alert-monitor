
"""
Main Application Controller.

Runs the Nationwide Severe Weather Alert System.

Workflow:

1. Check National Weather Service alerts
2. Filter severe and extreme alerts
3. Remove previously sent alerts
4. Generate alert map
5. Send notification email
6. Repeat on schedule
"""

import time
import logging

from config import (
    CHECK_INTERVAL,
    LOG_LEVEL,
    GENERATE_MAPS
)

from utils import setup_logging

from weather_api import (
    get_national_severe_alerts,
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


def process_weather_alerts():
    """
    Executes one complete monitoring cycle.
    """

    logger.info(
        "Checking National Weather Service alerts..."
    )


    # Retrieve active severe alerts
    alerts = get_national_severe_alerts()


    logger.info(
        "Severe alerts detected: %s",
        len(alerts)
    )


    if not alerts:

        logger.info(
            "No severe alerts found."
        )

        return



    # Remove alerts already emailed
    new_alerts = get_new_alerts(
        alerts
    )


    logger.info(
        "New alerts requiring notification: %s",
        len(new_alerts)
    )


    if not new_alerts:

        logger.info(
            "No new alerts to send."
        )

        return



    # Convert alerts for email formatting
    alert_summaries = [
        summarize_alert(alert)
        for alert in new_alerts
    ]



    # Generate map attachment
    map_file = None


    if GENERATE_MAPS:

        logger.info(
            "Generating weather alert map..."
        )

        map_file = generate_national_alert_map(
            new_alerts
        )



    # Send email notification
    logger.info(
        "Sending weather notification..."
    )


    email_sent = send_weather_alert(
        alert_summaries,
        map_file
    )


    if email_sent:

        logger.info(
            "Notification sent successfully."
        )

        update_alert_history(
            new_alerts
        )

    else:

        logger.error(
            "Notification failed. "
            "Alerts will be retried."
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
