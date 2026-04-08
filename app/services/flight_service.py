from typing import Dict, Any, List

async def fetch_flights(origin: str, destination: str, dates: dict, budget: str) -> List[Dict[str, Any]]:
    """
    Service layer for fetching flights.
    Returns a list of 5 diverse flight options:
      - 3 'API-sourced' (Amadeus-style) entries
      - 2 'Local/Partner' curated entries
    When the client provides actual API keys, replace this with the real Amadeus SDK call.
    """

    # Budget multiplier
    multiplier = {"Budget": 0.7, "Moderate": 1.0, "Luxury": 1.6}.get(budget, 1.0)

    dest_lower = destination.lower()

    # Base price estimate per destination
    base_price = 450
    carrier = "AA"
    duration = "7h 30m"

    if "dubai" in dest_lower:
        base_price = 980; carrier = "EK"; duration = "13h 50m"
    elif "tokyo" in dest_lower or "japan" in dest_lower:
        base_price = 1200; carrier = "JL"; duration = "14h 20m"
    elif "paris" in dest_lower or "france" in dest_lower:
        base_price = 650; carrier = "AF"; duration = "7h 45m"
    elif "bali" in dest_lower or "indonesia" in dest_lower:
        base_price = 720; carrier = "GA"; duration = "12h 10m"
    elif "china" in dest_lower or "beijing" in dest_lower or "shanghai" in dest_lower:
        base_price = 900; carrier = "CA"; duration = "11h 30m"
    elif "india" in dest_lower or "delhi" in dest_lower or "mumbai" in dest_lower:
        base_price = 550; carrier = "AI"; duration = "9h 00m"
    elif "bangladesh" in dest_lower or "dhaka" in dest_lower:
        base_price = 380; carrier = "BG"; duration = "7h 00m"
    elif "thailand" in dest_lower or "bangkok" in dest_lower:
        base_price = 620; carrier = "TG"; duration = "11h 45m"

    p = round(base_price * multiplier)
    origin_upper = origin.upper()
    dest_title = destination.title()

    return [
        # --- 3 API-Sourced (Amadeus GDS style) ---
        {
            "source": "Amadeus GDS",
            "route": f"{origin_upper} → {dest_title}",
            "stops": "Non-stop",
            "duration": duration,
            "price_usd": p,
            "carrier_code": carrier,
            "loyalty_points_earned": round(p * 0.1),
            "baggage_policy": "1 carry-on + 1 checked bag (23kg)",
            "pnr_status": "OPEN",
            "image_url": "https://images.unsplash.com/photo-1436491865332-7a61a109cc05?w=800&q=80"
        },
        {
            "source": "Amadeus GDS",
            "route": f"{origin_upper} → {dest_title} (via Hub)",
            "stops": "1 stop",
            "duration": f"{int(duration.split('h')[0]) + 3}h 15m",
            "price_usd": round(p * 0.82),
            "carrier_code": "QR",
            "loyalty_points_earned": round(p * 0.08),
            "baggage_policy": "1 carry-on only (budget fare)",
            "pnr_status": "OPEN",
            "image_url": "https://images.unsplash.com/photo-1569629743817-70d8db6c323b?w=800&q=80"
        },
        {
            "source": "Amadeus GDS",
            "route": f"{origin_upper} → {dest_title}",
            "stops": "Non-stop",
            "duration": duration,
            "price_usd": round(p * 1.25),
            "carrier_code": "EY",
            "loyalty_points_earned": round(p * 0.15),
            "baggage_policy": "2 checked bags (32kg each) + lounge access",
            "pnr_status": "OPEN",
            "image_url": "https://images.unsplash.com/photo-1544620347-c4fd4a3d5957?w=800&q=80"
        },
        # --- 2 Local/Partner curated entries ---
        {
            "source": "Solara Partner Network",
            "route": f"{origin_upper} → {dest_title}",
            "stops": "Non-stop",
            "duration": duration,
            "price_usd": round(p * 0.92),
            "carrier_code": "PARTNER",
            "loyalty_points_earned": round(p * 0.12),
            "baggage_policy": "1 checked bag (20kg) included",
            "pnr_status": "GUARANTEED",
            "image_url": "https://images.unsplash.com/photo-1474302770737-173ee21bab63?w=800&q=80"
        },
        {
            "source": "Solara Exclusive Deal",
            "route": f"{origin_upper} → {dest_title}",
            "stops": "1 stop",
            "duration": f"{int(duration.split('h')[0]) + 2}h 00m",
            "price_usd": round(p * 0.75),
            "carrier_code": "DEAL",
            "loyalty_points_earned": round(p * 0.05),
            "baggage_policy": "Carry-on only — checked bag +$30",
            "pnr_status": "LIMITED SEATS",
            "image_url": "https://images.unsplash.com/photo-1500835556837-99ac94a94552?w=800&q=80"
        },
    ]
