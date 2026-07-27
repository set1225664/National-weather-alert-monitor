# National Severe Weather Alert System 🌩️

An automated weather monitoring service that tracks **major severe weather events across the United States** and sends **email alerts with forecast maps, storm tracking imagery, and emergency details**.

The system is designed for users who want nationwide awareness of dangerous weather conditions without monitoring multiple weather websites or apps.

---

## Features

✅ Nationwide severe weather monitoring  
✅ Email notifications for major weather events  
✅ NOAA/NWS data integration  
✅ Hurricane and tropical storm tracking  
✅ Severe thunderstorm alerts  
✅ Tornado warnings  
✅ Flood warnings  
✅ Winter storm alerts  
✅ Extreme heat alerts  
✅ Wildfire alerts  
✅ Weather prediction maps included in emails  
✅ Automated scheduled monitoring  
✅ Duplicate alert prevention  
✅ Lightweight deployment

---

# How It Works

The system continuously monitors official weather data sources:

When a major weather event meets configured severity thresholds:

1. Weather data is collected
2. Event severity is evaluated
3. Relevant maps are generated
4. Email alert is created
5. Notification is sent

---

# Supported Alerts

## Severe Storms

- Tornado warnings
- Severe thunderstorm warnings
- Damaging wind events
- Large hail events

## Tropical Weather

- Tropical depressions
- Tropical storms
- Hurricanes
- Hurricane watches
- Hurricane warnings

## Flooding

- Flash flood warnings
- River flooding
- Coastal flooding

## Winter Weather

- Blizzard warnings
- Ice storms
- Heavy snow events
- Extreme cold

## Other Hazards

- Extreme heat
- Wildfires
- Dust storms
- High wind events

---

# Email Alert Example

Each alert contains:

---

# Weather Data Sources

This project uses publicly available government weather information.

Primary sources:

- NOAA Weather API
- National Weather Service Alerts API
- National Hurricane Center
- National Weather Radar Data

---

# Project Structure

---

# Installation

## Requirements

- Python 3.11+
- SMTP Email Account
- NOAA API Access

---

## Clone Repository

```bash
git clone https://github.com/YOUR_USERNAME/weather-alert-system.git

cd weather-alert-system

pip install -r requirements.txt

cp .env.example .env

EMAIL_ADDRESS=shipping@boatfix.com
EMAIL_PASSWORD=Pequot376!

SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587

ALERT_EMAIL=ops@boatfix.com
