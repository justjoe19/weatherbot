# 🌤️ Weatherbot

Weatherbot is a Python app that tweets the current weather, a 12-hour forecast, and severe weather alerts for a specific location.  

It uses the **OpenWeatherMap API** for weather data and the **Twitter API** to post updates automatically on a schedule.  

✨ Features:
- 🕒 Tweets **current weather** with rounded temperatures (°F)
- 📆 Includes a **12-hour forecast** in 3-hour increments
- ⚠️ Checks for **severe weather alerts** every 5 minutes and posts them **immediately**
- 🗂 Uses cached forecast data to fill in **missing time slots** if the API skips them
- ⏰ Runs continuously and posts at scheduled times
