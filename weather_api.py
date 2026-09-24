"""
National Weather Service API Client.

Retrieves active tropical weather alerts from the National Weather
Service and converts them into concise storm summaries for email
notifications.

Features:

1. Retrieves active nationwide NWS alerts
2. Filters hurricane and tropical-system alerts
3. Extracts named storms
4. Extracts storm classification/status
5. Extracts maximum sustained winds
6. Extracts storm movement and speed
7. Extracts central pressure
8. Converts affected counties/zones into affected states
9. Preserves detailed area data for maps
10. Creates condensed alert summaries for email notifications
"""

import logging
import re

import requests


logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------
# NWS API SETTINGS
# ---------------------------------------------------------------------

NWS_ALERTS_URL = "https://api.weather.gov/alerts/active"

NWS_HEADERS = {
    "User-Agent": (
        "Nationwide-Severe-Weather-Alert-System/1.0 "
        "(weather-alert-monitor)"
    ),
    "Accept": "application/geo+json",
}

REQUEST_TIMEOUT = 30


# ---------------------------------------------------------------------
# TROPICAL ALERT TYPES
# ---------------------------------------------------------------------

TROPICAL_ALERT_TYPES = {
    "Hurricane Warning",
    "Hurricane Watch",
    "Hurricane Local Statement",
    "Hurricane Force Wind Warning",
    "Hurricane Force Wind Watch",
    "Tropical Storm Warning",
    "Tropical Storm Watch",
    "Tropical Storm Local Statement",
    "Storm Surge Warning",
    "Storm Surge Watch",
    "Extreme Wind Warning",
    "Tropical Cyclone Statement",
    "Tropical Cyclone Local Statement",
    "Typhoon Warning",
    "Typhoon Watch",
}


# ---------------------------------------------------------------------
# STATE INFORMATION
# ---------------------------------------------------------------------

STATE_ABBREVIATIONS = {
    "AL": "Alabama",
    "AK": "Alaska",
    "AZ": "Arizona",
    "AR": "Arkansas",
    "CA": "California",
    "CO": "Colorado",
    "CT": "Connecticut",
    "DE": "Delaware",
    "FL": "Florida",
    "GA": "Georgia",
    "HI": "Hawaii",
    "ID": "Idaho",
    "IL": "Illinois",
    "IN": "Indiana",
    "IA": "Iowa",
    "KS": "Kansas",
    "KY": "Kentucky",
    "LA": "Louisiana",
    "ME": "Maine",
    "MD": "Maryland",
    "MA": "Massachusetts",
    "MI": "Michigan",
    "MN": "Minnesota",
    "MS": "Mississippi",
    "MO": "Missouri",
    "MT": "Montana",
    "NE": "Nebraska",
    "NV": "Nevada",
    "NH": "New Hampshire",
    "NJ": "New Jersey",
    "NM": "New Mexico",
    "NY": "New York",
    "NC": "North Carolina",
    "ND": "North Dakota",
    "OH": "Ohio",
    "OK": "Oklahoma",
    "OR": "Oregon",
    "PA": "Pennsylvania",
    "RI": "Rhode Island",
    "SC": "South Carolina",
    "SD": "South Dakota",
    "TN": "Tennessee",
    "TX": "Texas",
    "UT": "Utah",
    "VT": "Vermont",
    "VA": "Virginia",
    "WA": "Washington",
    "WV": "West Virginia",
    "WI": "Wisconsin",
    "WY": "Wyoming",
    "DC": "District of Columbia",

    # Territories
    "PR": "Puerto Rico",
    "VI": "U.S. Virgin Islands",
    "GU": "Guam",
    "AS": "American Samoa",
    "MP": "Northern Mariana Islands",
}


