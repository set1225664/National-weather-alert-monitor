"""Send one clearly labeled sample tropical-weather email; no NWS calls or history changes.

Run: python test_email.py
Optional: python test_email.py --map maps/example.png
"""
import argparse
import logging
from datetime import datetime, timedelta, timezone

from emailer import send_weather_alert


def main():
    parser = argparse.ArgumentParser(description="Send a test hurricane alert email")
    parser.add_argument("--map", default=None, help="Optional existing PNG map to embed")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    now = datetime.now(timezone.utc)
    sample = {
        "title": "TEST ONLY — Hurricane Example (NOT A REAL STORM)",
        "event": "TEST — Hurricane Warning",
        "storm_name": "Example",
        "storm_display_name": "TEST ONLY — Hurricane Example (NOT A REAL STORM)",
        "storm_status": "Hurricane (simulated)",
        "hurricane_category": "Category 2 (simulated)",
        "max_winds": "105 mph (simulated)",
        "movement": "NW at 12 mph (simulated)",
        "pressure": "970 mb (simulated)",
        "affected_states": ["Florida", "Georgia"],
        "affected_area": "Florida, Georgia (sample only)",
        "severity": "Severe (simulated)",
        "urgency": "Immediate (simulated)",
        "headline": "TEST MESSAGE — No actual storm or weather warning is being reported.",
        "description": "Sample impacts: strong winds, heavy rain, coastal flooding. TEST ONLY.",
        "impacts": ["Strong winds (simulated)", "Heavy rainfall (simulated)", "Coastal flooding (simulated)"],
        "effective": now.isoformat(),
        "expires": (now + timedelta(hours=24)).isoformat(),
        "ends": (now + timedelta(hours=24)).isoformat(),
    }
    ok = send_weather_alert([sample], args.map)
    if not ok:
        raise SystemExit("Test email failed. Review SMTP settings and the log above.")
    print("Test email accepted by SMTP. Check the recipient inbox and spam folder.")


if __name__ == "__main__":
    main()
