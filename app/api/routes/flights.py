from fastapi import APIRouter, HTTPException
from app.schemas import FlightSearchRequest, FlightInfo
from app.services.flight_service import fetch_flights

router = APIRouter()

@router.post("/search", response_model=FlightInfo)
async def search_flights_endpoint(request: FlightSearchRequest):
    try:
        # Pydantic validates input. We pass it directly to the service.
        result = await fetch_flights(
            origin=request.origin,
            destination=request.destination,
            dates=request.dates.model_dump(),
            budget=request.budget
        )
        return FlightInfo(**result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
