import httpx
from app.core.config import settings
from typing import Optional, Dict, Any

from app.services.flight_service import fetch_flights
from app.services.hotel_service import fetch_hotels

MOCK_MODE = settings.app_env == "development"


async def search_flights(origin: str, destination: str, dates: dict, budget: str) -> dict:
    if MOCK_MODE:
        return await fetch_flights(
            origin=origin,
            destination=destination,
            dates=dates,
            budget=budget,
        )
    
    async with httpx.AsyncClient(timeout=15.0) as client:
        res = await client.post(
            f"{settings.internal_api_flights}",
            json={
                "origin": origin,
                "destination": destination,
                "dates": dates,
                "budget": budget
            }
        )
        res.raise_for_status()
        return res.json()


async def search_hotels(destination: str, dates: dict, budget: str, travelers: str) -> dict:
    if MOCK_MODE:
        return await fetch_hotels(
            destination=destination,
            dates=dates,
            budget=budget,
            travelers=travelers,
        )

    async with httpx.AsyncClient(timeout=15.0) as client:
        res = await client.post(
            f"{settings.internal_api_hotels}",
            json={
                "destination": destination,
                "dates": dates,
                "budget": budget,
                "travelers": travelers
            }
        )
        res.raise_for_status()
        return res.json()


async def submit_trip_to_backend(
    location: str,
    start_date: str,
    end_date: str,
    travelers: str,
    budget: str,
    experience: str,
    flight_details: Optional[Dict[str, Any]] = None,
    hotel_details: Optional[Dict[str, Any]] = None,
    subscription_plan: Optional[str] = "free",
    user_id: Optional[str] = None,
    passengers: Optional[list] = None,
    points_applied: Optional[int] = 0,
) -> dict:
    payload = {
        "subscription_plan": subscription_plan,
        "user_id": user_id,
        "location": location,
        "start_date": start_date,
        "end_date": end_date,
        "travelers": travelers,
        "budget": budget,
        "experience": experience,
        "flight_details": flight_details,
        "hotel_details": hotel_details,
        "passengers": passengers,
        "points_applied": points_applied,
    }

    if MOCK_MODE:
        print(f"[mock] submit_trip_to_backend payload: {payload}")
        return {"status": "received", "payload": payload}

    async with httpx.AsyncClient(timeout=15.0) as client:
        res = await client.post(settings.internal_api_submit, json=payload)
        res.raise_for_status()
        return res.json()

async def check_cancellation_eligibility(trip_id: str) -> dict:
    """
    Checks if a trip is eligible for cancellation and refund.
    In production: calls the backend team's cancellation eligibility API.
    """
    if MOCK_MODE:
        print(f"[mock] check_cancellation_eligibility: trip_id={trip_id}")
        return {
            "eligible": True,
            "refund_amount_credits": 1000,
            "days_valid": 30
        }

    async with httpx.AsyncClient(timeout=15.0) as client:
        res = await client.post(
            f"{settings.internal_api_cancellation}/eligibility",
            json={"trip_id": trip_id}
        )
        res.raise_for_status()
        return res.json()

async def search_flexible_alternatives(location: str, start_date: str, end_date: str, budget: str, travelers: str) -> dict:
    """
    Searches for cheaper travel alternatives when prices exceed the user's budget.
    In production: calls the backend team's flexible search API.
    """
    if MOCK_MODE:
        print(f"[mock] search_flexible_alternatives: location={location}")
        return {
            "alternative_found": True,
            "suggested_location": location,
            "suggested_dates": {"start": "2026-10-12", "end": "2026-10-17"},
            "original_price": 1200,
            "new_price": 850
        }

    async with httpx.AsyncClient(timeout=15.0) as client:
        res = await client.post(
            f"{settings.internal_api_flights}/flexible",
            json={
                "location": location,
                "start_date": start_date,
                "end_date": end_date,
                "budget": budget,
                "travelers": travelers
            }
        )
        res.raise_for_status()
        return res.json()


async def confirm_cancellation(trip_id: str, subscription_plan: str = "free") -> dict:
    """
    Finalizes the cancellation after user confirms.
    In production: calls the backend team's cancellation API to mark
    the booking as cancelled and issue refund credits.
    """
    if MOCK_MODE:
        print(f"[mock] confirm_cancellation: trip_id={trip_id}, subscription_plan={subscription_plan}")
        return {
            "status": "cancelled",
            "refund_credits_issued": 1000,
            "refund_delivery": "2-3 business days",
            "booking_status": "CANCELLED"
        }

    async with httpx.AsyncClient(timeout=15.0) as client:
        res = await client.post(
            f"{settings.internal_api_submit}/cancel",
            json={"trip_id": trip_id, "subscription_plan": subscription_plan}
        )
        res.raise_for_status()
        return res.json()


async def get_user_points(user_id: str) -> dict:
    """
    Returns the user's current loyalty points balance, expiry info, and tier rates.
    In production: calls the backend team's loyalty API.
    """
    if MOCK_MODE:
        print(f"[mock] get_user_points: user_id={user_id}")
        return {"points": 1200, "expiring_soon": True, "expiry_days": 15, "earning_rate": "2%", "expiry_window": "365 days"}

    async with httpx.AsyncClient(timeout=15.0) as client:
        res = await client.get(
            f"{settings.internal_api_loyalty}/points",
            params={"user_id": user_id}
        )
        res.raise_for_status()
        return res.json()


async def apply_points_to_quote(base_price: float, points_to_use: int) -> dict:
    """
    Calculates a price discount based on loyalty points.
    In production: calls the backend team's pricing API for server-validated discount.
    """
    if MOCK_MODE:
        print(f"[mock] apply_points_to_quote: base_price={base_price}, points={points_to_use}")
        discount = (points_to_use / 100) * 10
        final_total = max(0, base_price - discount)
        return {
            "base_price": base_price,
            "points_discount": round(discount, 2),
            "final_estimated_total": round(final_total, 2)
        }

    async with httpx.AsyncClient(timeout=15.0) as client:
        res = await client.post(
            f"{settings.internal_api_pricing}/apply-points",
            json={"base_price": base_price, "points_to_use": points_to_use}
        )
        res.raise_for_status()
        return res.json()



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
                "passengers": {
                    "type": "array",
                    "description": "List of passenger details collected through chat.",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "passport": {"type": "string"}
                        },
                        "required": ["name", "passport"]
                    }
                },
                "points_applied": {"type": "integer", "description": "Number of loyalty points the user agreed to apply."},
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
    },
    {
        "name": "confirm_cancellation",
        "description": (
            "Call this ONLY after check_cancellation_eligibility returned eligible=true AND the user explicitly "
            "confirmed they want to proceed with the cancellation. This finalizes the cancellation and issues refund credits."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "trip_id": {"type": "string", "description": "The ID or description of the trip being cancelled."}
            },
            "required": ["trip_id"]
        }
    },
    {
        "name": "get_user_points",
        "description": (
            "Retrieves the user's current loyalty points balance and expiry status. "
            "Call this at the start of a session to check if the user has points, and whether any are expiring soon."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "user_id": {"type": "string", "description": "The authenticated user's ID."}
            },
            "required": ["user_id"]
        }
    },
    {
        "name": "apply_points_to_quote",
        "description": (
            "Calculates a live price estimate after applying loyalty points to a trip quote. "
            "Returns base_price, points_discount, and final_estimated_total."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "base_price": {"type": "number", "description": "The total trip price (flight + hotel) before any discount."},
                "points_to_use": {"type": "integer", "description": "The number of loyalty points the user wants to apply."}
            },
            "required": ["base_price", "points_to_use"]
        }
    }
]