STATE_FIPS = {
    "01": "Alabama",
    "02": "Alaska",
    "04": "Arizona",
    "05": "Arkansas",
    "06": "California",
    "08": "Colorado",
    "09": "Connecticut",
    "10": "Delaware",
    "11": "District of Columbia",
    "12": "Florida",
    "13": "Georgia",
    "15": "Hawaii",
    "16": "Idaho",
    "17": "Illinois",
    "18": "Indiana",
    "19": "Iowa",
    "20": "Kansas",
    "21": "Kentucky",
    "22": "Louisiana",
    "23": "Maine",
    "24": "Maryland",
    "25": "Massachusetts",
    "26": "Michigan",
    "27": "Minnesota",
    "28": "Mississippi",
    "29": "Missouri",
    "30": "Montana",
    "31": "Nebraska",
    "32": "Nevada",
    "33": "New Hampshire",
    "34": "New Jersey",
    "35": "New Mexico",
    "36": "New York",
    "37": "North Carolina",
    "38": "North Dakota",
    "39": "Ohio",
    "40": "Oklahoma",
    "41": "Oregon",
    "42": "Pennsylvania",
    "44": "Rhode Island",
    "45": "South Carolina",
    "46": "South Dakota",
    "47": "Tennessee",
    "48": "Texas",
    "49": "Utah",
    "50": "Vermont",
    "51": "Virginia",
    "53": "Washington",
    "54": "West Virginia",
    "55": "Wisconsin",
    "56": "Wyoming",

    # Territories
    "60": "American Samoa",
    "66": "Guam",
    "69": "Northern Mariana Islands",
    "72": "Puerto Rico",
    "78": "U.S. Virgin Islands",
}


# ---------------------------------------------------------------------
# BASIC ALERT HELPERS
# ---------------------------------------------------------------------

def get_alert_properties(alert):
    """
    Return the NWS properties dictionary.
    """

    if not isinstance(alert, dict):
        return {}

    properties = alert.get("properties")

    if isinstance(properties, dict):
        return properties

    return alert


def normalize_text(value):
    """
    Safely normalize API text values.
    """

    if value is None:
        return ""

    return str(value).strip()


def get_alert_text(alert):
    """
    Combine useful NWS text fields for storm-detail extraction.

    The National Weather Service may place storm details in different
    fields depending on the product, so all useful text is combined.
    """

    properties = get_alert_properties(alert)

    fields = [
        properties.get("event"),
        properties.get("headline"),
        properties.get("description"),
        properties.get("instruction"),
    ]

    return "\n".join(
        normalize_text(value)
        for value in fields
        if normalize_text(value)
    )


# ---------------------------------------------------------------------
# NWS API
# ---------------------------------------------------------------------

def get_active_alerts():
    """
    Retrieve all active National Weather Service alerts.

    Returns:
        list:
            GeoJSON alert feature dictionaries.
    """

    logger.info(
        "Requesting active National Weather Service alerts..."
    )

    response = requests.get(
        NWS_ALERTS_URL,
        headers=NWS_HEADERS,
        timeout=REQUEST_TIMEOUT,
    )

    response.raise_for_status()

    data = response.json()

    alerts = data.get(
        "features",
        [],
    )

    if not isinstance(alerts, list):

        logger.warning(
            "Unexpected NWS response format. "
            "'features' was not a list."
        )

        return []

    logger.info(
        "NWS returned %s active alerts.",
        len(alerts),
    )

    return alerts


# ---------------------------------------------------------------------
# TROPICAL ALERT FILTERING
# ---------------------------------------------------------------------

def is_tropical_alert(alert):
    """
    Determine whether the alert relates to a tropical cyclone.
    """

    properties = get_alert_properties(alert)

    event = normalize_text(
        properties.get("event")
    )

    if event in TROPICAL_ALERT_TYPES:
        return True

    text = get_alert_text(
        alert
    ).lower()

    tropical_terms = (
        "hurricane",
        "tropical storm",
        "tropical depression",
        "tropical cyclone",
        "storm surge",
        "subtropical storm",
        "typhoon",
    )

    return any(
        term in text
        for term in tropical_terms
    )


def is_severe_tropical_alert(alert):
    """
    Determine whether the alert belongs in the hurricane monitor.

    Explicit tropical warnings/watches are always retained.
    """

    properties = get_alert_properties(alert)

    if not is_tropical_alert(alert):
        return False

    event = normalize_text(
        properties.get("event")
    )

    severity = normalize_text(
        properties.get("severity")
    ).lower()

    if event in TROPICAL_ALERT_TYPES:
        return True

    return severity in {
        "severe",
        "extreme",
    }


def get_national_hurricane_alerts():
    """
    Retrieve active nationwide hurricane/tropical alerts.
    """

    try:

        alerts = get_active_alerts()

    except requests.RequestException as error:

        logger.error(
            "Unable to retrieve National Weather Service alerts: %s",
            error,
        )

        raise

    hurricane_alerts = [
        alert
        for alert in alerts
        if is_severe_tropical_alert(alert)
    ]

    logger.info(
        "Active tropical/hurricane alerts after filtering: %s",
        len(hurricane_alerts),
    )

    return hurricane_alerts


