```python
"""
Email Notification Module.

Creates and sends nationwide severe weather
alert emails with generated weather maps.
"""

import os
import logging
import smtplib

from email.message import EmailMessage
from email.utils import formataddr

from config import (
    SMTP_SERVER,
    SMTP_PORT,
    EMAIL_FROM,
    EMAIL_TO,
    EMAIL_PASSWORD
)


logger = logging.getLogger(__name__)


def format_alert_html(alerts):
    """
    Creates HTML content from weather alerts.

    Args:
        alerts (list):
            List of summarized alert dictionaries

    Returns:
        str:
            HTML email body
    """

    if not alerts:
        return """
        <html>
        <body>
            <h2>No Active Severe Weather Alerts</h2>
            <p>The monitoring system completed a check
            and found no qualifying alerts.</p>
        </body>
        </html>
        """


    alert_sections = ""


    for alert in alerts:

        alert_sections += f"""
        <hr>

        <h2>{alert.get('event')}</h2>

        <p>
        <strong>Severity:</strong>
        {alert.get('severity')}
        </p>

        <p>
        <strong>Area:</strong>
        {alert.get('area')}
        </p>

        <p>
        <strong>Expires:</strong>
        {alert.get('expires')}
        </p>

        <p>
        <strong>Headline:</strong><br>
        {alert.get('headline')}
        </p>

        <p>
        {alert.get('description')}
        </p>
        """


    return f"""
    <html>
    <body>

    <h1>
    National Severe Weather Alert
    </h1>

    <p>
    The National Weather Service has issued
    the following severe weather alerts:
    </p>

    {alert_sections}

    <br>

    <p>
    This notification was generated automatically
    by the Nationwide Severe Weather Alert System.
    </p>

    </body>
    </html>
    """


def create_email(alerts, map_file=None):
    """
    Builds email message.

    Args:
        alerts (list):
            Alert summaries

        map_file (str):
            Optional weather map attachment

    Returns:
        EmailMessage
    """

    message = EmailMessage()


    message["Subject"] = (
        f"SEVERE WEATHER ALERT: "
        f"{len(alerts)} Active Alert(s)"
    )

    message["From"] = formataddr(
        (
            "Weather Monitoring System",
            EMAIL_FROM
        )
    )

    message["To"] = EMAIL_TO


    message.set_content(
        "Severe weather alerts detected. "
        "Please view the HTML version."
    )


    message.add_alternative(
        format_alert_html(alerts),
        subtype="html"
    )


    if map_file and os.path.exists(map_file):

        with open(
            map_file,
            "rb"
        ) as file:

            image_data = file.read()


        message.add_attachment(
            image_data,
            maintype="image",
            subtype="png",
            filename=os.path.basename(
                map_file
            )
        )


    return message



def send_email(message):
    """
    Sends email through SMTP server.
    """

    try:

        with smtplib.SMTP(
            SMTP_SERVER,
            SMTP_PORT
        ) as server:

            server.starttls()

            server.login(
                EMAIL_FROM,
                EMAIL_PASSWORD
            )

            server.send_message(
                message
            )


        logger.info(
            "Weather alert email sent successfully."
        )

        return True


    except Exception as error:

        logger.error(
            "Unable to send email: %s",
            error
        )

        return False



def send_weather_alert(alerts, map_file=None):
    """
    Convenience function used by main.py.
    """

    email = create_email(
        alerts,
        map_file
    )

    return send_email(
        email
    )



if __name__ == "__main__":

    print(
        "Email module loaded."
    )
```
