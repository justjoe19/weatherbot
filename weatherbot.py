import os
import requests
import tweepy
import time
import argparse
from datetime import datetime
from dotenv import load_dotenv
from apscheduler.schedulers.background import BackgroundScheduler

print("\n🚀 NWS Weatherbot is starting up...")

# === Load environment variables from .env ===
load_dotenv()

# === Twitter API credentials ===
TWITTER_BEARER_TOKEN = os.getenv("TWITTER_BEARER_TOKEN")
TWITTER_API_KEY = os.getenv("TWITTER_API_KEY")
TWITTER_API_SECRET = os.getenv("TWITTER_API_SECRET")
TWITTER_ACCESS_TOKEN = os.getenv("TWITTER_ACCESS_TOKEN")
TWITTER_ACCESS_TOKEN_SECRET = os.getenv("TWITTER_ACCESS_TOKEN_SECRET")

assert TWITTER_API_KEY and TWITTER_API_SECRET, "Twitter API credentials missing!"

# Use v1.1 for basic tweet posting (no Elevated access required)
auth = tweepy.OAuth1UserHandler(
    TWITTER_API_KEY, TWITTER_API_SECRET,
    TWITTER_ACCESS_TOKEN, TWITTER_ACCESS_TOKEN_SECRET
)
twitter_api = tweepy.API(auth)

# ---- NWS API URLs ----
POINT_URL = "https://api.weather.gov/points/41.6764,-86.2520"  # South Bend, IN
FORECAST_HOURLY_URL = ""
OBSERVATION_URL = ""
ALERTS_URL = "https://api.weather.gov/alerts/active?point=41.6764,-86.2520"

HEADERS = {"User-Agent": "nws-weatherbot"}

# Track posted alert IDs
posted_alerts = set()

# Global dry-run flag
DRY_RUN = False

def initialize_nws_urls():
    global FORECAST_HOURLY_URL, OBSERVATION_URL
    response = requests.get(POINT_URL, headers=HEADERS)
    response.raise_for_status()
    properties = response.json()["properties"]
    FORECAST_HOURLY_URL = properties["forecastHourly"]
    OBSERVATION_URL = properties["observationStations"]

def fetch_current_weather():
    stations_resp = requests.get(OBSERVATION_URL, headers=HEADERS)
    stations_resp.raise_for_status()
    first_station_url = stations_resp.json()["features"][0]["id"] + "/observations/latest"

    obs_resp = requests.get(first_station_url, headers=HEADERS)
    obs_resp.raise_for_status()
    obs = obs_resp.json()["properties"]

    temperature_c = obs["temperature"]["value"]
    temp_f = round((temperature_c * 9/5) + 32) if temperature_c else "N/A"
    condition = obs.get("textDescription", "N/A")

    return f"{temp_f}°F | {condition}"

def fetch_hourly_forecast():
    response = requests.get(FORECAST_HOURLY_URL, headers=HEADERS)
    response.raise_for_status()
    periods = response.json()["properties"]["periods"][:4]  # Limit to next 4 hours

    def format_time(iso_time):
        dt = datetime.fromisoformat(iso_time.replace("Z", "+00:00"))
        return dt.strftime("%-I:%M%p").lower()

    forecast_lines = []
    for p in periods:
        desc = p['shortForecast']
        if len(desc) > 30:
            desc = desc[:27] + "..."
        forecast_lines.append(
            f"{format_time(p['startTime'])}: {p['temperature']}°{p['temperatureUnit']} {desc}"
        )
    return "\n".join(forecast_lines)

def fetch_severe_alerts():
    response = requests.get(ALERTS_URL, headers=HEADERS)
    response.raise_for_status()
    alerts = response.json()

    new_alerts = []
    for feature in alerts["features"]:
        alert_id = feature["id"]
        if alert_id not in posted_alerts:
            posted_alerts.add(alert_id)
            title = feature["properties"]["headline"]
            description = feature["properties"]["description"]
            new_alerts.append((title, description))
    return new_alerts

def safe_tweet_post(message):
    if len(message) > 280:
        message = message[:276] + "..."
    if DRY_RUN:
        print("📜 [DRY-RUN] Would tweet:", message)
        return
    try:
        twitter_api.update_status(status=message)
        print("✅ Tweet sent:", message)
    except Exception as e:
        print("⚠️ Failed to send tweet:", e)
        print("📄 Tweet content:", message)

def tweet_weather_update():
    print("Fetching and tweeting weather update...")
    try:
        current = fetch_current_weather()
        forecast = fetch_hourly_forecast()
        message = (
            f"South Bend Weather Update\n\n"
            f"Now: {current}\n\n"
            f"Next 4 Hours:\n{forecast}\n\n"
            f"#SouthBend #Weather"
        )
        safe_tweet_post(message)
    except Exception as e:
        print(f"Error tweeting weather update: {e}")

def tweet_alert(title, description):
    try:
        message = (
            f"WEATHER ALERT\n\n{title}\n\n{description[:230]}...\n\n"
            f"#SouthBend #WeatherAlert"
        )
        safe_tweet_post(message)
        print(f"✅ Alert posted: {title}")
    except Exception as e:
        print(f"Error tweeting alert: {e}")

def check_alerts_periodically():
    print("Checking for new alerts...")
    try:
        new_alerts = fetch_severe_alerts()
        for title, description in new_alerts:
            tweet_alert(title, description)
    except Exception as e:
        print(f"Error checking alerts: {e}")

def run_scheduler():
    scheduler = BackgroundScheduler()
    scheduler.add_job(tweet_weather_update, "cron", hour=7, minute=0)
    scheduler.add_job(tweet_weather_update, "cron", hour=11, minute=0)
    scheduler.add_job(tweet_weather_update, "cron", hour=16, minute=0)
    scheduler.add_job(tweet_weather_update, "cron", hour=20, minute=0)
    scheduler.add_job(check_alerts_periodically, "interval", minutes=5)
    scheduler.start()

    print("\n🕱️ Scheduler started. Press Ctrl+C to exit.")
    try:
        while True:
            time.sleep(60)
    except (KeyboardInterrupt, SystemExit):
        scheduler.shutdown()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="Print tweets instead of sending them")
    args = parser.parse_args()
    DRY_RUN = args.dry_run

    initialize_nws_urls()
    safe_tweet_post("NWS Weatherbot is now online and monitoring South Bend weather.")
    run_scheduler()
