import requests
import os
from agentc.catalog import tool

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
def convert_currencies(amounts: list[float], from_currency: str, to_currency: str) -> str:
    """
    Converts one or multiple currency amounts in a single API call.
    Use this when the user requires conversion from any currency to another. 
    Example: amounts=[200, 67, 40], from_currency='GBP', to_currency='EUR'
    """
    api_key = os.getenv("CURRENCYFREAKS_API_KEY")
    url = f'https://api.currencyfreaks.com/v2.0/rates/latest?apikey={api_key}'

    try:
        response = requests.get(url)
        if response.status_code != 200:
            return "Currency conversion failed: could not reach exchange rate API."

        rates = response.json()['rates']
        results = []

        for amount in amounts:
            rate_from = float(rates.get(from_currency, 1))
            rate_to   = float(rates.get(to_currency, 1))
            converted = (amount / rate_from) * rate_to
            results.append(f"{amount:.0f} {from_currency} = {converted:.2f} {to_currency}")

        return "\n".join(results)

    except Exception as e:
        return f"Currency conversion failed: {str(e)}"
