from pydantic import BaseModel, Field
from typing import List, Optional

class Question(BaseModel):
    question: str
    key: str

class ChatRequest(BaseModel):
    user_id: str = Field(examples=["user123"])
    session_id: str = Field(examples=["session123"])
    message: str = Field(examples=["I want to book travel to Maldives"])

class DestinationCard(BaseModel):
    name: str
    image_url: str
    rating: float
    reviews_count: int
    price_from: str
    duration: str
    highlights: List[str] = []

class HotelCard(BaseModel):
    name: str
    image_url: str
    rating: float
    reviews_count: int
    price_per_night: str
    amenities: List[str] = []

class PackageCard(BaseModel):
    name: str
    price: str
    duration: str
    rating: float
    highlights: List[str] = []

class FollowUpQuestion(BaseModel):
    question: str
    suggestions: List[str] = []

class ChatResponse(BaseModel):
    answer: str
    conversational_text: Optional[str] = None
    destinations: List[DestinationCard] = []
    hotels: List[HotelCard] = []
    packages: List[PackageCard] = []
    follow_up_questions: List[FollowUpQuestion] = []
    plan_generated: bool = False
    plan_summary: Optional[str] = None