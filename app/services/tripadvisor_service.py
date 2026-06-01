import httpx
import logging
import asyncio
from typing import List, Dict, Any
from app.core.config import settings

logger = logging.getLogger("solara.tripadvisor")

BASE_URL = "https://api.content.tripadvisor.com/api/v1"

# In-memory fallbacks for offline development/fallback purposes
FALLBACK_DATA = {
    "tokyo": {
        "attractions": [
            {
                "location_id": "320053",
                "name": "Sensō-ji Temple",
                "rating": 4.5,
                "num_reviews": 15240,
                "address": "2-3-1 Asakusa, Taito, Tokyo 111-0032",
                "category": "Attraction",
                "web_url": "https://www.tripadvisor.com/Attraction_Review-g14135437-d320053-Reviews-Senso_ji_Temple-Asakusa_Taito_Tokyo_Tokyo_Prefecture_Kanto.html",
                "photo_url": "https://images.unsplash.com/photo-1542051841857-5f90071e7989?w=800&q=80"
            },
            {
                "location_id": "2623190",
                "name": "Tokyo Skytree",
                "rating": 4.5,
                "num_reviews": 8940,
                "address": "1-1-2 Oshiage, Sumida, Tokyo 131-0045",
                "category": "Attraction",
                "web_url": "https://www.tripadvisor.com/Attraction_Review-g1066459-d2623190-Reviews-Tokyo_Skytree-Sumida_Tokyo_Tokyo_Prefecture_Kanto.html",
                "photo_url": "https://images.unsplash.com/photo-1503899036084-c55cdd92da26?w=800&q=80"
            },
            {
                "location_id": "1239088",
                "name": "Meiji Jingu Shrine",
                "rating": 4.5,
                "num_reviews": 11020,
                "address": "1-1 Yoyogikamizonocho, Shibuya, Tokyo 151-8557",
                "category": "Attraction",
                "web_url": "https://www.tripadvisor.com/Attraction_Review-g1066456-d320052-Reviews-Meiji_Jingu_Shrine-Shibuya_Tokyo_Tokyo_Prefecture_Kanto.html",
                "photo_url": "https://images.unsplash.com/photo-1582769926462-2b3644f10822?w=800&q=80"
            }
        ],
        "restaurants": [
            {
                "location_id": "1697232",
                "name": "Sukiyabashi Jiro",
                "rating": 4.0,
                "num_reviews": 320,
                "address": "4-2-15 Ginza, Chuo, Tokyo 104-0061",
                "category": "Restaurant",
                "web_url": "https://www.tripadvisor.com/Restaurant_Review-g1066444-d1697232-Reviews-Sukiyabashi_Jiro_Honten-Chuo_Tokyo_Tokyo_Prefecture_Kanto.html",
                "photo_url": "https://images.unsplash.com/photo-1579871494447-9811cf80d66c?w=800&q=80"
            },
            {
                "location_id": "6732910",
                "name": "Ichiran Shibuya",
                "rating": 4.5,
                "num_reviews": 2450,
                "address": "1-22-7 Jinnan, Shibuya, Tokyo 150-0041",
                "category": "Restaurant",
                "web_url": "https://www.tripadvisor.com/Restaurant_Review-g1066456-d6732910-Reviews-Ichiran_Shibuya-Shibuya_Tokyo_Tokyo_Prefecture_Kanto.html",
                "photo_url": "https://images.unsplash.com/photo-1569718212165-3a8278d5f624?w=800&q=80"
            }
        ]
    },
    "paris": {
        "attractions": [
            {
                "location_id": "188151",
                "name": "Eiffel Tower",
                "rating": 4.5,
                "num_reviews": 140230,
                "address": "Champ de Mars, 75007 Paris, France",
                "category": "Attraction",
                "web_url": "https://www.tripadvisor.com/Attraction_Review-g187147-d188151-Reviews-Eiffel_Tower-Paris_Ile_de_France.html",
                "photo_url": "https://images.unsplash.com/photo-1502602898657-3e91760cbb34?w=800&q=80"
            },
            {
                "location_id": "188757",
                "name": "Louvre Museum",
                "rating": 4.5,
                "num_reviews": 98450,
                "address": "Rue de Rivoli, 75001 Paris, France",
                "category": "Attraction",
                "web_url": "https://www.tripadvisor.com/Attraction_Review-g187147-d188757-Reviews-Louvre_Museum-Paris_Ile_de_France.html",
                "photo_url": "https://images.unsplash.com/photo-1597910037310-7dd8ddb93e24?w=800&q=80"
            }
        ],
        "restaurants": [
            {
                "location_id": "733908",
                "name": "Le Jules Verne",
                "rating": 4.5,
                "num_reviews": 2980,
                "address": "Eiffel Tower, 2nd Floor, 75007 Paris, France",
                "category": "Restaurant",
                "web_url": "https://www.tripadvisor.com/Restaurant_Review-g187147-d733908-Reviews-Le_Jules_Verne-Paris_Ile_de_France.html",
                "photo_url": "https://images.unsplash.com/photo-1550966871-3ed3cdb5ed0c?w=800&q=80"
            }
        ]
    }
}