# ---------------------------------------------------------------------
# STORM NAME EXTRACTION
# ---------------------------------------------------------------------

def extract_storm_name(alert):
    """
    Extract a tropical cyclone name.

    Examples:

        Hurricane Gabrielle
        Tropical Storm Erin
        Tropical Depression Nine
        Subtropical Storm Alberto
        Typhoon Mawar
    """

    text = get_alert_text(
        alert
    )

    patterns = [
        r"\bMajor Hurricane\s+([A-Za-z][A-Za-z'-]+)",
        r"\bHurricane\s+([A-Za-z][A-Za-z'-]+)",
        r"\bTropical Storm\s+([A-Za-z][A-Za-z'-]+)",
        r"\bSubtropical Storm\s+([A-Za-z][A-Za-z'-]+)",
        r"\bTropical Depression\s+([A-Za-z0-9][A-Za-z0-9'-]+)",
        r"\bTyphoon\s+([A-Za-z][A-Za-z'-]+)",
    ]

    ignored_names = {
        "warning",
        "watch",
        "statement",
        "conditions",
        "force",
        "winds",
        "wind",
        "local",
    }

    for pattern in patterns:

        match = re.search(
            pattern,
            text,
            re.IGNORECASE,
        )

        if not match:
            continue

        name = match.group(1).strip()

        if name.lower() in ignored_names:
            continue

        if name.isupper():
            name = name.title()

        return name

    return None


# ---------------------------------------------------------------------
# STORM STATUS / CLASSIFICATION
# ---------------------------------------------------------------------

def extract_storm_status(alert):
    """
    Extract the current storm classification.

    Possible values include:

        Major Hurricane
        Hurricane
        Tropical Storm
        Tropical Depression
        Subtropical Storm
        Typhoon
        Tropical Cyclone

    Returns None when classification cannot be determined.
    """

    text = get_alert_text(
        alert
    )

    classifications = [
        "Major Hurricane",
        "Hurricane",
        "Typhoon",
        "Tropical Storm",
        "Subtropical Storm",
        "Tropical Depression",
        "Tropical Cyclone",
    ]

    for classification in classifications:

        if re.search(
            r"\b"
            + re.escape(classification)
            + r"\b",
            text,
            re.IGNORECASE,
        ):

            return classification

    return None


def get_storm_display_name(alert):
    """
    Return storm classification plus storm name.

    Example:

        Hurricane Gabrielle
    """

    storm_name = extract_storm_name(
        alert
    )

    storm_status = extract_storm_status(
        alert
    )

    if not storm_name:
        return None

    if storm_status:

        return (
            f"{storm_status} "
            f"{storm_name}"
        )

    return storm_name


# ---------------------------------------------------------------------
# WIND EXTRACTION
# ---------------------------------------------------------------------

def extract_max_winds(alert):
    """
    Extract maximum sustained wind speed when present.

    Returns:
        str | None

    Example:
        "115 mph"
    """

    text = get_alert_text(
        alert
    )

    patterns = [
        (
            r"maximum sustained winds?"
            r"(?:\s+are|\s+near|\s+of|\s+around)?"
            r"\s*(\d{1,3})\s*(?:mph|m\.p\.h\.)"
        ),
        (
            r"maximum winds?"
            r"(?:\s+are|\s+near|\s+of|\s+around)?"
            r"\s*(\d{1,3})\s*(?:mph|m\.p\.h\.)"
        ),
        (
            r"sustained winds?"
            r"(?:\s+are|\s+near|\s+of|\s+around)?"
            r"\s*(\d{1,3})\s*(?:mph|m\.p\.h\.)"
        ),
    ]

    for pattern in patterns:

        match = re.search(
            pattern,
            text,
            re.IGNORECASE,
        )

        if match:

            return (
                f"{match.group(1)} mph"
            )

    knot_patterns = [
        (
            r"maximum sustained winds?"
            r"(?:\s+are|\s+near|\s+of|\s+around)?"
            r"\s*(\d{1,3})\s*(?:kt|knots?)"
        ),
        (
            r"maximum winds?"
            r"(?:\s+are|\s+near|\s+of|\s+around)?"
            r"\s*(\d{1,3})\s*(?:kt|knots?)"
        ),
    ]

    for pattern in knot_patterns:

        match = re.search(
            pattern,
            text,
            re.IGNORECASE,
        )

        if match:

            knots = int(
                match.group(1)
            )

            mph = round(
                knots * 1.15078
            )

            return (
                f"{mph} mph "
                f"({knots} kt)"
            )

    return None


