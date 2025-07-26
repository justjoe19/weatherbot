# 🌦️ WeatherBot

A Python bot that tweets current weather forecasts and severe weather alerts for **South Bend, Indiana**, using data from the [National Weather Service (NWS)](https://www.weather.gov/) and the Twitter API.

---

## 🔧 Features

- ⛅ Tweets current conditions and a short-term forecast every day at:
  - 3 AM, 7 AM, 12 PM, 5 PM, and 10 PM
- ⚠️ Tweets severe weather alerts as soon as they’re published
- 🗃️ Caches previously tweeted alerts to avoid duplicates
- ⏰ Uses `apscheduler` to schedule tasks
- 📡 Pulls live data from `api.weather.gov`
- 🐍 Built in Python with `tweepy`, `requests`, `dotenv`, and `apscheduler`
- Currently running on [X.com/SBforecast](https://x.com/SBforecast)