from fastapi import APIRouter, HTTPException
from app.schemas import HotelSearchRequest, HotelInfo
from app.services.hotel_service import fetch_hotels

router = APIRouter()

@router.post("/search", response_model=HotelInfo)
async def search_hotels_endpoint(request: HotelSearchRequest):
    try:
        # Pydantic validates input. We pass it directly to the service.
        result = await fetch_hotels(
            destination=request.destination,
            dates=request.dates.model_dump(),
            budget=request.budget,
            travelers=request.travelers
        )
        return HotelInfo(**result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