# ---------------------------------------------------------------------
# MOVEMENT EXTRACTION
# ---------------------------------------------------------------------

def normalize_direction(direction):
    """
    Normalize common direction values.
    """

    if not direction:
        return None

    direction = direction.upper().strip()

    direction_map = {
        "N": "N",
        "NORTH": "N",

        "NNE": "NNE",
        "NORTH-NORTHEAST": "NNE",
        "NORTH NORTHEAST": "NNE",

        "NE": "NE",
        "NORTHEAST": "NE",

        "ENE": "ENE",
        "EAST-NORTHEAST": "ENE",
        "EAST NORTHEAST": "ENE",

        "E": "E",
        "EAST": "E",

        "ESE": "ESE",
        "EAST-SOUTHEAST": "ESE",
        "EAST SOUTHEAST": "ESE",

        "SE": "SE",
        "SOUTHEAST": "SE",

        "SSE": "SSE",
        "SOUTH-SOUTHEAST": "SSE",
        "SOUTH SOUTHEAST": "SSE",

        "S": "S",
        "SOUTH": "S",

        "SSW": "SSW",
        "SOUTH-SOUTHWEST": "SSW",
        "SOUTH SOUTHWEST": "SSW",

        "SW": "SW",
        "SOUTHWEST": "SW",

        "WSW": "WSW",
        "WEST-SOUTHWEST": "WSW",
        "WEST SOUTHWEST": "WSW",

        "W": "W",
        "WEST": "W",

        "WNW": "WNW",
        "WEST-NORTHWEST": "WNW",
        "WEST NORTHWEST": "WNW",

        "NW": "NW",
        "NORTHWEST": "NW",

        "NNW": "NNW",
        "NORTH-NORTHWEST": "NNW",
        "NORTH NORTHWEST": "NNW",
    }

    return direction_map.get(
        direction,
        direction,
    )


def extract_movement(alert):
    """
    Extract storm direction and forward speed.

    Example:
        "NW at 12 mph"
    """

    text = get_alert_text(
        alert
    )

    direction_pattern = (
        r"(N|NNE|NE|ENE|E|ESE|SE|SSE|S|SSW|SW|WSW|"
        r"W|WNW|NW|NNW|"
        r"north|south|east|west|"
        r"northeast|northwest|southeast|southwest|"
        r"north-northeast|north-northwest|"
        r"south-southeast|south-southwest|"
        r"east-northeast|east-southeast|"
        r"west-northwest|west-southwest)"
    )

    patterns = [
        (
            r"moving"
            r"(?:\s+toward|\s+to|\s+generally)?"
            r"(?:\s+the)?\s+"
            + direction_pattern
            + r"\s+(?:at|near)\s+"
            r"(\d{1,3})\s*(mph|kt|knots?)"
        ),
        (
            r"movement[:\s]+"
            + direction_pattern
            + r"\s+(?:at|near)\s+"
            r"(\d{1,3})\s*(mph|kt|knots?)"
        ),
    ]

    for pattern in patterns:

        match = re.search(
            pattern,
            text,
            re.IGNORECASE,
        )

        if not match:
            continue

        direction = normalize_direction(
            match.group(1)
        )

        speed = int(
            match.group(2)
        )

        unit = match.group(3).lower()

        if unit in {
            "kt",
            "knot",
            "knots",
        }:

            mph = round(
                speed * 1.15078
            )

            return (
                f"{direction} at "
                f"{mph} mph "
                f"({speed} kt)"
            )

        return (
            f"{direction} at "
            f"{speed} mph"
        )

    return None


# ---------------------------------------------------------------------
# PRESSURE EXTRACTION
# ---------------------------------------------------------------------

def extract_pressure(alert):
    """
    Extract minimum central pressure.

    Example:
        "960 mb"
    """

    text = get_alert_text(
        alert
    )

    patterns = [
        (
            r"minimum central pressure"
            r"(?:\s+is|\s+near|\s+of|\s*:)?"
            r"\s*(\d{3,4})\s*(?:mb|millibars?)"
        ),
        (
            r"central pressure"
            r"(?:\s+is|\s+near|\s+of|\s*:)?"
            r"\s*(\d{3,4})\s*(?:mb|millibars?)"
        ),
        (
            r"minimum pressure"
            r"(?:\s+is|\s+near|\s+of|\s*:)?"
            r"\s*(\d{3,4})\s*(?:mb|millibars?)"
        ),
    ]

    for pattern in patterns:

        match = re.search(
            pattern,
            text,
            re.IGNORECASE,
        )

        if match:

            return (
                f"{match.group(1)} mb"
            )

    return None


