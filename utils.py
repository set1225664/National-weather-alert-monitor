```python
"""
Utility Functions Module.

Shared helper functions for the Nationwide
Severe Weather Alert System.
"""

import os
import logging
from datetime import datetime


def setup_logging(log_level="INFO"):
    """
    Configures application logging.

    Args:
        log_level (str):
            Logging level name
    """

    numeric_level = getattr(
        logging,
        log_level.upper(),
        logging.INFO
    )

    logging.basicConfig(
        level=numeric_level,
        format=(
            "%(asctime)s | "
            "%(levelname)s | "
            "%(name)s | "
            "%(message)s"
        ),
        handlers=[
            logging.StreamHandler()
        ]
    )



def create_directory(path):
    """
    Creates a directory if it does not exist.

    Args:
        path (str):
            Directory path
    """

    if not os.path.exists(path):

        os.makedirs(path)



def get_timestamp():
    """
    Returns current timestamp.

    Returns:
        str: Formatted timestamp
    """

    return datetime.utcnow().strftime(
        "%Y-%m-%d %H:%M:%S UTC"
    )



def get_file_timestamp():
    """
    Returns timestamp safe for filenames.

    Returns:
        str: Filename-compatible timestamp
    """

    return datetime.utcnow().strftime(
        "%Y%m%d_%H%M%S"
    )



def format_alert_text(alert):
    """
    Converts alert information into
    readable email text.

    Args:
        alert (dict):
            Alert summary

    Returns:
        str:
            Formatted alert message
    """

    return f"""
Weather Event:
{alert.get('event', 'Unknown')}

Severity:
{alert.get('severity', 'Unknown')}

Affected Area:
{alert.get('area', 'Unknown')}

Expires:
{alert.get('expires', 'Unknown')}

Details:
{alert.get('description', 'No details available')}
"""



def clean_filename(filename):
    """
    Removes unsafe filename characters.

    Args:
        filename (str)

    Returns:
        str
    """

    invalid_characters = [
        "<",
        ">",
        ":",
        '"',
        "/",
        "\\",
        "|",
        "?",
        "*"
    ]


    for character in invalid_characters:

        filename = filename.replace(
            character,
            "_"
        )


    return filename



def write_text_file(path, content):
    """
    Writes text content to a file.

    Args:
        path (str):
            File path

        content (str):
            Text content
    """

    directory = os.path.dirname(
        path
    )


    if directory:

        create_directory(
            directory
        )


    with open(
        path,
        "w",
        encoding="utf-8"
    ) as file:

        file.write(
            content
        )



if __name__ == "__main__":

    setup_logging()

    logging.info(
        "Utility module loaded."
    )
```