async def fetch_tripadvisor_poi(location: str, category: str) -> List[Dict[str, Any]]:
    """
    Exclusively queries the live TripAdvisor Content API (Search, Details, Photos)
    using the configured API key. Falls back to static details if key is missing or calls fail.
    """
    api_key = settings.tripadvisor_api_key
    
    # Check if API Key is completely missing or is the placeholder string
    if not api_key or "your_tripadvisor_api_key" in api_key.lower():
        logger.warning("TripAdvisor API Key is missing or placeholder. Returning mock fallback.")
        return _get_fallback_data(location, category)

    headers = {
        "Accept": "application/json"
    }
    
    query = f"{category} in {location}"
    logger.info(f"Querying live TripAdvisor Search API for: '{query}' ({category})")
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            # 1. Search for matching locations
            search_params = {
                "key": api_key,
                "searchQuery": query,
                "category": category,
                "language": "en"
            }
            
            search_url = f"{BASE_URL}/location/search"
            res = await client.get(search_url, params=search_params, headers=headers)
            
            if res.status_code != 200:
                logger.error(f"TripAdvisor Search API returned status {res.status_code}: {res.text}")
                return _get_fallback_data(location, category)
                
            search_results = res.json().get("data", [])
            if not search_results:
                logger.warning(f"No results found for '{query}' on TripAdvisor.")
                return _get_fallback_data(location, category)
            
            # Limit to top 3 POIs
            top_pois = search_results[:3]
            
            # 2. Gather details and photos concurrently for the top POIs
            tasks = []
            for poi in top_pois:
                location_id = poi.get("location_id")
                if location_id:
                    tasks.append(_fetch_poi_details_and_photos(client, location_id, api_key, headers))
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            poi_list = []
            for idx, r in enumerate(results):
                if isinstance(r, Exception):
                    logger.error(f"Error fetching details/photos for POI index {idx}: {r}")
                    continue
                if r:
                    poi_list.append(r)
            
            if poi_list:
                return poi_list
            else:
                logger.warning("Failed to gather details for any POIs. Returning fallback.")
                return _get_fallback_data(location, category)

    except Exception as e:
        logger.error(f"TripAdvisor API exception: {type(e).__name__}: {e}")
        return _get_fallback_data(location, category)