# ---------------------------------------------------------------------
# OPTIONAL CATEGORY EXTRACTION
# ---------------------------------------------------------------------

def extract_hurricane_category(alert):
    """
    Extract Saffir-Simpson category when explicitly stated.

    Returns examples such as:
        "Category 1"
        "Category 4"
    """

    text = get_alert_text(
        alert
    )

    patterns = [
        r"\bCategory\s+([1-5])\b",
        r"\bCategory\s+([1-5])\s+Hurricane\b",
    ]

    for pattern in patterns:

        match = re.search(
            pattern,
            text,
            re.IGNORECASE,
        )

        if match:

            return (
                f"Category {match.group(1)}"
            )

    return None


# ---------------------------------------------------------------------
# AFFECTED STATES
# ---------------------------------------------------------------------

def extract_states_from_area_description(area_desc):
    """
    Determine affected states from areaDesc text.
    """

    states = set()

    if not area_desc:
        return states

    area_desc = normalize_text(
        area_desc
    )

    for abbreviation, state_name in STATE_ABBREVIATIONS.items():

        pattern = (
            r"(?<![A-Za-z])"
            + re.escape(abbreviation)
            + r"(?![A-Za-z])"
        )

        if re.search(
            pattern,
            area_desc,
        ):

            states.add(
                state_name
            )

    lower_area = area_desc.lower()

    for state_name in STATE_ABBREVIATIONS.values():

        if state_name.lower() in lower_area:

            states.add(
                state_name
            )

    return states


def extract_states_from_same_codes(alert):
    """
    Extract affected states from SAME/FIPS codes.
    """

    properties = get_alert_properties(
        alert
    )

    geocode = properties.get(
        "geocode",
        {},
    ) or {}

    same_codes = geocode.get(
        "SAME",
        [],
    ) or []

    states = set()

    for code in same_codes:

        code = str(
            code
        ).strip()

        if len(code) >= 5:

            if len(code) == 6:

                state_fips = (
                    code[1:3]
                )

            else:

                state_fips = (
                    code[:2]
                )

            state_name = (
                STATE_FIPS.get(
                    state_fips
                )
            )

            if state_name:

                states.add(
                    state_name
                )

    return states


def extract_states_from_ugc_codes(alert):
    """
    Extract affected states from NWS UGC zone codes.

    Example:
        FLZ063 -> Florida
        GAZ001 -> Georgia
    """

    properties = get_alert_properties(
        alert
    )

    geocode = properties.get(
        "geocode",
        {},
    ) or {}

    ugc_codes = geocode.get(
        "UGC",
        [],
    ) or []

    states = set()

    for code in ugc_codes:

        code = normalize_text(
            code
        ).upper()

        if len(code) < 2:
            continue

        abbreviation = (
            code[:2]
        )

        state_name = (
            STATE_ABBREVIATIONS.get(
                abbreviation
            )
        )

        if state_name:

            states.add(
                state_name
            )

    return states


def extract_affected_states(alert):
    """
    Return a sorted list of all affected states/territories.
    """

    properties = get_alert_properties(
        alert
    )

    states = set()

    area_desc = normalize_text(
        properties.get("areaDesc")
    )

    states.update(
        extract_states_from_area_description(
            area_desc
        )
    )

    states.update(
        extract_states_from_ugc_codes(
            alert
        )
    )

    states.update(
        extract_states_from_same_codes(
            alert
        )
    )

    return sorted(
        states
    )


# ---------------------------------------------------------------------
# DETAILED AREAS FOR MAPS
# ---------------------------------------------------------------------

def get_original_affected_areas(alert):
    """
    Keep county/zone detail internally for map generation.

    These values are not intended to clutter the email summary.
    """

    properties = get_alert_properties(
        alert
    )

    affected_areas = properties.get(
        "affectedAreas"
    )

    if isinstance(
        affected_areas,
        list,
    ):

        return sorted(
            {
                normalize_text(area)
                for area in affected_areas
                if normalize_text(area)
            }
        )

    area_desc = normalize_text(
        properties.get("areaDesc")
    )

    if not area_desc:
        return []

    areas = [
        normalize_text(area)
        for area in area_desc.split(";")
        if normalize_text(area)
    ]

    return sorted(
        set(areas)
    )


