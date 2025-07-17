import requests
import tweepy
import schedule
import time
import os
import json
from datetime import datetime, timedelta
from dotenv import load_dotenv

print("🚀 Weatherbot is starting up...")

# === Load environment variables from .env ===
load_dotenv()

# === OpenWeatherMap API credentials ===
WEATHER_API_KEY = os.getenv("WEATHER_API_KEY")
CITY = os.getenv("CITY", "South Bend, Indiana")
LAT = os.getenv("LAT", "41.6764")
LON = os.getenv("LON", "-86.2520")
CURRENT_WEATHER_URL = f"https://api.openweathermap.org/data/2.5/weather?q={CITY}&appid={WEATHER_API_KEY}&units=imperial"
FORECAST_URL = f"https://api.openweathermap.org/data/2.5/forecast?q={CITY}&appid={WEATHER_API_KEY}&units=imperial"
ALERTS_URL = f"https://api.openweathermap.org/data/3.0/onecall?lat={LAT}&lon={LON}&appid={WEATHER_API_KEY}&units=imperial"

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

# === File for tracking last alert sent and forecast cache ===
ALERT_TRACK_FILE = "last_alert.txt"
FORECAST_CACHE_FILE = "forecast_cache.json"

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

# === Fetch current weather ===
def fetch_current_weather():
    response = requests.get(CURRENT_WEATHER_URL)
    if response.status_code == 200:
        data = response.json()
        temp = data["main"]["temp"]
        weather_desc = data["weather"][0]["description"]
        city = data["name"]
        return f"Current weather in {city}:\n{temp}°F, {weather_desc.capitalize()} #SouthBend #Weather"
    else:
        log("[ERROR] Failed to fetch current weather data.")
        return "Failed to fetch current weather data."

# === Fetch 12-hour forecast and fill missing slots from cache ===
def fetch_12_hour_forecast():
    live_data = None
    try:
        response = requests.get(FORECAST_URL)
        if response.status_code == 200:
            live_data = response.json()
            save_forecast_cache(live_data)  # Update cache with fresh data
        else:
            log(f"[WARNING] Could not fetch live forecast (status {response.status_code})")
    except Exception as e:
        log(f"[ERROR] Failed to fetch live forecast: {e}")

    # Load cached data if available
    cached_data = load_forecast_cache()

    if not live_data and not cached_data:
        return "Failed to fetch forecast and no cached data available."

    # Use live forecast first, then fill missing slots with cached forecast
    combined_forecast = []
    seen_times = set()

    now = datetime.now()

    # Find the next 3-hour increment
    hours_to_next_block = (3 - now.hour % 3) % 3
    if hours_to_next_block == 0:
        hours_to_next_block = 3
    next_forecast_time = (now + timedelta(hours=hours_to_next_block)).replace(
        minute=0, second=0, microsecond=0
    )

    # Merge live and cached data
    def merge_forecasts(forecast_list):
        merged = []
        for forecast in forecast_list:
            dt = datetime.strptime(forecast["dt_txt"], "%Y-%m-%d %H:%M:%S")
            if dt >= next_forecast_time and dt not in seen_times:
                seen_times.add(dt)
                merged.append((dt, forecast))
        return merged

    if cached_data:
        combined_forecast.extend(merge_forecasts(cached_data["list"]))
    if live_data:
        combined_forecast.extend(merge_forecasts(live_data["list"]))

    # Sort merged forecasts chronologically and take next 4 slots
    combined_forecast.sort(key=lambda x: x[0])
    forecast_summary = []

    for dt, forecast in combined_forecast[:4]:
        temp = forecast["main"]["temp"]
        weather_desc = forecast["weather"][0]["description"]
        formatted_time = dt.strftime("%I:%M %p")
        forecast_summary.append(f"{formatted_time}: {temp}°F, {weather_desc.capitalize()}")

    if not forecast_summary:
        return "No forecast data available."

    return "Upcoming weather:\n" + "\n".join(forecast_summary) + "\n#SouthBend #Forecast"

# === Tweet weather update ===
def tweet_weather():
    try:
        current_weather = fetch_current_weather()
        forecast = fetch_12_hour_forecast()
        weather_update = current_weather + "\n\n" + forecast

        response = client.create_tweet(text=weather_update)
        print("Tweeted:", response.data)
        log(f"[WEATHER TWEETED] {weather_update}")

    except tweepy.errors.TooManyRequests:
        log("[ERROR] Rate limit exceeded. Retrying after 15 minutes...")
        time.sleep(900)
        tweet_weather()
    except Exception as e:
        print(f"[ERROR] in tweet_weather: {e}")
        log(f"[ERROR] in tweet_weather: {e}")

# === Check and tweet severe weather alerts ===
last_alert_sent = load_last_alert()

def check_severe_weather():
    global last_alert_sent
    try:
        response = requests.get(ALERTS_URL)
        if response.status_code == 200:
            data = response.json()
            alerts = data.get("alerts", [])
            if alerts:
                latest_alert = alerts[0]
                event = latest_alert.get("event", "Severe Weather Alert")
                description = latest_alert.get("description", "")

                if event != last_alert_sent:
                    hashtags = "#SouthBend #WeatherAlert"
                    tweet_text = f"⚠️ {event} ⚠️\n\n{description}\n\n{hashtags}"

                    if len(tweet_text) > 280:
                        allowed_length = 280 - len(hashtags) - 5
                        tweet_text = f"⚠️ {event} ⚠️\n\n{description[:allowed_length]}...\n\n{hashtags}"

                    client.create_tweet(text=tweet_text)
                    log(f"[ALERT TWEETED] {event} - {description[:240]}")
                    last_alert_sent = event
                    save_last_alert(event)
            else:
                log("[NO ALERTS] No severe weather alerts at this time.")
        else:
            log(f"[ERROR] Failed to fetch alerts: Status {response.status_code}")
    except Exception as e:
        log(f"[ERROR] in check_severe_weather: {e}")

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
schedule.every(5).minutes.do(check_severe_weather)

# === Keep script running ===
while True:
    schedule.run_pending()
    time.sleep(10)
