import requests
import tweepy
import schedule
import time
from datetime import datetime

# OpenWeatherMap API credentials
WEATHER_API_KEY = "5e671b7f581679f3423aa7772f50de40"
CITY = "South Bend, Indiana"
CURRENT_WEATHER_URL = f"https://api.openweathermap.org/data/2.5/weather?q={CITY}&appid={WEATHER_API_KEY}&units=imperial"
FORECAST_URL = f"https://api.openweathermap.org/data/2.5/forecast?q={CITY}&appid={WEATHER_API_KEY}&units=imperial"

# Twitter API credentials
TWITTER_BEARER_TOKEN = "your_bearer_token"  
TWITTER_API_KEY = "your_twitter_api"
TWITTER_API_SECRET = "your_twitter_secret_api"
TWITTER_ACCESS_TOKEN = "your_twitter_access_token"
TWITTER_ACCESS_TOKEN_SECRET = "your_twitter_secret_token"

# Fetch current weather data
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

# Fetch 12-hour weather forecast
def fetch_12_hour_forecast():
    response = requests.get(FORECAST_URL)
    if response.status_code == 200:
        data = response.json()
        forecast_list = data["list"]
        forecast_summary = []
        
        # Extract the next 4 entries (12 hours)
        for forecast in forecast_list[:4]:
            temp = forecast["main"]["temp"]
            weather_desc = forecast["weather"][0]["description"]
            dt = datetime.strptime(forecast["dt_txt"], "%Y-%m-%d %H:%M:%S")
            formatted_time = dt.strftime("%I:%M %p")  # Format time as HH:MM AM/PM
            forecast_summary.append(f"{formatted_time}: {temp}°F, {weather_desc.capitalize()}")
        
        return "Upcoming weather:\n" + "\n".join(forecast_summary)
    else:
        return "Failed to fetch 12-hour forecast."

# Post to Twitter using v2 endpoint
def tweet_weather():
    client = tweepy.Client(
        bearer_token=TWITTER_BEARER_TOKEN,
        consumer_key=TWITTER_API_KEY,
        consumer_secret=TWITTER_API_SECRET,
        access_token=TWITTER_ACCESS_TOKEN,
        access_token_secret=TWITTER_ACCESS_TOKEN_SECRET,
    )

    current_weather = fetch_current_weather()
    forecast = fetch_12_hour_forecast()
    weather_update = current_weather + "\n\n" + forecast

    response = client.create_tweet(text=weather_update)
    print("Tweeted:", response.data)

# Send an initial tweet
tweet_weather()

# Schedule the function to run at specific times
schedule.every().day.at("01:00").do(tweet_weather)  # 1 AM
schedule.every().day.at("07:00").do(tweet_weather)  # 7 AM
schedule.every().day.at("11:00").do(tweet_weather)  # 11 AM
schedule.every().day.at("13:00").do(tweet_weather)  # 1 PM
schedule.every().day.at("16:00").do(tweet_weather)  # 4 PM
schedule.every().day.at("19:00").do(tweet_weather)  # 8 PM

# Keep the script running
while True:
    schedule.run_pending()
    time.sleep(1)
