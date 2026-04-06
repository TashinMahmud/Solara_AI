from typing import Dict, Any
from datetime import datetime

async def fetch_hotels(destination: str, dates: dict, budget: str, travelers: str) -> dict:
    """
    Service layer for fetching hotels.
    When the client provides actual API keys (e.g., Booking.com / SERP API), 
    replace this mock logic with the real HTTP request/SDK call.
    """
    
    # ---------------------------------------------------------
    # TODO: Real Implementation Placeholder (Amadeus API)
    # ---------------------------------------------------------
    # API: GET https://test.api.amadeus.com/v1/reference-data/locations/hotels/by-city
    # response = httpx.get("...", headers={"Authorization": "Bearer YOUR_KEY"})
    # return _format_booking_response(response, budget)
    # ---------------------------------------------------------

    nights = _night_count(dates)
    price_per_night = 150
    hotel_name = f"Grand Hyatt {destination.title()}"
    rating = 4.7
    amenities = ["Free WiFi", "Pool", "Gym"]
    review_count = 1200
    tripadvisor_rating = 4.5

    dest_lower = destination.lower()
    if budget == "Luxury":
        price_per_night = 450
        hotel_name = f"The Ritz-Carlton, {destination.title()}"
        rating = 4.9
        amenities = ["Spa", "Private Beach", "Butler Service", "Free WiFi", "Pool"]
        review_count = 850
        tripadvisor_rating = 5.0
    elif budget == "Budget":
        price_per_night = 80
        hotel_name = f"Holiday Inn {destination.title()}"
        rating = 4.2
        amenities = ["Free WiFi", "Breakfast Included"]
        review_count = 3400
        tripadvisor_rating = 4.0

    if "dubai" in dest_lower and budget == "Luxury":
        hotel_name = "Burj Al Arab"
        price_per_night = 1200
        rating = 5.0
    elif "bali" in dest_lower:
        hotel_name = "Nusa Penida Resort & Spa" if budget != "Budget" else "Bali Backpacker Hostel"

    return {
        "name": hotel_name,
        "nights": nights,
        "rating": rating,
        "price_per_night_usd": price_per_night,
        "amenities": amenities,
        "review_count": review_count,
        "tripadvisor_rating": tripadvisor_rating
    }

def _night_count(dates: dict) -> int:
    try:
        start = datetime.strptime(dates.get("start", ""), "%Y-%m-%d")
        end = datetime.strptime(dates.get("end", ""), "%Y-%m-%d")
        return max((end - start).days, 1)
    except Exception:
        return 5