# ---------------------------------------------------------------------
# ALERT SUMMARY
# ---------------------------------------------------------------------

def summarize_alert(alert):
    """
    Convert an NWS alert into the condensed format used by emailer.py.

    The returned dictionary includes:

        storm name
        storm status
        hurricane category when explicitly available
        maximum winds
        movement
        pressure
        affected states
        severity
        timing
        NWS headline
        detailed areas for maps
    """

    properties = get_alert_properties(
        alert
    )

    event = normalize_text(
        properties.get("event")
    )

    severity = normalize_text(
        properties.get("severity")
    )

    urgency = normalize_text(
        properties.get("urgency")
    )

    certainty = normalize_text(
        properties.get("certainty")
    )

    headline = normalize_text(
        properties.get("headline")
    )

    description = normalize_text(
        properties.get("description")
    )

    instruction = normalize_text(
        properties.get("instruction")
    )

    effective = normalize_text(
        properties.get("effective")
    )

    onset = normalize_text(
        properties.get("onset")
    )

    expires = normalize_text(
        properties.get("expires")
    )

    ends = normalize_text(
        properties.get("ends")
    )

    sender_name = normalize_text(
        properties.get("senderName")
    )

    response = normalize_text(
        properties.get("response")
    )

    message_type = normalize_text(
        properties.get("messageType")
    )

    # -------------------------------------------------------------
    # STORM DETAILS
    # -------------------------------------------------------------

    storm_name = extract_storm_name(
        alert
    )

    storm_status = extract_storm_status(
        alert
    )

    storm_display_name = get_storm_display_name(
        alert
    )

    hurricane_category = (
        extract_hurricane_category(
            alert
        )
    )

    max_winds = extract_max_winds(
        alert
    )

    movement = extract_movement(
        alert
    )

    pressure = extract_pressure(
        alert
    )

    # -------------------------------------------------------------
    # LOCATION DETAILS
    # -------------------------------------------------------------

    affected_states = extract_affected_states(
        alert
    )

    detailed_areas = get_original_affected_areas(
        alert
    )

    if affected_states:

        affected_area = ", ".join(
            affected_states
        )

    else:

        affected_area = normalize_text(
            properties.get("areaDesc")
        )

        if not affected_area:

            affected_area = (
                "Affected area unavailable"
            )

    # -------------------------------------------------------------
    # TITLE
    # -------------------------------------------------------------

    if storm_display_name:

        title = (
            f"{event} — {storm_display_name}"
            if event
            else storm_display_name
        )

    elif storm_name:

        title = (
            f"{event} — {storm_name}"
            if event
            else storm_name
        )

    else:

        title = (
            event
            or "Weather Alert"
        )

    # -------------------------------------------------------------
    # RETURN EMAIL/MAP SUMMARY
    # -------------------------------------------------------------

    return {
        # Primary title
        "title": title,

        # Alert type
        "event": (
            event
            or "Weather Alert"
        ),

        # Storm identity
        "storm_name": storm_name,

        "storm_status": storm_status,

        "storm_display_name": (
            storm_display_name
        ),

        "hurricane_category": (
            hurricane_category
        ),

        # Storm facts
        "max_winds": max_winds,

        "movement": movement,

        "pressure": pressure,

        # Geographic information
        "affected_states": (
            affected_states
        ),

        "affected_area": (
            affected_area
        ),

        "affected_state_count": len(
            affected_states
        ),

        # Detailed county/zone information remains available
        # internally for map generation.
        "detailed_areas": (
            detailed_areas
        ),

        "affected_area_count": len(
            detailed_areas
        ),

        # Alert characteristics
        "severity": (
            severity
            or "Unknown"
        ),

        "urgency": (
            urgency
            or "Unknown"
        ),

        "certainty": (
            certainty
            or "Unknown"
        ),

        # NWS text
        "headline": headline,

        "description": description,

        "instruction": instruction,

        # Timing
        "effective": effective,

        "onset": onset,

        "expires": expires,

        "ends": ends,

        # Additional NWS metadata
        "sender_name": sender_name,

        "response": response,

        "message_type": (
            message_type
        ),

        # Tracking
        "id": alert.get(
            "id"
        ),

        "source_alert_ids": alert.get(
            "_source_alert_ids",
            [],
        ),
    }
