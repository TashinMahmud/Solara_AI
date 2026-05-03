from fastapi import APIRouter
from app.api.routes.chat import router as chat_router
from app.api.routes.flights import router as flights_router
from app.api.routes.hotels import router as hotels_router
api_router = APIRouter()
api_router.include_router(chat_router, prefix="/api/v1", tags=["chat"])
api_router.include_router(flights_router, prefix="/api/v1/flights", tags=["flights"])
api_router.include_router(hotels_router, prefix="/api/v1/hotels", tags=["hotels"])
