```python
"""
Alert Manager Module.

Tracks previously processed weather alerts
to prevent duplicate notifications.
"""

import os
import json
import logging
from datetime import datetime


logger = logging.getLogger(__name__)


ALERT_HISTORY_FILE = "alert_history.json"


def load_alert_history():
    """
    Loads previously processed alert IDs.

    Returns:
        dict: Alert history data
    """

    if not os.path.exists(ALERT_HISTORY_FILE):
        return {}

    try:
        with open(
            ALERT_HISTORY_FILE,
            "r"
        ) as file:

            return json.load(file)

    except Exception as error:

        logger.warning(
            "Unable to load alert history: %s",
            error
        )

        return {}



def save_alert_history(history):
    """
    Saves alert history to disk.
    """

    try:

        with open(
            ALERT_HISTORY_FILE,
            "w"
        ) as file:

            json.dump(
                history,
                file,
                indent=4
            )

    except Exception as error:

        logger.error(
            "Unable to save alert history: %s",
            error
        )



def get_alert_id(alert):
    """
    Extracts unique identifier from NWS alert.

    Returns:
        str: Alert identifier
    """

    properties = alert.get(
        "properties",
        {}
    )

    return properties.get(
        "id",
        ""
    )



def get_new_alerts(alerts):
    """
    Compares current alerts against history.

    Returns:
        list: New alerts only
    """

    history = load_alert_history()

    new_alerts = []


    for alert in alerts:

        alert_id = get_alert_id(
            alert
        )

        if not alert_id:
            continue


        if alert_id not in history:

            new_alerts.append(
                alert
            )


    return new_alerts



def update_alert_history(alerts):
    """
    Records alerts after notification.

    """

    history = load_alert_history()


    for alert in alerts:

        alert_id = get_alert_id(
            alert
        )

        if alert_id:

            history[alert_id] = {
                "sent_at":
                    datetime.utcnow()
                    .isoformat(),

                "event":
                    alert.get(
                        "properties",
                        {}
                    )
                    .get(
                        "event",
                        "Unknown"
                    )
            }


    save_alert_history(
        history
    )



def clear_old_alerts(days=7):
    """
    Removes old alert records.

    Prevents the history file from
    growing indefinitely.
    """

    history = load_alert_history()

    cutoff = datetime.utcnow()


    cleaned_history = {}


    for alert_id, data in history.items():

        try:

            sent_time = datetime.fromisoformat(
                data.get(
                    "sent_at"
                )
            )


            age = (
                cutoff - sent_time
            ).days


            if age <= days:

                cleaned_history[alert_id] = data


        except Exception:

            continue


    save_alert_history(
        cleaned_history
    )



if __name__ == "__main__":

    print(
        "Alert manager module loaded."
    )
```
