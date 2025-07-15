import requests
import tweepy
import schedule
import time
import os
from datetime import datetime
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

# === File for tracking last alert sent ===
ALERT_TRACK_FILE = "last_alert.txt"

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

# === Fetch 12-hour forecast ===
def fetch_12_hour_forecast():
    response = requests.get(FORECAST_URL)
    if response.status_code == 200:
        data = response.json()
        forecast_list = data["list"]
        forecast_summary = []

        for forecast in forecast_list[:4]:
            temp = forecast["main"]["temp"]
            weather_desc = forecast["weather"][0]["description"]
            dt = datetime.strptime(forecast["dt_txt"], "%Y-%m-%d %H:%M:%S")
            formatted_time = dt.strftime("%I:%M %p")
            forecast_summary.append(f"{formatted_time}: {temp}°F, {weather_desc.capitalize()}")

        return "Upcoming weather:\n" + "\n".join(forecast_summary) + "\n#SouthBend #Forecast"
    else:
        log("[ERROR] Failed to fetch 12-hour forecast.")
        return "Failed to fetch 12-hour forecast."

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
