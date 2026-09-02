"""
National Weather Service API Client.

Retrieves active tropical weather alerts from the National Weather
Service and converts them into a condensed format for email
notifications.

Features:

1. Retrieves active nationwide NWS alerts
2. Filters hurricane and tropical-system alerts
3. Keeps severe / extreme alerts
4. Extracts named hurricanes and tropical storms
5. Converts affected counties/zones into affected states
6. Preserves detailed alert data for maps and history tracking
7. Creates condensed alert summaries for email notifications
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
    "Accept": "application/geo+json"
}

REQUEST_TIMEOUT = 30


# ---------------------------------------------------------------------
# ALERT TYPES
# ---------------------------------------------------------------------

# Tropical-system alerts that should be included by the hurricane
# monitoring system.
#
# Keeping these separate allows Hurricane Warning, Storm Surge Warning,
# Tropical Storm Warning, etc. to appear as separate consolidated
# notices while still grouping all affected locations within each type.

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
    "Typhoon Watch"
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

    # U.S. territories commonly affected by tropical systems
    "PR": "Puerto Rico",
    "VI": "U.S. Virgin Islands",
    "GU": "Guam",
    "AS": "American Samoa",
    "MP": "Northern Mariana Islands"
}


# State FIPS codes.
#
# NWS SAME/geocode values can be used as a fallback when the normal
# affected-area text does not explicitly contain state abbreviations.

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
    "78": "U.S. Virgin Islands"
}


# ---------------------------------------------------------------------
# BASIC ALERT HELPERS
# ---------------------------------------------------------------------

def get_alert_properties(alert):
    """
    Return the NWS properties dictionary from an alert.

    Supports both the standard GeoJSON alert format and dictionaries
    that have already been reduced to their properties.
    """

    if not isinstance(alert, dict):
        return {}

    properties = alert.get("properties")

    if isinstance(properties, dict):
        return properties

    return alert


def normalize_text(value):
    """
    Safely normalize an API text value.
    """

    if value is None:
        return ""

    return str(value).strip()


# ---------------------------------------------------------------------
# NWS API
# ---------------------------------------------------------------------

def get_active_alerts():
    """
    Retrieve all currently active alerts from the National Weather
    Service.

    Returns:
        list:
            List of GeoJSON alert feature dictionaries.

    Raises:
        requests.RequestException:
            If the National Weather Service request fails.
    """

    logger.info(
        "Requesting active National Weather Service alerts..."
    )

    response = requests.get(
        NWS_ALERTS_URL,
        headers=NWS_HEADERS,
        timeout=REQUEST_TIMEOUT
    )

    response.raise_for_status()

    data = response.json()

    alerts = data.get(
        "features",
        []
    )

    if not isinstance(alerts, list):
        logger.warning(
            "Unexpected NWS response format. "
            "'features' was not a list."
        )

        return []

    logger.info(
        "NWS returned %s active alerts.",
        len(alerts)
    )

    return alerts


# ---------------------------------------------------------------------
# TROPICAL ALERT FILTERING
# ---------------------------------------------------------------------

def is_tropical_alert(alert):
    """
    Determine whether an alert is associated with a hurricane,
    tropical storm, storm surge, typhoon, or related tropical cyclone.

    The event type is checked first. Headline and description are used
    as a fallback because NWS products can occasionally vary.
    """

    properties = get_alert_properties(
        alert
    )

    event = normalize_text(
        properties.get("event")
    )

    if event in TROPICAL_ALERT_TYPES:
        return True

    text = " ".join([
        event,
        normalize_text(
            properties.get("headline")
        ),
        normalize_text(
            properties.get("description")
        )
    ]).lower()

    tropical_terms = (
        "hurricane",
        "tropical storm",
        "tropical cyclone",
        "storm surge",
        "typhoon"
    )

    return any(
        term in text
        for term in tropical_terms
    )


def is_severe_tropical_alert(alert):
    """
    Determine whether an alert should trigger the hurricane monitoring
    system.

    Warnings and watches are retained regardless of whether NWS marks
    them Moderate, Severe, or Extreme because some important tropical
    products do not always carry identical severity metadata.
    """

    properties = get_alert_properties(
        alert
    )

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
        "extreme"
    }


def get_national_hurricane_alerts():
    """
    Retrieve active nationwide tropical-system alerts.

    This is the primary function used by main.py.

    Returns:
        list:
            Active alerts associated with hurricanes, tropical storms,
            storm surge, typhoons, and related tropical cyclone hazards.
    """

    try:

        alerts = get_active_alerts()

    except requests.RequestException as error:

        logger.error(
            "Unable to retrieve National Weather Service alerts: %s",
            error
        )

        raise

    hurricane_alerts = [
        alert
        for alert in alerts
        if is_severe_tropical_alert(alert)
    ]

    logger.info(
        "Active tropical/hurricane alerts after filtering: %s",
        len(hurricane_alerts)
    )

    return hurricane_alerts


# ---------------------------------------------------------------------
# STORM NAME EXTRACTION
# ---------------------------------------------------------------------

def extract_storm_name(alert):
    """
    Extract the name of a hurricane or tropical storm.

    Examples that can be detected:

        Hurricane Gabrielle
        Tropical Storm Erin
        Tropical Depression Nine
        Subtropical Storm Alberto
        Typhoon Mawar

    Returns:
        str | None:
            Storm name if detected, otherwise None.
    """

    properties = get_alert_properties(
        alert
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

    event = normalize_text(
        properties.get("event")
    )

    text = " ".join([
        headline,
        description,
        instruction,
        event
    ])

    # More specific patterns should be checked first.
    patterns = [
        r"\bMajor Hurricane\s+([A-Za-z][A-Za-z'-]+)",
        r"\bHurricane\s+([A-Za-z][A-Za-z'-]+)",
        r"\bTropical Storm\s+([A-Za-z][A-Za-z'-]+)",
        r"\bSubtropical Storm\s+([A-Za-z][A-Za-z'-]+)",
        r"\bTropical Depression\s+([A-Za-z0-9][A-Za-z0-9'-]+)",
        r"\bTyphoon\s+([A-Za-z][A-Za-z'-]+)"
    ]

    ignored_names = {
        "warning",
        "watch",
        "statement",
        "conditions",
        "force",
        "winds",
        "wind",
        "local"
    }

    for pattern in patterns:

        match = re.search(
            pattern,
            text,
            re.IGNORECASE
        )

        if not match:
            continue

        name = match.group(1).strip()

        if name.lower() in ignored_names:
            continue

        # If the name is all-uppercase from an NWS bulletin,
        # convert it into normal title capitalization.
        if name.isupper():
            name = name.title()

        return name

    return None


def get_storm_display_name(alert):
    """
    Return the storm name with its classification where possible.

    Example:
        Hurricane Gabrielle
        Tropical Storm Erin

    Returns None when no named system can be identified.
    """

    properties = get_alert_properties(
        alert
    )

    storm_name = extract_storm_name(
        alert
    )

    if not storm_name:
        return None

    text = " ".join([
        normalize_text(
            properties.get("headline")
        ),
        normalize_text(
            properties.get("description")
        )
    ])

    classifications = [
        "Major Hurricane",
        "Hurricane",
        "Tropical Storm",
        "Subtropical Storm",
        "Tropical Depression",
        "Typhoon"
    ]

    for classification in classifications:

        pattern = (
            r"\b"
            + re.escape(classification)
            + r"\s+"
            + re.escape(storm_name)
            + r"\b"
        )

        if re.search(
            pattern,
            text,
            re.IGNORECASE
        ):
            return (
                f"{classification} "
                f"{storm_name}"
            )

    return storm_name


# ---------------------------------------------------------------------
# AFFECTED STATE EXTRACTION
# ---------------------------------------------------------------------

def extract_states_from_area_description(area_desc):
    """
    Attempt to determine affected states from the NWS areaDesc field.

    Supports formats such as:

        Miami-Dade; Broward; Palm Beach
        Miami-Dade County, FL
        Coastal Miami Dade County, Florida
        South Carolina Coast

    Returns:
        set[str]
    """

    states = set()

    if not area_desc:
        return states

    area_desc = normalize_text(
        area_desc
    )

    # -------------------------------------------------------------
    # STATE ABBREVIATIONS
    # -------------------------------------------------------------

    # Match abbreviations when they appear as separate tokens.
    #
    # Examples:
    #   Miami-Dade County, FL
    #   Coastal Waters, FL

    for abbreviation, state_name in STATE_ABBREVIATIONS.items():

        pattern = (
            r"(?<![A-Za-z])"
            + re.escape(abbreviation)
            + r"(?![A-Za-z])"
        )

        if re.search(
            pattern,
            area_desc
        ):
            states.add(
                state_name
            )

    # -------------------------------------------------------------
    # FULL STATE NAMES
    # -------------------------------------------------------------

    lower_area = area_desc.lower()

    for state_name in STATE_ABBREVIATIONS.values():

        if state_name.lower() in lower_area:

            states.add(
                state_name
            )

    return states


def extract_states_from_same_codes(alert):
    """
    Extract states using NWS SAME/FIPS geocode information.

    SAME codes generally contain a subdivision digit followed by the
    two-digit state FIPS code and three-digit county code.

    Example:

        012086

    The state portion is:

        12 -> Florida
    """

    properties = get_alert_properties(
        alert
    )

    geocode = properties.get(
        "geocode",
        {}
    ) or {}

    same_codes = geocode.get(
        "SAME",
        []
    ) or []

    states = set()

    for code in same_codes:

        code = str(
            code
        ).strip()

        # SAME codes are normally six digits:
        #
        # PSSCCC
        #
        # P   = subdivision
        # SS  = state FIPS
        # CCC = county
        if len(code) >= 5:

            if len(code) == 6:
                state_fips = code[1:3]

            else:
                # Defensive fallback for five-digit FIPS-style values.
                state_fips = code[:2]

            state_name = STATE_FIPS.get(
                state_fips
            )

            if state_name:
                states.add(
                    state_name
                )

    return states


def extract_states_from_ugc_codes(alert):
    """
    Extract state abbreviations from NWS UGC zone codes when available.

    Examples:

        FLZ063
        GAZ001
        SCZ050

    The first two characters identify the state or territory.
    """

    properties = get_alert_properties(
        alert
    )

    geocode = properties.get(
        "geocode",
        {}
    ) or {}

    ugc_codes = geocode.get(
        "UGC",
        []
    ) or []

    states = set()

    for code in ugc_codes:

        code = normalize_text(
            code
        ).upper()

        if len(code) < 2:
            continue

        abbreviation = code[:2]

        state_name = STATE_ABBREVIATIONS.get(
            abbreviation
        )

        if state_name:
            states.add(
                state_name
            )

    return states


def extract_affected_states(alert):
    """
    Determine all states affected by an alert.

    Several NWS fields are examined because the format can vary
    depending on the alert-producing office.

    Priority sources:

        1. areaDesc
        2. UGC geocodes
        3. SAME/FIPS codes

    Returns:
        list[str]:
            Sorted, deduplicated state names.
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
# CONSOLIDATED ALERT SUPPORT
# ---------------------------------------------------------------------