async def _fetch_poi_details_and_photos(client: httpx.AsyncClient, location_id: str, api_key: str, headers: dict) -> Dict[str, Any]:
    """
    Fetches details and photos for a specific location_id in parallel.
    """
    params = {"key": api_key, "language": "en"}
    
    details_url = f"{BASE_URL}/location/{location_id}/details"
    photos_url = f"{BASE_URL}/location/{location_id}/photos"
    
    # Run details and photos requests in parallel
    details_res, photos_res = await asyncio.gather(
        client.get(details_url, params=params, headers=headers),
        client.get(photos_url, params=params, headers=headers),
        return_exceptions=True
    )
    
    # Check details result
    if isinstance(details_res, Exception) or details_res.status_code != 200:
        err_msg = details_res if isinstance(details_res, Exception) else f"Status {details_res.status_code}"
        logger.error(f"Failed to fetch details for location_id {location_id}: {err_msg}")
        return None
        
    details_data = details_res.json()
    
    # Parse photos url if success
    photo_url = None
    if not isinstance(photos_res, Exception) and photos_res.status_code == 200:
        try:
            photos_data = photos_res.json().get("data", [])
            if photos_data:
                # Retrieve medium or original image size
                images_obj = photos_data[0].get("images", {})
                medium_img = images_obj.get("medium") or images_obj.get("large") or images_obj.get("original")
                if medium_img:
                    photo_url = medium_img.get("url")
        except Exception as pe:
            logger.warning(f"Error parsing photos for location_id {location_id}: {pe}")
            
    # Default fallback image if none returned from API
    if not photo_url:
        photo_url = "https://images.unsplash.com/photo-1469854523086-cc02fe5d8800?w=800&q=80"
        
    address_obj = details_data.get("address_obj", {})
    address_str = address_obj.get("address_string") or address_obj.get("street1") or ""
    
    rating_val = details_data.get("rating")
    try:
        rating = float(rating_val) if rating_val is not None else None
    except ValueError:
        rating = None
        
    num_revs_val = details_data.get("num_reviews")
    try:
        num_reviews = int(num_revs_val) if num_revs_val is not None else None
    except ValueError:
        num_reviews = None
        
    return {
        "location_id": str(location_id),
        "name": details_data.get("name", "Unknown Landmark"),
        "rating": rating,
        "num_reviews": num_reviews,
        "address": address_str,
        "category": details_data.get("category", {}).get("name") or details_data.get("category", {}).get("localized_name"),
        "web_url": details_data.get("web_url"),
        "photo_url": photo_url
    }

def _get_fallback_data(location: str, category: str) -> List[Dict[str, Any]]:
    """
    Gets matching in-memory fallback items for the specified location and category.
    """
    loc_key = location.lower()
    
    # Try finding exact city matches in fallbacks
    for key in FALLBACK_DATA:
        if key in loc_key:
            return FALLBACK_DATA[key].get(category, [])
            
    # Generic default fallback list if destination not listed above
    if category == "attractions":
        return [
            {
                "location_id": "0001",
                "name": f"Historic Center of {location.title()}",
                "rating": 4.6,
                "num_reviews": 1240,
                "address": f"Downtown {location.title()}",
                "category": "Historic Area",
                "web_url": "https://www.tripadvisor.com",
                "photo_url": "https://images.unsplash.com/photo-1447752875215-b2761acb3c5d?w=800&q=80"
            },
            {
                "location_id": "0002",
                "name": f"City Park & Gardens of {location.title()}",
                "rating": 4.5,
                "num_reviews": 850,
                "address": f"Green Lane, {location.title()}",
                "category": "Park",
                "web_url": "https://www.tripadvisor.com",
                "photo_url": "https://images.unsplash.com/photo-1473448912268-2022ce9509d8?w=800&q=80"
            }
        ]
    else:  # restaurants
        return [
            {
                "location_id": "0003",
                "name": f"The Local Bistro {location.title()}",
                "rating": 4.7,
                "num_reviews": 512,
                "address": f"Food Street, {location.title()}",
                "category": "Restaurant / Cafe",
                "web_url": "https://www.tripadvisor.com",
                "photo_url": "https://images.unsplash.com/photo-1552566626-52f8b828add9?w=800&q=80"
            }
        ]
