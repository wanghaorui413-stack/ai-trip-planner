import logging
import json
import os
from typing import Optional

import requests
from dotenv import load_dotenv

# Get a logger instance for this module.
# The configuration is applied once in the main entrypoint.
logger = logging.getLogger(__name__)

load_dotenv()

# --- Configuration ---
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"
EXCHANGE_RATE_API_URL = "https://api.exchangerate-api.com/v4/latest/"


# --- Helper Function for Gemini API Calls ---
def call_gemini_api(prompt: str, response_schema: Optional[dict] = None) -> str:
    """
    Calls the Gemini API with a given prompt and returns the generated text or JSON.
    """
    logger.info("Calling Gemini API...")
    headers = {
        "Content-Type": "application/json",
    }
    params = {
        "key": GEMINI_API_KEY
    }
    payload = {
        "contents": [
            {
                "role": "user",
                "parts": [{"text": prompt}]
            }
        ]
    }

    if response_schema:
        payload["generationConfig"] = {
            "responseMimeType": "application/json",
            "responseSchema": response_schema
        }

    try:
        response = requests.post(GEMINI_API_URL, headers=headers, params=params, json=payload)
        response.raise_for_status()
        result = response.json()
        logger.info("Successfully received response from Gemini API.")

        if result and "candidates" in result and len(result["candidates"]) > 0 and \
           "content" in result["candidates"][0] and "parts" in result["candidates"][0]["content"] and \
           len(result["candidates"][0]["content"]["parts"]) > 0:
            # If a schema was provided, the response will be a JSON string. Parse it.
            if response_schema:
                try:
                    return json.loads(result["candidates"][0]["content"]["parts"][0]["text"])
                except json.JSONDecodeError:
                    logger.error("Failed to parse JSON response from AI.")
                    return {"error": "Failed to parse JSON response from AI."}
            else:
                return result["candidates"][0]["content"]["parts"][0]["text"]
        else:
            logger.warning("No candidates found in Gemini API response.")
            return "No content found in the API response."

    except requests.exceptions.RequestException as e:
        logger.error(f"Request to Gemini API failed: {e}", exc_info=True)
        return {"error": f"Could not retrieve information from AI. Details: {e}"}
    except Exception as e:
        logger.error(f"An unexpected error occurred in call_gemini_api: {e}", exc_info=True)
        return {"error": f"An unexpected error occurred. Details: {e}"}

# --- Agent Functions ---

def find_hotels_agent(destination: str, dates: str, preferences: str = "") -> str:
    """
    Agent to find hotel recommendations, ensuring direct and absolute Google Maps search links.
    """
    logger.info(f"Executing find_hotels_agent for destination: '{destination}'")
    if not destination or not dates:
        logger.warning("find_hotels_agent called with missing destination or dates.")
        return "Please provide destination and dates to find hotels."
    prompt = (f"Find 3 highly-rated hotels in {destination} for {dates}. Consider these preferences: {preferences if preferences else 'any'}. For each hotel, provide its name, a brief description, approximate price range, and "
              f"a full, absolute Google Maps search clickable links which will directly open google maps and point to particular hotels ")
    return call_gemini_api(prompt)

def find_restaurants_agent(destination: str, preferences: str = "") -> str:
    """
    Agent to find restaurant recommendations, ensuring direct and absolute Google Maps search links.
    """
    logger.info(f"Executing find_restaurants_agent for destination: '{destination}'")
    if not destination:
        logger.warning("find_restaurants_agent called with missing destination.")
        return "Please provide a destination to find restaurants."
    prompt = (f"Suggest 3 popular restaurants in {destination}. Consider these preferences: {preferences if preferences else 'any'}. For each restaurant, provide its name, cuisine type, a brief reason for recommendation, and "
              f"a full, absolute Google Maps search clickable links which will directly open google maps and point to particular restaurants")
    return call_gemini_api(prompt)

