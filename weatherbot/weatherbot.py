import requests
import tweepy
import schedule
import time
from datetime import datetime

# === OpenWeatherMap API credentials ===
WEATHER_API_KEY = "5e671b7f581679f3423aa7772f50de40"
CITY = "South Bend, Indiana"
LAT = 41.6764
LON = -86.2520
CURRENT_WEATHER_URL = f"https://api.openweathermap.org/data/2.5/weather?q={CITY}&appid={WEATHER_API_KEY}&units=imp>
FORECAST_URL = f"https://api.openweathermap.org/data/2.5/forecast?q={CITY}&appid={WEATHER_API_KEY}&units=imperial"
ALERTS_URL = f"https://api.openweathermap.org/data/3.0/onecall?lat={LAT}&lon={LON}&appid={WEATHER_API_KEY}&units=i>

# === Twitter API credentials ===
TWITTER_BEARER_TOKEN = "bearer_token"
TWITTER_API_KEY = "api_key"
TWITTER_API_SECRET = "api_secret_key"
TWITTER_ACCESS_TOKEN = "api_access_token"
TWITTER_ACCESS_TOKEN_SECRET = "secret_access_token"

# === Twitter client ===
client = tweepy.Client(
    bearer_token=TWITTER_BEARER_TOKEN,
    consumer_key=TWITTER_API_KEY,
    consumer_secret=TWITTER_API_SECRET,
    access_token=TWITTER_ACCESS_TOKEN,
    access_token_secret=TWITTER_ACCESS_TOKEN_SECRET,
)

# === Last alert tracking ===
last_alert_sent = None

# === Logging ===
def log(msg):
    with open("/home/joe/weatherbot_log.txt", "a") as f:
        f.write(f"{datetime.now()} - {msg}\n")

# === Fetch current weather ===
def fetch_current_weather():
    response = requests.get(CURRENT_WEATHER_URL)
    if response.status_code == 200:
        data = response.json()
        temp = data["main"]["temp"]
        weather_desc = data["weather"][0]["description"]
        city = data["name"]
        return f"Current weather in {city}:\n {temp}°F, {weather_desc.capitalize()}"
    else:
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

        return "Upcoming weather:\n" + "\n".join(forecast_summary)
    else:
        return "Failed to fetch 12-hour forecast."

# === Post weather tweet ===
def tweet_weather():
    try:
        current_weather = fetch_current_weather()
        forecast = fetch_12_hour_forecast()
        weather_update = current_weather + "\n\n" + forecast

        response = client.create_tweet(text=weather_update)
        print("Tweeted:", response.data)

        with open("/home/joe/weatherbot_log.txt", "a") as f:
            f.write(f"Tweeted at {datetime.now()}:\n{weather_update}\n\n")

    except tweepy.errors.TooManyRequests:
        print("Rate limit exceeded. Retrying after 15 minutes...")
        time.sleep(900)
        tweet_weather()
    except Exception as e:
        print(f"An error occurred: {e}")
        log(f"[ERROR] in tweet_weather: {e}")

# === Check for and tweet severe alerts ===
def check_severe_weather():
    global last_alert_sent
    try:
        response = requests.get(ALERTS_URL)
        if response.status_code == 200:
            data = response.json()
            alerts = data.get("alerts", [])
            if alerts:
                latest = alerts[0]
                event = latest.get("event", "Severe Weather Alert")
                description = latest.get("description", "")

                if event != last_alert_sent:
                    tweet_text = f"⚠️ {event} ⚠️\n\n{description[:240]}..."
                    client.create_tweet(text=tweet_text)
                    log(f"[ALERT TWEETED] {event} - {description[:240]}")
                    last_alert_sent = event
        else:
            log("Failed to fetch alerts")
    except Exception as e:
        log(f"[ERROR] in check_severe_weather: {e}")

# === Send an initial tweet ===
tweet_weather()

# === Schedule the function to run at specific times ===
schedule.every().day.at("01:00").do(tweet_weather)
schedule.every().day.at("07:00").do(tweet_weather)
schedule.every().day.at("11:00").do(tweet_weather)
schedule.every().day.at("13:00").do(tweet_weather)
schedule.every().day.at("16:00").do(tweet_weather)
schedule.every().day.at("19:00").do(tweet_weather)
# === Keep script running and check for alerts ===
while True:
    schedule.run_pending()
    check_severe_weather()
    time.sleep(60)
