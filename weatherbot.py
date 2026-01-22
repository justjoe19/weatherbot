"""
WeatherBot - Twitter Weather & Alert Notifier

This bot posts weather updates and severe weather alerts for a specific location
(South Bend, Indiana by default) to Twitter using the NWS API.

Environment Variables Required:
- CITY: Name of the city for tweet formatting.
- LAT, LON: Latitude and longitude coordinates.
- TWITTER_API_KEY, TWITTER_API_SECRET
- TWITTER_ACCESS_TOKEN, TWITTER_ACCESS_TOKEN_SECRET

Schedule:
- Tweets weather forecast 6 times daily.
- Checks for severe alerts every 5 minutes.
"""

import os
import time
import json
import pytz
import requests
from datetime import datetime, timedelta
from dotenv import load_dotenv
from apscheduler.schedulers.blocking import BlockingScheduler
from requests_oauthlib import OAuth1

# === Load environment variables ===
load_dotenv()

# === Configuration ===
CITY = os.getenv("CITY", "South Bend, Indiana")
LAT = os.getenv("LAT", "41.6764")
LON = os.getenv("LON", "-86.2520")
TZ = pytz.timezone("America/Indiana/Indianapolis")

TWITTER_API_KEY = os.getenv("TWITTER_API_KEY")
TWITTER_API_SECRET = os.getenv("TWITTER_API_SECRET")
TWITTER_ACCESS_TOKEN = os.getenv("TWITTER_ACCESS_TOKEN")
TWITTER_ACCESS_TOKEN_SECRET = os.getenv("TWITTER_ACCESS_TOKEN_SECRET")

ALERT_TRACK_FILE = "last_alert.txt"

# === Twitter OAuth Setup ===
auth = OAuth1(
    TWITTER_API_KEY,
    TWITTER_API_SECRET,
    TWITTER_ACCESS_TOKEN,
    TWITTER_ACCESS_TOKEN_SECRET,
)

# === Logging Utility ===
def log(msg):
    print(f"[{datetime.now()}] {msg}")

# === HTTP JSON Fetch with Error Handling ===
def fetch_json(url):
    try:
        r = requests.get(url, headers={"User-Agent": "weatherbot"}, timeout=10)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        log(f"ERROR: Failed to fetch {url}: {e}")
        return None

# === Post Tweet ===
def post_tweet(text):
    url = "https://api.twitter.com/2/tweets"
    payload = {"text": text}
    try:
        res = requests.post(url, auth=auth, json=payload)
        res.raise_for_status()
        log(f"Tweeted: {text}")
    except Exception as e:
        log(f"ERROR posting tweet: {e}")

# === Current Weather Report ===
def get_current_conditions():
    points = fetch_json(f"https://api.weather.gov/points/{LAT},{LON}")
    if not points:
        return "Weather unavailable."

    station_url = points["properties"]["observationStations"]
    stations = fetch_json(station_url)
    if not stations:
        return "Weather unavailable."

    station_id = stations["features"][0]["properties"]["stationIdentifier"]
    obs = fetch_json(f"https://api.weather.gov/stations/{station_id}/observations/latest")
    if not obs:
        return "Weather unavailable."

    temp_c = obs["properties"]["temperature"]["value"]
    desc = obs["properties"]["textDescription"]
    if temp_c is not None:
        temp_f = round(temp_c * 9 / 5 + 32)
        return f"Current in {CITY}: {temp_f}°F, {desc}"
    return f"Current in {CITY}: {desc}"

# === Hourly Forecast Summary ===
def get_hourly_forecast():
    points = fetch_json(f"https://api.weather.gov/points/{LAT},{LON}")
    if not points:
        return "Forecast unavailable."

    hourly_url = points["properties"]["forecastHourly"]
    forecast = fetch_json(hourly_url)
    if not forecast:
        return "Forecast unavailable."

    now = datetime.now(TZ)
    next_hour = (now + timedelta(hours=1)).replace(minute=0, second=0, microsecond=0)

    summary = []
    count = 0
    for period in forecast["properties"]["periods"]:
        t = datetime.fromisoformat(period["startTime"]).astimezone(TZ)
        if t >= next_hour:
            time_str = t.strftime("%I %p").lstrip("0")
            summary.append(f"{time_str}: {period['temperature']}°F, {period['shortForecast']}")
            count += 1
        if count == 4:
            break

    return "\n".join(summary)

# === Alert File IO ===
def load_last_alert():
    if os.path.exists(ALERT_TRACK_FILE):
        with open(ALERT_TRACK_FILE) as f:
            return f.read().strip()
    return ""

def save_last_alert(event):
    with open(ALERT_TRACK_FILE, "w") as f:
        f.write(event)

# === Severe Weather Alerts ===
def check_alerts():
    url = f"https://api.weather.gov/alerts/active?point={LAT},{LON}"
    data = fetch_json(url)
    if not data or not data.get("features"):
        log("No alerts.")
        return

    last_sent = load_last_alert()

    for alert in data["features"]:
        event = alert["properties"]["event"]
        if event == last_sent:
            return

        description = alert["properties"].get("description", "")
        hashtags = "#WeatherAlert #SouthBend"
        tweet = f"⚠️ {event} ⚠️\n\n{description[:240]}...\n\n{hashtags}"
        post_tweet(tweet)
        save_last_alert(event)
        return

# === Weather Tweet Job ===
def tweet_forecast():
    current = get_current_conditions()
    forecast = get_hourly_forecast()
    hashtags = "#SouthBend #Indiana #Weather"
    post_tweet(f"{current}\n\n{forecast}\n\n{hashtags}")

# === Scheduler Configuration ===
scheduler = BlockingScheduler(timezone=TZ)
scheduler.add_job(tweet_forecast, "cron", hour="3,7,12,17,22")
scheduler.add_job(check_alerts, "interval", minutes=5)

if __name__ == "__main__":
    log("✅ Weatherbot started")
    # tweet_forecast() # Don't tweet immediately on startup to avoid spam if restarting frequently
    check_alerts()
    scheduler.start()