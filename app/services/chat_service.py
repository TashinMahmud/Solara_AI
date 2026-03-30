from sqlalchemy.orm import Session
from app.model.models import User, Session as DBSession, Message, Plan
from app.schemas.chat import (
    ChatRequest, ChatResponse, Question, 
    DestinationCard, HotelCard, PackageCard, FollowUpQuestion
)
from typing import Dict, List
import json
import re
from anthropic import Anthropic
from app.core.config import settings

class ChatService:
    def __init__(self):
        self.client = Anthropic(api_key=settings.claude_api_key)
        self.flow = [
            {"key": "purpose", "question": "Where would you like to travel?", "required": True},
            {"key": "date", "question": "When are you thinking of heading out?", "required": True},
            {"key": "guests", "question": "Who's coming along for the ride?", "required": False},
            {"key": "budget", "question": "What's your budget for this adventure?", "required": False},
        ]

        self.destination_data = {
            "maldives": {
                "destinations": [
                    {"name": "Male City", "image": "https://images.unsplash.com/photo-1512453333734-c86a0d7c7a6f", "price": "$1,200", "rating": 4.9, "duration": "3 days"},
                    {"name": "Baa Atoll", "image": "https://images.unsplash.com/photo-1507525428034-b723cf961d3e", "price": "$2,400", "rating": 4.8, "duration": "5 days"},
                    {"name": "North Male Atoll", "image": "https://images.unsplash.com/photo-1551632786-de41ec16a41d", "price": "$1,800", "rating": 4.9, "duration": "4 days"},
                    {"name": "South Male Atoll", "image": "https://images.unsplash.com/photo-1559827260-dc66d52bef19", "price": "$2,100", "rating": 4.7, "duration": "4 days"},
                ],
                "hotels": [
                    {"name": "Ocean Breeze Resort", "rating": 4.9, "price": "$400/night", "amenities": ["Beach access", "Spa", "Water sports"]},
                    {"name": "Coral Reef Villas", "rating": 4.8, "price": "$350/night", "amenities": ["Snorkeling", "Diving", "Restaurant"]},
                    {"name": "Sunset Overwater Bungalows", "rating": 4.7, "price": "$500/night", "amenities": ["Private pool", "Butler service", "Infinity deck"]},
                ],
                "packages": [
                    {"name": "7-Day Island Escape", "price": "$2,800", "rating": 4.9, "highlights": ["Snorkeling", "Island hopping", "Sunset cruise"]},
                    {"name": "5-Day Luxury Resort Tour", "price": "$3,300", "rating": 4.8, "highlights": ["Spa treatment", "Fine dining", "Water activities"]},
                    {"name": "Adventure + Snorkel Package", "price": "$2,200", "rating": 4.7, "highlights": ["Diving lessons", "Local culture", "Beach relaxation"]},
                ]
            },
            "dubai": {
                "destinations": [
                    {"name": "Dubai Marina", "image": "https://images.unsplash.com/photo-1518684029980-422177f9f7f0", "price": "$1,500", "rating": 4.8, "duration": "3 days"},
                    {"name": "Downtown Dubai", "image": "https://images.unsplash.com/photo-1512455520664-37a23a0fb0b8", "price": "$1,300", "rating": 4.7, "duration": "3 days"},
                    {"name": "Palm Jumeirah", "image": "https://images.unsplash.com/photo-1509316785289-025f5b846b35", "price": "$2,000", "rating": 4.9, "duration": "4 days"},
                ],
                "hotels": [
                    {"name": "Burj Al Arab", "rating": 5.0, "price": "$1,500/night", "amenities": ["Private beach", "Michelin-star dining", "Concierge"]},
                    {"name": "Emirates Towers", "rating": 4.8, "price": "$600/night", "amenities": ["Gym", "Pool", "Business center"]},
                    {"name": "JW Marriott", "rating": 4.7, "price": "$400/night", "amenities": ["Spa", "Beach club", "Fine dining"]},
                ],
                "packages": [
                    {"name": "5-Day Dubai Luxury", "price": "$2,500", "rating": 4.9, "highlights": ["Desert safari", "Burj Khalifa", "Shopping"]},
                    {"name": "3-Day City Explorer", "price": "$1,500", "rating": 4.8, "highlights": ["City tours", "Beach time", "Mall visit"]},
                    {"name": "Weekend Getaway", "price": "$1,200", "rating": 4.7, "highlights": ["Relaxation", "Local food", "Marina walk"]},
                ]
            }
        }

    def process_message(self, db: Session, request: ChatRequest) -> ChatResponse:
        user = db.query(User).filter(User.id == request.user_id).first()
        if not user:
            user = User(id=request.user_id)
            db.add(user)
            db.commit()

        session = db.query(DBSession).filter(DBSession.id == request.session_id).first()
        if not session:
            session = DBSession(id=request.session_id, user_id=request.user_id)
            db.add(session)
            db.commit()

        user_message = Message(session_id=request.session_id, content=request.message, is_bot=False)
        db.add(user_message)
        db.commit()

        messages = db.query(Message).filter(Message.session_id == request.session_id).order_by(Message.created_at).all()
        history = {msg.content for msg in messages if not msg.is_bot}

        collected_info = self.extract_info(history)
        next_questions = self.get_next_questions(collected_info)

        plan_generated = False
        plan_summary = None
        destinations = []
        hotels = []
        packages = []
        follow_ups = []

        if self.can_generate_plan(collected_info):
            response = self.generate_full_tour_response(collected_info)
            answer = response["conversational_text"]
            destinations = response["destinations"]
            hotels = response["hotels"]
            packages = response["packages"]
            follow_ups = response["follow_ups"]
            plan_summary = json.dumps(collected_info)
            plan_generated = True
        else:
            answer = self.generate_conversational_response(collected_info, next_questions)

        bot_message = Message(session_id=request.session_id, content=answer, is_bot=True)
        db.add(bot_message)
        db.commit()

        if plan_generated:
            plan = Plan(session_id=request.session_id, summary=plan_summary, details=json.dumps(collected_info))
            db.add(plan)
            db.commit()

        return ChatResponse(
            answer=answer,
            conversational_text=answer,
            destinations=destinations,
            hotels=hotels,
            packages=packages,
            follow_up_questions=follow_ups,
            plan_generated=plan_generated,
            plan_summary=plan_summary
        )

    def extract_info(self, history: set) -> Dict[str, str]:
        info: Dict[str, str] = {}

        for msg in history:
            if ":" in msg:
                parts = [p.strip() for p in msg.split(":", 1)]
                if len(parts) == 2:
                    key_text, value_text = parts
                    for item in self.flow:
                        if item["key"] == key_text.lower():
                            info[item["key"]] = value_text

        for msg in history:
            lower = msg.lower()
            
            # Destination extraction
            for dest in ["maldives", "dubai", "paris", "tokyo", "bali", "thailand"]:
                if dest in lower and "purpose" not in info:
                    info["purpose"] = dest.title()

            dest_match = re.search(r"(?:travel to|trip to|visit)\s+([a-zA-Z ]+)", lower)
            if dest_match and "purpose" not in info:
                info["purpose"] = dest_match.group(1).strip().title()

            date_match = re.search(r"(\d{4}-\d{2}-\d{2})", lower)
            if date_match and "date" not in info:
                info["date"] = date_match.group(1)

            guests_match = re.search(r"(\d+)\s*guests?", lower)
            if guests_match and "guests" not in info:
                info["guests"] = guests_match.group(1)

            budget_match = re.search(r"\$\s*(\d+)|budget(?: is)?\s*(\d+)", lower)
            if budget_match and "budget" not in info:
                info["budget"] = budget_match.group(1) or budget_match.group(2)

        return info

    def get_next_questions(self, collected_info: Dict[str, str]) -> List[Question]:
        questions: List[Question] = []
        for item in self.flow:
            if item["key"] not in collected_info and item["required"]:
                questions.append(Question(question=item["question"], key=item["key"]))
        return questions[:1]

    def generate_conversational_response(self, info: Dict[str, str], next_questions: List[Question]) -> str:
        if not info:
            return "Hey there! 👋 Where are you thinking of heading? Tell me a destination and I'll help you plan the perfect trip!"
        elif next_questions:
            return next_questions[0].question
        return "Tell me more about your travel plans!"

    def can_generate_plan(self, info: Dict[str, str]) -> bool:
        required = [item for item in self.flow if item["required"]]
        return all(item["key"] in info for item in required)

    def generate_full_tour_response(self, info: Dict[str, str]) -> dict:
        destination = info.get("purpose", "your destination").lower()
        date = info.get("date", "TBD")
        guests = info.get("guests", "2")
        budget = info.get("budget", "Flexible")

        # Get destination-specific data
        dest_data = self.destination_data.get(destination, self.get_generic_destination_data(destination))

        # Convert to CardModel objects
        destinations = [
            DestinationCard(
                name=d["name"],
                image_url=d["image"],
                rating=d["rating"],
                reviews_count=int(d["rating"] * 100),
                price_from=d["price"],
                duration=d["duration"],
                highlights=["Top rated", "Popular destination"]
            )
            for d in dest_data["destinations"]
        ]

        hotels = [
            HotelCard(
                name=h["name"],
                image_url="https://images.unsplash.com/photo-1631049307264-da0ec9d70304",
                rating=h["rating"],
                reviews_count=int(h["rating"] * 150),
                price_per_night=h["price"],
                amenities=h["amenities"]
            )
            for h in sorted(dest_data["hotels"], key=lambda x: -x["rating"])
        ]

        packages = [
            PackageCard(
                name=p["name"],
                price=p["price"],
                duration=p["name"].split("-")[0] if "-" in p["name"] else "4 days",
                rating=p["rating"],
                highlights=p["highlights"]
            )
            for p in sorted(dest_data["packages"], key=lambda x: -x["rating"])
        ]

        follow_ups = [
            FollowUpQuestion(
                question="What activities interest you most?",
                suggestions=["Water sports", "Cultural tours", "Relaxation", "Adventure"]
            ),
            FollowUpQuestion(
                question="Any dietary or accessibility requirements?",
                suggestions=["Vegetarian", "Wheelchair access", "Halal", "None"]
            ),
        ]

        conversational_text = (
            f"🌍 Perfect! I found some amazing options for {info.get('purpose', 'your destination')}!\n\n"
            f"Based on your trip in {date} for {guests} guest(s) with a {budget} budget, "
            f"here are handpicked destinations, hotels (sorted by ratings), and packages tailored for you.\n\n"
            f"Check out the recommendations below and let me know what catches your eye!"
        )

        return {
            "conversational_text": conversational_text,
            "destinations": destinations,
            "hotels": hotels,
            "packages": packages,
            "follow_ups": follow_ups,
        }

    def get_generic_destination_data(self, destination: str) -> dict:
        return {
            "destinations": [
                {"name": f"{destination} City Center", "image": "https://images.unsplash.com/photo-1488646953014-85cb44e25828", "price": "$1,200", "rating": 4.6, "duration": "3 days"},
                {"name": f"{destination} Landmarks", "image": "https://images.unsplash.com/photo-1506905925346-21bda4d32df4", "price": "$1,500", "rating": 4.7, "duration": "4 days"},
                {"name": f"{destination} Cultural Tour", "image": "https://images.unsplash.com/photo-1469854523086-cc02fe5d8800", "price": "$1,800", "rating": 4.8, "duration": "5 days"},
            ],
            "hotels": [
                {"name": f"{destination} Grand Hotel", "rating": 4.8, "price": "$250/night", "amenities": ["Gym", "Restaurant", "WiFi"]},
                {"name": f"{destination} Comfort Stay", "rating": 4.6, "price": "$180/night", "amenities": ["Breakfast", "Airport shuttle"]},
                {"name": f"{destination} Boutique Inn", "rating": 4.7, "price": "$200/night", "amenities": ["Spa", "Rooftop bar"]},
            ],
            "packages": [
                {"name": "5-Day City Explorer", "price": "$1,500", "rating": 4.7, "highlights": ["City tours", "Local dining", "Museum visits"]},
                {"name": "4-Day Culture & Food", "price": "$1,200", "rating": 4.6, "highlights": ["Food tours", "Cultural sites"]},
                {"name": "7-Day Comprehensive", "price": "$2,000", "rating": 4.8, "highlights": ["All attractions", "Expert guide", "Meals included"]},
            ]
        }

