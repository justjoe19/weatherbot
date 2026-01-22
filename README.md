# 🌦️ WeatherBot

**Automated Weather Forecasting & Alert System for South Bend, Indiana**

WeatherBot is a robust Python application designed to provide real-time weather updates and severe weather alerts via Twitter (X). Leveraging the National Weather Service (NWS) API, it ensures the community stays informed with accurate, timely, and automated broadcasts.

---

## 📋 Table of Contents
- [Features](#-features)
- [Tech Stack](#-tech-stack)
- [Configuration](#-configuration)
- [Local Development](#-local-development)
- [Deployment](#-deployment)

---

## 🌟 Features

*   **Scheduled Forecasts**: Automatically tweets current conditions and short-term forecasts five times daily (3 AM, 7 AM, 12 PM, 5 PM, and 10 PM).
*   **Real-Time Alerts**: Monitors NWS feeds every 5 minutes to broadcast severe weather warnings immediately.
*   **Smart Caching**: Implements a caching mechanism to prevent duplicate alerts for the same weather event.
*   **Resilient Architecture**: Built with `apscheduler` for reliable task scheduling and error handling for network requests.
*   **Live Data**: Fetches precise, localized data directly from `api.weather.gov`.

---

## 🛠 Tech Stack

*   **Language**: Python 3.11+
*   **APIs**:
    *   [National Weather Service API](https://www.weather.gov/documentation/services-web-api) (Weather Data)
    *   [Twitter API v2](https://developer.twitter.com/en/docs/twitter-api) (Broadcasting)
*   **Key Libraries**:
    *   `requests` & `requests-oauthlib`: HTTP networking and OAuth authentication.
    *   `apscheduler`: Advanced background scheduling.
    *   `flask`: Lightweight web server (required for cloud hosting health checks).
    *   `python-dotenv`: Environment variable management.

---

## ⚙️ Configuration

The application requires the following environment variables to function. These can be set in a `.env` file for local development or in your cloud provider's dashboard.

| Variable | Description | Default / Example |
| :--- | :--- | :--- |
| `CITY` | Target city name for display | `South Bend, Indiana` |
| `LAT` | Latitude of the location | `41.6764` |
| `LON` | Longitude of the location | `-86.2520` |
| `TWITTER_API_KEY` | Twitter Consumer Key | `...` |
| `TWITTER_API_SECRET` | Twitter Consumer Secret | `...` |
| `TWITTER_ACCESS_TOKEN` | Twitter Access Token | `...` |
| `TWITTER_ACCESS_TOKEN_SECRET` | Twitter Access Token Secret | `...` |

---

## 💻 Local Development

To run WeatherBot locally on your machine:

1.  **Clone the repository**
    ```bash
    git clone https://github.com/yourusername/weatherbot.git
    cd weatherbot
    ```

2.  **Install dependencies**
    ```bash
    pip install -r requirements.txt
    ```

3.  **Configure Environment**
    Create a `.env` file in the root directory and add your API keys (see [Configuration](#-configuration)).

4.  **Run the Bot**
    ```bash
    python weatherbot.py
    ```
    *The bot will start a local web server at `http://localhost:5000` and begin its scheduling loop.*

---

## 🚀 Deployment

This project is optimized for deployment on **Render** as a **Web Service** (Free Tier compatible).

### Deploying with Render Blueprints

1.  **Push to GitHub**: Ensure your code is in a GitHub repository.
2.  **New Blueprint**: Go to the [Render Dashboard](https://dashboard.render.com/), click **New**, and select **Blueprint**.
3.  **Connect Repo**: Select your `weatherbot` repository.
4.  **Auto-Configuration**: Render will detect the `render.yaml` file included in this project.
5.  **Credentials**: You will be prompted to input your Twitter API credentials securely during the setup.
6.  **Launch**: Click **Apply**. Render will build the environment and start the web service.

The service is configured to run continuously. Render will ping the web server to keep it alive.

---

*Developed by [Your Name]*
