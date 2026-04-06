import httpx
from app.core.config import settings
from typing import Optional, Dict, Any

from app.services.flight_service import fetch_flights
from app.services.hotel_service import fetch_hotels

MOCK_MODE = settings.app_env == "development"


async def search_flights(origin: str, destination: str, dates: dict, budget: str) -> dict:
    return await fetch_flights(
        origin=origin,
        destination=destination,
        dates=dates,
        budget=budget,
    )


async def search_hotels(destination: str, dates: dict, budget: str, travelers: str) -> dict:
    return await fetch_hotels(
        destination=destination,
        dates=dates,
        budget=budget,
        travelers=travelers,
    )


async def submit_trip_to_backend(
    location: str,
    start_date: str,
    end_date: str,
    travelers: str,
    budget: str,
    experience: str,
    flight_details: Optional[Dict[str, Any]] = None,
    hotel_details: Optional[Dict[str, Any]] = None,
    user_id: Optional[str] = None,
) -> dict:
    payload = {
        "user_id": user_id,
        "location": location,
        "start_date": start_date,
        "end_date": end_date,
        "travelers": travelers,
        "budget": budget,
        "experience": experience,
        "flight_details": flight_details,
        "hotel_details": hotel_details,
    }

    if MOCK_MODE:
        print(f"[mock] submit_trip_to_backend payload: {payload}")
        return {"status": "received", "payload": payload}

    async with httpx.AsyncClient(timeout=15.0) as client:
        res = await client.post(settings.internal_api_submit, json=payload)
        res.raise_for_status()
        return res.json()

async def check_cancellation_eligibility(trip_id: str) -> dict:
    # MVP Mock implementation
    # Returns 100% refund logic assuming > 72 hours
    return {
        "eligible": True,
        "refund_amount_credits": 1000,
        "days_valid": 30
    }

async def search_flexible_alternatives(location: str, start_date: str, end_date: str, budget: str, travelers: str) -> dict:
    # MVP Mock implementation for "Soft No"
    return {
        "alternative_found": True,
        "suggested_location": location,
        "suggested_dates": {"start": "2026-10-12", "end": "2026-10-17"}, # 2 days later
        "original_price": 1200,
        "new_price": 850
    }



TOOL_DEFINITIONS = [
    {
        "name": "search_flights",
        "description": (
            "Search for available flights between two cities for given dates and budget. "
            "Returns route, stop count, flight duration, and estimated price."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "origin": {"type": "string", "description": "IATA code or city name of departure."},
                "destination": {"type": "string", "description": "IATA code or city name of arrival."},
                "dates": {
                    "type": "object",
                    "properties": {
                        "start": {"type": "string", "description": "Departure date YYYY-MM-DD."},
                        "end": {"type": "string", "description": "Return date YYYY-MM-DD."},
                    },
                    "required": ["start", "end"],
                },
                "budget": {"type": "string", "enum": ["Budget", "Moderate", "Luxury"]},
            },
            "required": ["origin", "destination", "dates", "budget"],
        },
    },
    {
        "name": "search_hotels",
        "description": (
            "Search for hotels at a destination for given dates, budget tier, and traveler type. "
            "Returns hotel name, number of nights, rating, and nightly price."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "destination": {"type": "string"},
                "dates": {
                    "type": "object",
                    "properties": {
                        "start": {"type": "string"},
                        "end": {"type": "string"},
                    },
                    "required": ["start", "end"],
                },
                "budget": {"type": "string", "enum": ["Budget", "Moderate", "Luxury"]},
                "travelers": {"type": "string", "enum": ["Solo", "Couple", "Family"]},
            },
            "required": ["destination", "dates", "budget", "travelers"],
        },
    },
    {
        "name": "submit_trip_to_backend",
        "description": (
            "Call this tool ONLY when all five travel parameters have been confirmed by the user, "
            "AND you have presented option(s) from search_flights and search_hotels, and the user has chosen an option. "
            "Submits the final payload (including the chosen flight/hotel) to the backend team for booking."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "location": {"type": "string"},
                "start_date": {"type": "string"},
                "end_date": {"type": "string"},
                "travelers": {"type": "string", "enum": ["Solo", "Couple", "Family"]},
                "budget": {"type": "string", "enum": ["Budget", "Moderate", "Luxury"]},
                "experience": {"type": "string", "enum": ["Relaxation", "Adventure", "Shopping", "Culture", "Mix of everything"]},
                "flight_details": {
                    "type": "object",
                    "description": "Details of the chosen flight (from search_flights tool)",
                },
                "hotel_details": {
                    "type": "object",
                    "description": "Details of the chosen hotel (from search_hotels tool)",
                },
            },
            "required": ["location", "start_date", "end_date", "travelers", "budget", "experience"],
        },
    },
    {
        "name": "check_cancellation_eligibility",
        "description": "Checks if a specific trip is eligible for a refund credit. Call this when a user asks to cancel.",
        "input_schema": {
            "type": "object",
            "properties": {
                "trip_id": {"type": "string", "description": "The ID or description of the trip to cancel."}
            },
            "required": ["trip_id"]
        }
    },
    {
        "name": "search_flexible_alternatives",
        "description": "Searches for cheaper alternatives when Amadeus/Hotel prices exceed the user's budget.",
        "input_schema": {
            "type": "object",
            "properties": {
                "location": {"type": "string"},
                "start_date": {"type": "string"},
                "end_date": {"type": "string"},
                "budget": {"type": "string"},
                "travelers": {"type": "string"}
            },
            "required": ["location", "start_date", "end_date", "budget", "travelers"]
        }
    }
]
