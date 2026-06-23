from langchain_core.messages import SystemMessage

from tools_and_prompts.memory import (
    save_user_preference, get_user_preferences, book_trip, get_trip_history
)

from tools_and_prompts.weather import (
    get_weather, get_weather_forecast, get_current_date
) 

from tools_and_prompts.currency import (
    convert_currency, convert_current_currency, convert_current_currencies, convert_currencies
)

from tools_and_prompts.hotels import (
    find_hotels_by_location, find_hotels_by_coordinates, get_hotel_sentiment, get_hotels_sentiments, find_hotels_by_vibe, find_hotels_by_vibe_and_coordinates, get_hotels_details
)

from tools_and_prompts.policies import get_travel_policy

def load_assets():
    with open("tools_and_prompts/persona.txt") as f:
        persona_base = f.read()

    prompt = SystemMessage(content=persona_base)

    tools_weather = [
        get_weather, get_weather_forecast, get_current_date
    ]

    tools_currency = [
        convert_currency, convert_current_currency, convert_current_currencies, convert_currencies
    ] 

    tools_hotels = [
        find_hotels_by_location, find_hotels_by_coordinates, get_hotel_sentiment, get_hotels_sentiments, find_hotels_by_vibe, find_hotels_by_vibe_and_coordinates, get_hotels_details
    ]

    tools_memory = [
        save_user_preference, get_user_preferences, book_trip, get_trip_history
    ]

    tools_policy = [get_travel_policy]

    
    tools = tools_weather + tools_currency + tools_hotels + tools_policy + tools_memory
    return tools, prompt