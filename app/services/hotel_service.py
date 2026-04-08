from typing import Dict, Any, List
from datetime import datetime


async def fetch_hotels(destination: str, dates: dict, budget: str, travelers: str) -> List[Dict[str, Any]]:
    """
    Service layer for fetching hotels.
    Returns a list of 5 diverse hotel options:
      - 3 'API-sourced' (Amadeus/Booking.com style) entries
      - 2 'Local/Partner' curated entries
    When the client provides actual API keys, replace with real SDK call.
    """

    nights = _night_count(dates)
    dest_title = destination.title()
    dest_lower = destination.lower()

    # Base price per budget
    base_price = {"Budget": 70, "Moderate": 150, "Luxury": 450}.get(budget, 150)
    if "dubai" in dest_lower and budget == "Luxury":
        base_price = 1200
    elif "bali" in dest_lower:
        base_price = {"Budget": 55, "Moderate": 130, "Luxury": 380}.get(budget, 130)

    # Amenity sets
    budget_amenities = ["Free WiFi", "24h Reception"]
    moderate_amenities = ["Free WiFi", "Pool", "Gym", "Breakfast"]
    luxury_amenities = ["Free WiFi", "Pool", "Spa", "Butler Service", "Private Beach Access", "Rooftop Bar"]
    amenities = {"Budget": budget_amenities, "Moderate": moderate_amenities, "Luxury": luxury_amenities}.get(budget, moderate_amenities)
    amenity_icons = {"Budget": ["wifi", "reception_bell"], "Moderate": ["wifi", "pool", "fitness_center", "free_breakfast"], "Luxury": ["wifi", "pool", "spa", "room_service", "beach_access", "rooftop"]}.get(budget, ["wifi", "pool"])

    p = base_price

    return [
        # --- 3 API-Sourced ---
        {
            "source": "Amadeus Hotel API",
            "name": f"Grand Hyatt {dest_title}",
            "nights": nights,
            "rating": 4.7,
            "price_per_night_usd": p,
            "amenities": amenities,
            "review_count": 1240,
            "tripadvisor_rating": 4.6,
            "cancellation_policy": "Free cancellation up to 72 hours before check-in.",
            "check_in_instructions": "Check-in from 3:00 PM. Photo ID and credit card required at front desk.",
            "amenities_icons": amenity_icons,
            "image_url": "https://images.unsplash.com/photo-1566073771259-6a8506099945?w=800&q=80"
        },
        {
            "source": "Amadeus Hotel API",
            "name": f"Marriott {dest_title} City Centre",
            "nights": nights,
            "rating": 4.5,
            "price_per_night_usd": round(p * 0.9),
            "amenities": amenities,
            "review_count": 2300,
            "tripadvisor_rating": 4.4,
            "cancellation_policy": "Free cancellation up to 48 hours before check-in.",
            "check_in_instructions": "Check-in from 2:00 PM. Early check-in available on request.",
            "amenities_icons": amenity_icons,
            "image_url": "https://images.unsplash.com/photo-1551882547-ff40c63fe2fa?w=800&q=80"
        },
        {
            "source": "Booking.com API",
            "name": f"Hilton {dest_title}",
            "nights": nights,
            "rating": 4.6,
            "price_per_night_usd": round(p * 1.15),
            "amenities": amenities + ["Airport Shuttle"],
            "review_count": 980,
            "tripadvisor_rating": 4.7,
            "cancellation_policy": "Non-refundable — special rate.",
            "check_in_instructions": "Check-in from 4:00 PM. Concierge available 24/7.",
            "amenities_icons": amenity_icons + ["airport_shuttle"],
            "image_url": "https://images.unsplash.com/photo-1542314831-068cd1dbfeeb?w=800&q=80"
        },
        # --- 2 Local/Partner entries ---
        {
            "source": "Solara Partner Stay",
            "name": f"Boutique Nest {dest_title}",
            "nights": nights,
            "rating": 4.8,
            "price_per_night_usd": round(p * 0.8),
            "amenities": amenities + ["Rooftop Terrace", "Local Guided Tours"],
            "review_count": 450,
            "tripadvisor_rating": 4.9,
            "cancellation_policy": "Free cancellation up to 24 hours before check-in.",
            "check_in_instructions": "Self check-in via smart lock. Code sent 2 hours before arrival.",
            "amenities_icons": amenity_icons + ["rooftop", "tour"],
            "image_url": "https://images.unsplash.com/photo-1520250497591-112f2f40a3f4?w=800&q=80"
        },
        {
            "source": "Solara Exclusive Deal",
            "name": f"Heritage Inn {dest_title}",
            "nights": nights,
            "rating": 4.3,
            "price_per_night_usd": round(p * 0.65),
            "amenities": budget_amenities + ["Cultural Activities"],
            "review_count": 3100,
            "tripadvisor_rating": 4.2,
            "cancellation_policy": "Free cancellation up to 72 hours before check-in.",
            "check_in_instructions": "Check-in from 1:00 PM. Passport required at arrival.",
            "amenities_icons": ["wifi", "cultural_activity"],
            "image_url": "https://images.unsplash.com/photo-1578683010236-d716f9a3f461?w=800&q=80"
        },
    ]


def _night_count(dates: dict) -> int:
    try:
        start = datetime.strptime(dates.get("start", ""), "%Y-%m-%d")
        end = datetime.strptime(dates.get("end", ""), "%Y-%m-%d")
        return max((end - start).days, 1)
    except Exception:
        return 5
