from enum import Enum
from typing import Optional, List
from pydantic import BaseModel


class TravelersEnum(str, Enum):
    solo = "Solo"
    couple = "Couple"
    family = "Family"


class BudgetEnum(str, Enum):
    budget = "Budget"
    moderate = "Moderate"
    luxury = "Luxury"


class ExperienceEnum(str, Enum):
    relaxation = "Relaxation"
    adventure = "Adventure"
    shopping = "Shopping"
    culture = "Culture"
    mix = "Mix of everything"

class SafetyLevelEnum(str, Enum):
    very_high = "Very High"
    high = "High"
    moderate = "Moderate"
    low = "Low"
    very_low = "Very Low"


class PassengerDetail(BaseModel):
    name: str
    passport: str


class ExtractedParameters(BaseModel):
    location: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    travelers: Optional[TravelersEnum] = None
    budget: Optional[BudgetEnum] = None
    experience: Optional[ExperienceEnum] = None
    citizenship: Optional[str] = None
    passengers: Optional[List[PassengerDetail]] = None
    passenger_preferences: Optional[str] = None


class TripCard(BaseModel):
    destination: str
    description: str
    rating: float
    distance_km: int
    restaurants_available: int
    total_price_per_person: int
    points_applied: Optional[int] = 0
    parameters_extracted: ExtractedParameters


class FlightInfo(BaseModel):
    route: str
    stops: str
    duration: str
    price_usd: Optional[float] = None
    carrier_code: Optional[str] = None
    loyalty_points_earned: Optional[int] = None
    baggage_policy: Optional[str] = None
    pnr_status: Optional[str] = None
    image_url: Optional[str] = None


class HotelInfo(BaseModel):
    name: str
    nights: int
    rating: float
    price_per_night_usd: Optional[float] = None
    amenities: Optional[List[str]] = None
    review_count: Optional[int] = None
    tripadvisor_rating: Optional[float] = None
    cancellation_policy: Optional[str] = None
    check_in_instructions: Optional[str] = None
    amenities_icons: Optional[List[str]] = None
    image_url: Optional[str] = None


class WeatherInfo(BaseModel):
    date: str
    condition: str
    temperature_celsius: int


class SafetyInfo(BaseModel):
    safety_level: SafetyLevelEnum
    tips: List[str]
    restrictions: List[str]


class TripGuide(BaseModel):
    flight: Optional[FlightInfo] = None
    hotel: Optional[HotelInfo] = None
    flight_options: Optional[List[FlightInfo]] = []
    hotel_options: Optional[List[HotelInfo]] = []
    weather: Optional[WeatherInfo] = None
    travel_tips: Optional[List[str]] =[]
    culture_etiquette: Optional[List[str]] = []
    safety_info: Optional[SafetyInfo] = None
    visa_status: Optional[str] = None
    base_price: Optional[float] = 0.0
    points_discount: Optional[float] = 0.0
    final_estimated_total: Optional[float] = 0.0


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    message: str
    session_id: str
    user_id: Optional[str] = None
    subscription_plan: str = "free"


class ChatResponse(BaseModel):
    session_id: str
    user_id: Optional[str] = None
    ai_message: str
    current_step: Optional[str] = None
    parameters_extracted: Optional[ExtractedParameters] = None
    trip_card: Optional[TripCard] = None
    trip_guide: Optional[TripGuide] = None
    submitted: bool = False
    checkout_required: bool = False


class DatesDict(BaseModel):
    start: str
    end: str

class FlightSearchRequest(BaseModel):
    origin: str
    destination: str
    dates: DatesDict
    budget: str

class HotelSearchRequest(BaseModel):
    destination: str
    dates: DatesDict
    budget: str
    travelers: str
