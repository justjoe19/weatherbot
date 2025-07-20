import requests
import tweepy
import schedule
import time
import os
import json
from datetime import datetime, timedelta
from dotenv import load_dotenv

print("🚀 NWS Weatherbot is starting up...")

# === Load environment variables from .env ===
load_dotenv()

# === Location settings ===
CITY = os.getenv("CITY", "South Bend, Indiana")
LAT = os.getenv("LAT", "41.6764")
LON = os.getenv("LON", "-86.2520")

# === Twitter API credentials ===
TWITTER_BEARER_TOKEN = os.getenv("TWITTER_BEARER_TOKEN")
TWITTER_API_KEY = os.getenv("TWITTER_API_KEY")
TWITTER_API_SECRET = os.getenv("TWITTER_API_SECRET")
TWITTER_ACCESS_TOKEN = os.getenv("TWITTER_ACCESS_TOKEN")
TWITTER_ACCESS_TOKEN_SECRET = os.getenv("TWITTER_ACCESS_TOKEN_SECRET")

# === Twitter client ===
client = tweepy.Client(
    bearer_token=TWITTER_BEARER_TOKEN,
    consumer_key=TWITTER_API_KEY,
    consumer_secret=TWITTER_API_SECRET,
    access_token=TWITTER_ACCESS_TOKEN,
    access_token_secret=TWITTER_ACCESS_TOKEN_SECRET,
)

# === Files for tracking alerts and caching forecast ===
ALERT_TRACK_FILE = "last_alert.txt"
FORECAST_CACHE_FILE = "forecast_cache.json"

# === NWS API headers ===
HEADERS = {"User-Agent": "WeatherBot (https://github.com/justjoe19/weatherbot)"}


# === Logging ===
def log(msg):
    with open("weatherbot_log.txt", "a") as f:
        f.write(f"{datetime.now()} - {msg}\n")

# === Load last alert from file ===
def load_last_alert():
    if os.path.exists(ALERT_TRACK_FILE):
        with open(ALERT_TRACK_FILE, "r") as f:
            return f.read().strip()
    return None

# === Save last alert to file ===
def save_last_alert(alert_event):
    with open(ALERT_TRACK_FILE, "w") as f:
        f.write(alert_event)

# === Save forecast data to cache ===
def save_forecast_cache(data):
    with open(FORECAST_CACHE_FILE, "w") as f:
        json.dump(data, f)

# === Load forecast data from cache ===
def load_forecast_cache():
    if os.path.exists(FORECAST_CACHE_FILE):
        with open(FORECAST_CACHE_FILE, "r") as f:
            return json.load(f)
    return None

# === Fetch hourly forecast from NWS ===
def fetch_hourly_forecast():
    try:
        # Step 1: Get grid point info for the location
        points_url = f"https://api.weather.gov/points/{LAT},{LON}"
        points_resp = requests.get(points_url, headers=HEADERS)
        points_resp.raise_for_status()
        points_data = points_resp.json()

        # Step 2: Get hourly forecast URL
        forecast_url = points_data["properties"]["forecastHourly"]

        # Step 3: Get hourly forecast data
        forecast_resp = requests.get(forecast_url, headers=HEADERS)
        forecast_resp.raise_for_status()
        forecast_data = forecast_resp.json()
        save_forecast_cache(forecast_data)  # Cache the data

        # Step 4: Filter forecasts starting 3 hours from now
        now = datetime.now()
        start_time = now + timedelta(hours=3)

        forecast_summary = []
        count = 0
        for period in forecast_data["properties"]["periods"]:
            forecast_time = datetime.fromisoformat(period["startTime"])
            if forecast_time >= start_time and count < 4:
                temp = period["temperature"]
                short_forecast = period["shortForecast"]
                formatted_time = forecast_time.strftime("%I:%M %p").lstrip("0")
                forecast_summary.append(f"{formatted_time}: {temp}°F, {short_forecast}")
                count += 1

        if not forecast_summary:
            return "No forecast data available."

        return f"Upcoming weather for {CITY}:\n" + "\n".join(forecast_summary) + "\n#SouthBend #Indiana #Weather #Forecast"

    except Exception as e:
        log(f"[ERROR] Failed to fetch forecast: {e}")
        cached_data = load_forecast_cache()
        if cached_data:
            log("[WARNING] Using cached forecast data.")
            return "Using cached forecast data.\n"
        return "Failed to fetch forecast data."

# === Fetch active severe weather alerts from NWS ===
last_alert_sent = load_last_alert()

def fetch_severe_weather_alerts():
    global last_alert_sent
    try:
        alerts_url = f"https://api.weather.gov/alerts/active?point={LAT},{LON}"
        alerts_resp = requests.get(alerts_url, headers=HEADERS)
        alerts_resp.raise_for_status()
        alerts_data = alerts_resp.json()

        for alert in alerts_data.get("features", []):
            event = alert["properties"]["event"]
            description = alert["properties"]["description"]

            if event != last_alert_sent:
                hashtags = f"#{CITY.replace(' ', '')} #WeatherAlert"
                tweet_text = f"⚠️ {event} ⚠️\n\n{description}\n\n{hashtags}"

                # Truncate if too long
                if len(tweet_text) > 280:
                    allowed_length = 280 - len(hashtags) - 5
                    tweet_text = f"⚠️ {event} ⚠️\n\n{description[:allowed_length]}...\n\n{hashtags}"

                client.create_tweet(text=tweet_text)
                log(f"[ALERT TWEETED] {event} - {description[:240]}")
                last_alert_sent = event
                save_last_alert(event)
                break  # Only tweet the first new alert
        else:
            log("[NO ALERTS] No severe weather alerts at this time.")

    except Exception as e:
        log(f"[ERROR] Failed to fetch severe weather alerts: {e}")

# === Tweet weather update ===
def tweet_weather():
    try:
        forecast = fetch_hourly_forecast()
        response = client.create_tweet(text=forecast)
        print("Tweeted:", response.data)
        log(f"[WEATHER TWEETED] {forecast}")

    except tweepy.errors.TooManyRequests:
        log("[ERROR] Rate limit exceeded. Retrying after 15 minutes...")
        time.sleep(900)
        tweet_weather()
    except Exception as e:
        log(f"[ERROR] in tweet_weather: {e}")

# === Send initial tweet ===
tweet_weather()

# === Schedule tweets ===
schedule.every().day.at("01:00").do(tweet_weather)
schedule.every().day.at("07:00").do(tweet_weather)
schedule.every().day.at("11:00").do(tweet_weather)
schedule.every().day.at("13:00").do(tweet_weather)
schedule.every().day.at("16:00").do(tweet_weather)
schedule.every().day.at("19:00").do(tweet_weather)

# === Check severe weather every 5 minutes ===
schedule.every(5).minutes.do(fetch_severe_weather_alerts)

# === Keep script running ===
while True:
    schedule.run_pending()
    time.sleep(10)
