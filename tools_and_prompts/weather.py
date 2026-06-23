import requests
import os
from agentc.catalog import tool
from datetime import datetime

# Start with a single Weather tool
@tool
def get_weather(location: str) -> str:
    """
    Fetches the current weather for a specific city. 
    Input should be a city name (e.g., 'Paris').
    """
    api_key = os.getenv("OPENWEATHER_API_KEY")
    url = f"https://api.openweathermap.org/data/2.5/weather?q={location}&appid={api_key}&units=metric"
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        temp = data['main']['temp']
        desc = data['weather'][0]['description']
        return f"The weather in {location} is {desc} with a temperature of {temp}°C."
    return f"Could not find weather for {location}."

@tool
def get_current_date() -> str:
    """
    Returns today's date and day of the week. 
    Use this whenever the user mentions relative times like 'tomorrow', 
    'Wednesday', or 'next week' to ground your reasoning.
    """
    return datetime.now().strftime("Today is %A, %B %d, %Y.")

@tool
def get_weather_forecast(location: str) -> str:
    """
    Fetches the 5-day weather forecast for a city as a raw list of dates.
    Use this for questions about future dates or planning trips.
    """
    api_key = os.getenv("OPENWEATHER_API_KEY")
    url = f"https://api.openweathermap.org/data/2.5/forecast?q={location}&appid={api_key}&units=metric"
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        # Extracts one reading per day
        forecasts = data['list'][::8][:5]
        details = [f"{f['dt_txt']}: {f['weather'][0]['description']}, {f['main']['temp']}°C" for f in forecasts]
        return f"5-day forecast for {location}:\n" + "\n".join(details)
    return f"Could not find forecast for {location}."