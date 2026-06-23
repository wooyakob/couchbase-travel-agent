import os
import requests
from datetime import datetime
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain.agents import AgentExecutor, tool, create_tool_calling_agent
from langchain_core.prompts import ChatPromptTemplate

load_dotenv()  # reads variables from a .env file and sets them in os.environ

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
def convert_currency(usd_amount: float) -> str:
    """
    Converts USD to EUR using a STATIC approximate rate. 
    Use this for quick, informal budget estimates where 100% accuracy is NOT required.
    """
    rate = 0.92
    eur_amount = float(usd_amount) * rate
    return f"${usd_amount} USD is approximately €{eur_amount:.2f} EUR."

@tool
def convert_current_currency(usd_amount: float) -> str:
    """
    Converts USD to EUR using a DYNAMIC real-time API. 
    Use this ONLY when the user requires high accuracy, 'exact' rates, or 'real-time' data.
    """
    api_key = os.getenv("CURRENCYFREAKS_API_KEY")
    url = f'https://api.currencyfreaks.com/v2.0/rates/latest?apikey={api_key}&symbols=EUR'
    response = requests.get(url)
    if response.status_code == 200:
        rate = float(response.json()['rates']['EUR'])
        eur_amount = usd_amount * rate
        return f"${usd_amount} USD is exactly €{eur_amount:.2f} EUR."
    return "Currency conversion failed."

@tool
def convert_current_currencies(amounts: list[float]) -> str:
    """
    When a user specifies multiple currency amounts, use this tool.
    Converts multiple currency amounts from USD to EUR in a single API call.
    Use this when the user requires multiple conversion from USD to EUR.
    Example: amounts=[200, 67, 40]
    """
    api_key = os.getenv("CURRENCYFREAKS_API_KEY")
    url = f'https://api.currencyfreaks.com/v2.0/rates/latest?apikey={api_key}'

    try:
        response = requests.get(url)
        if response.status_code != 200:
            return "Currency conversion failed: could not reach exchange rate API."

        rates = response.json()['rates']
        results = []

        for usd_amount in amounts:
            rate = float(response.json()['rates']['EUR'])
            eur_amount = usd_amount * rate
            results.append(f"${usd_amount} USD is exactly €{eur_amount:.2f} EUR.")

        return "\n".join(results)

    except Exception as e:
        return f"Currency conversion failed: {str(e)}"

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

def run_app():
   # Clear the terminal for a 'Clean Slate' experience
   os.system('cls' if os.name == 'nt' else 'clear')
  
   llm = ChatOpenAI(model="gpt-4o", temperature=0)
  
   # Get the toolkit list
   tools = [get_weather, convert_currency, convert_current_currency, convert_current_currencies, get_current_date, get_weather_forecast]

   # Set the agent persona
   prompt = ChatPromptTemplate.from_messages([
       ("system", f"You are a polite British travel assistant who likes to use the full extent of your vocabulary to help with your customer's travel requests."),
       ("human", "{input}"),
       ("placeholder", "{agent_scratchpad}"), # Required for LangChain tool calling
   ])

   # Create the agent 
   agent = create_tool_calling_agent(llm, tools, prompt)
   agent_executor = AgentExecutor(agent=agent, tools=tools)

   # Interact with the human in the terminal 
   print("Launching Agent... (type exit to stop)")

   while True:
       user_text = input("\nYou: ")
       if user_text.lower() == 'exit': break
      
       for chunk in agent_executor.stream({"input": user_text}):
           # Check if the agent is calling a tool
           if "actions" in chunk:
               for action in chunk["actions"]:
                   print(f"\n  [TOOL CALL]: {action.tool}({action.tool_input})")
          
           # Check if we have the final answer
           elif "output" in chunk:
               print(f"\nAgent: {chunk['output']}")
       

if __name__ == "__main__":
    run_app()