def get_original_affected_areas(alert):
    """
    Return the detailed NWS affected areas.

    These are kept internally for maps/debugging even though email
    notifications primarily display state names.
    """

    properties = get_alert_properties(
        alert
    )

    affected_areas = properties.get(
        "affectedAreas"
    )

    if isinstance(affected_areas, list):

        return sorted(
            set(
                normalize_text(area)
                for area in affected_areas
                if normalize_text(area)
            )
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
# EMAIL SUMMARY
# ---------------------------------------------------------------------

def summarize_alert(alert):
    """
    Convert an NWS alert into the condensed dictionary used by
    emailer.py.

    The email-facing summary emphasizes:

        - Alert type
        - Named storm
        - Affected states
        - Severity
        - Timing
        - NWS headline
        - NWS description
        - Instructions

    County/zone data is preserved as detailed_areas for maps,
    diagnostics, or future email enhancements.
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

    storm_name = extract_storm_name(
        alert
    )

    storm_display_name = get_storm_display_name(
        alert
    )

    affected_states = extract_affected_states(
        alert
    )

    detailed_areas = get_original_affected_areas(
        alert
    )

    # This is the primary location string intended for email display.
    if affected_states:

        affected_area = ", ".join(
            affected_states
        )

    else:

        # Fallback only when a state cannot be derived.
        affected_area = normalize_text(
            properties.get("areaDesc")
        )

        if not affected_area:
            affected_area = "Affected area unavailable"

    # Build a concise display title.
    #
    # Example:
    #   Hurricane Warning — Hurricane Gabrielle
    #
    # If only the storm's name is known:
    #   Hurricane Warning — Gabrielle

    if storm_display_name:

        # Avoid awkward duplication such as:
        #
        # Hurricane Warning — Hurricane Hurricane Gabrielle
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

    summary = {
        # ---------------------------------------------------------
        # EMAIL DISPLAY FIELDS
        # ---------------------------------------------------------

        "title": title,

        "event": (
            event
            or "Weather Alert"
        ),

        "storm_name": storm_name,

        "storm_display_name": storm_display_name,

        "affected_states": affected_states,

        "affected_area": affected_area,

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

        "headline": headline,

        "description": description,

        "instruction": instruction,

        "effective": effective,

        "onset": onset,

        "expires": expires,

        "ends": ends,

        # ---------------------------------------------------------
        # ADDITIONAL NWS INFORMATION
        # ---------------------------------------------------------

        "sender_name": sender_name,

        "response": response,

        "message_type": message_type,

        # Keep county/zone detail internally.
        "detailed_areas": detailed_areas,

        # Number of states affected.
        "affected_state_count": len(
            affected_states
        ),

        # Number of underlying zones/counties in the consolidated
        # notice.
        "affected_area_count": len(
            detailed_areas
        ),

        # ---------------------------------------------------------
        # TRACKING INFORMATION
        # ---------------------------------------------------------

        "id": alert.get(
            "id"
        ),

        "source_alert_ids": alert.get(
            "_source_alert_ids",
            []
        )
    }

    return summary
