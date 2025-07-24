import os
import json
import time
import pytz
import requests
import schedule
from datetime import datetime, timedelta
from dotenv import load_dotenv
from requests_oauthlib import OAuth1

print("✨ WeatherBot (no tweepy) starting up...")

# === Load environment ===
load_dotenv()

CITY = os.getenv("CITY", "South Bend, Indiana")
LAT = os.getenv("LAT", "41.6764")
LON = os.getenv("LON", "-86.2520")

# === Twitter API credentials ===
TW_API_KEY = os.getenv("TWITTER_API_KEY")
TW_API_SECRET = os.getenv("TWITTER_API_SECRET")
TW_ACCESS_TOKEN = os.getenv("TWITTER_ACCESS_TOKEN")
TW_ACCESS_SECRET = os.getenv("TWITTER_ACCESS_TOKEN_SECRET")

# === Twitter auth ===
auth = OAuth1(
    TW_API_KEY,
    TW_API_SECRET,
    TW_ACCESS_TOKEN,
    TW_ACCESS_SECRET
)

# === Log file ===
def log(msg):
    print(msg)
    with open("weatherbot_log.txt", "a") as f:
        f.write(f"{datetime.utcnow()} - {msg}\n")

# === Twitter post ===
def post_tweet(text):
    url = "https://api.twitter.com/2/tweets"
    headers = {"Content-Type": "application/json"}
    payload = {"text": text}
    try:
        r = requests.post(url, headers=headers, json=payload, auth=auth)
        r.raise_for_status()
        log("[TWEET SENT] " + text)
    except Exception as e:
        log(f"[ERROR] Tweet failed: {e}")

# === NWS API headers ===
HEADERS = {"User-Agent": "WeatherBot (https://github.com/yourusername/weatherbot)"}

# === Fetch helper ===
def fetch_with_retries(url, retries=3, delay=5):
    for i in range(retries):
        try:
            r = requests.get(url, headers=HEADERS, timeout=10)
            r.raise_for_status()
            return r.json()
        except Exception as e:
            log(f"[RETRY {i+1}] {url}: {e}")
            time.sleep(delay)
    return None

# === Weather fetch ===
def fetch_current_weather():
    points = fetch_with_retries(f"https://api.weather.gov/points/{LAT},{LON}")
    if not points:
        return "Weather unavailable."

    stations = fetch_with_retries(points['properties']['observationStations'])
    if not stations or not stations.get("features"):
        return "Weather unavailable."

    station = stations['features'][0]['properties']['stationIdentifier']
    obs = fetch_with_retries(f"https://api.weather.gov/stations/{station}/observations/latest")
    if not obs:
        return "Weather unavailable."

    temp = obs['properties']['temperature']['value']
    desc = obs['properties']['textDescription']
    if temp is not None:
        temp_f = round(temp * 9 / 5 + 32)
        return f"Current weather in {CITY}:\n{temp_f}°F, {desc}"
    return f"Current weather in {CITY}:\n{desc}"

# === Forecast ===
def fetch_hourly_forecast():
    points = fetch_with_retries(f"https://api.weather.gov/points/{LAT},{LON}")
    if not points:
        return "Forecast unavailable."

    forecast_url = points['properties']['forecastHourly']
    forecast_data = fetch_with_retries(forecast_url)
    if not forecast_data:
        return "Forecast unavailable."

    local_tz = pytz.timezone('America/New_York')
    now = datetime.now(local_tz)
    start = now + timedelta(hours=1 if now.minute > 10 else 0)
    start = start.replace(minute=0, second=0, microsecond=0)

    summary = []
    for i in range(4):
        target = start + timedelta(hours=i * 3)
        for period in forecast_data['properties']['periods']:
            t = datetime.fromisoformat(period['startTime']).astimezone(local_tz)
            if abs((t - target).total_seconds()) <= 3600:
                time_label = target.strftime("%I:%M %p").lstrip("0")
                summary.append(f"{time_label}: {period['temperature']}°F, {period['shortForecast']}")
                break
    return "Upcoming forecast:\n" + "\n".join(summary)

# === Tweet Weather ===
def tweet_weather():
    current = fetch_current_weather()
    forecast = fetch_hourly_forecast()
    hashtags = "#SouthBend #Indiana #Weather #Forecast"
    text = f"{current}\n\n{forecast}\n\n{hashtags}"
    post_tweet(text)

# === Schedule ===
tweet_weather()
schedule.every().day.at("03:00").do(tweet_weather)
schedule.every().day.at("07:00").do(tweet_weather)
schedule.every().day.at("12:00").do(tweet_weather)
schedule.every().day.at("17:00").do(tweet_weather)
schedule.every().day.at("22:00").do(tweet_weather)

while True:
    schedule.run_pending()
    time.sleep(10)