def plan_tourist_spots_agent(destination: str, dates: str, preferences: str = "") -> dict:
    """
    Agent to plan tourist spots itinerary, requesting structured JSON output.
    """
    logger.info(f"Executing plan_tourist_spots_agent for destination: '{destination}'")
    if not destination or not dates:
        logger.warning("plan_tourist_spots_agent called with missing destination or dates.")
        return {"error": "Please provide destination and dates to plan tourist spots."}

    response_schema = {
        "type": "ARRAY",
        "items": {
            "type": "OBJECT",
            "properties": {
                "day": {"type": "INTEGER"},
                "date": {"type": "STRING"},
                "activities": {
                    "type": "ARRAY",
                    "items": {
                        "type": "OBJECT",
                        "properties": {
                            "time": {"type": "STRING", "description": "Optional time for the activity"},
                            "name": {"type": "STRING", "description": "Name of the tourist spot or activity"},
                            "description": {"type": "STRING", "description": "Brief description of the activity"},
                            "map_link": {"type": "STRING", "description": "Full Google Maps search link"}
                        },
                        "required": ["name", "description", "map_link"]
                    }
                }
            },
            "required": ["day", "date", "activities"]
        }
    }

    prompt = (f"Plan a itinerary for tourist spots in {destination} for dates {dates}. Consider these preferences: {preferences if preferences else 'any'}. For each spot, include a mix of activities, brief descriptions, and "
              f"a full absolute Google Maps search link which are clickable and once i click those it should point to particular destination point.")

    return call_gemini_api(prompt, response_schema=response_schema)

def convert_currency_agent(amount: float, from_currency: str, to_currency: str) -> str:
    """
    Agent to convert currency using an external API.
    """
    logger.info(f"Executing convert_currency_agent for {amount} {from_currency} to {to_currency}")
    if not isinstance(amount, (int, float)) or amount <= 0:
        logger.warning(f"Invalid amount provided for currency conversion: {amount}")
        return "Please provide a valid positive amount for currency conversion."
    if not from_currency or not to_currency:
        return "Please provide both 'from' and 'to' currencies."

    from_currency = from_currency.upper()
    to_currency = to_currency.upper()

    try:
        response = requests.get(f"{EXCHANGE_RATE_API_URL}{from_currency}")
        response.raise_for_status()
        data = response.json()

        if data and data.get("rates"):
            rates = data["rates"]
            if from_currency not in rates:
                return f"Error: '{from_currency}' is not a valid currency code or exchange rate not found."
            if to_currency not in rates:
                return f"Error: '{to_currency}' is not a valid currency code or exchange rate not found."

            rate_from_to_usd = rates.get(to_currency) / rates.get(from_currency)
            converted_amount = amount * rate_from_to_usd
            logger.info("Successfully converted currency.")
            return f"{amount:.2f} {from_currency} is approximately {converted_amount:.2f} {to_currency}."
        else:
            return "Error: Could not retrieve exchange rates from the API."
    except requests.exceptions.RequestException as e:
        logger.error(f"Error calling currency API: {e}", exc_info=True)
        return f"Error: Failed to fetch exchange rates. Details: {e}"
    except Exception as e:
        logger.error(f"An unexpected error occurred during currency conversion: {e}", exc_info=True)
        return f"Error: An unexpected error occurred. Details: {e}"


# --- Example Usage (for testing the Python functions directly) ---
if __name__ == "__main__":
    # When running this file directly, set up logging to see the output.
    from logging_config import setup_logging

    setup_logging()

    logger.info("--- Testing Hotel Agent ---")
    hotel_info = find_hotels_agent("Kyoto, Japan", "Oct 10-15, 2025", "luxury, near temples")
    logger.info(hotel_info)

    logger.info("\n" + "=" * 50 + "\n")
    logger.info("--- Testing Restaurant Agent ---")
    restaurant_info = find_restaurants_agent("Kyoto, Japan", "traditional Japanese, vegan options")
    logger.info(restaurant_info)

    logger.info("\n" + "=" * 50 + "\n")
    logger.info("--- Testing Tourist Spot Agent ---")
    tourist_spot_info = plan_tourist_spots_agent("Kyoto, Japan", "Oct 10-15, 2025", "historical, nature")
    logger.info(json.dumps(tourist_spot_info, indent=2))

    logger.info("\n" + "=" * 50 + "\n")
    logger.info("--- Testing Currency Converter Agent ---")
    converted_value = convert_currency_agent(100, "USD", "EUR")
    logger.info(converted_value)

    print("--- Testing Tourist Spot Agent ---")
    tourist_spot_info = plan_tourist_spots_agent("Kyoto, Japan", "Oct 10-15, 2025", "historical, nature")
    print(json.dumps(tourist_spot_info, indent=2))
    print("\n" + "="*50 + "\n")

    print("--- Testing Currency Converter Agent ---")
    converted_value = convert_currency_agent(100, "USD", "EUR")
    print(converted_value)
    print("\n" + "="*50 + "\n")


