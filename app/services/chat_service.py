from sqlalchemy.orm import Session
from app.model.models import User, Session as DBSession, Message, Plan
from app.schemas.chat import ChatRequest, ChatResponse, Question
from typing import Dict, List
import json
from anthropic import Anthropic
from app.core.config import settings

class ChatService:
    def __init__(self):
        self.client = Anthropic(api_key=settings.claude_api_key)
        # Define the conversation flow
        self.flow = [
            {"key": "purpose", "question": "What would you like to book? (e.g., hotel, flight, event)", "required": True},
            {"key": "date", "question": "When do you want to book it? (e.g., 2023-12-25)", "required": True},
            {"key": "guests", "question": "How many guests?", "required": False},
            {"key": "budget", "question": "What's your budget?", "required": False},
        ]

    def process_message(self, db: Session, request: ChatRequest) -> ChatResponse:
        # Get or create user
        user = db.query(User).filter(User.id == request.user_id).first()
        if not user:
            user = User(id=request.user_id)
            db.add(user)
            db.commit()

        # Get or create session
        session = db.query(DBSession).filter(DBSession.id == request.session_id).first()
        if not session:
            session = DBSession(id=request.session_id, user_id=request.user_id)
            db.add(session)
            db.commit()

        # Save user message
        user_message = Message(session_id=request.session_id, content=request.message, is_bot=False)
        db.add(user_message)
        db.commit()

        # Get conversation history
        messages = db.query(Message).filter(Message.session_id == request.session_id).order_by(Message.created_at).all()
        history = {msg.content for msg in messages if not msg.is_bot}

        # Determine current state
        collected_info = self.extract_info(history)
        next_questions = self.get_next_questions(collected_info)

        # Generate answer
        answer = self.generate_answer(request.message, collected_info, next_questions)

        # Save bot message
        bot_message = Message(session_id=request.session_id, content=answer, is_bot=True)
        db.add(bot_message)
        db.commit()

        # Check if plan can be generated
        plan_generated = False
        plan_summary = None
        if self.can_generate_plan(collected_info):
            plan_summary = self.generate_plan(collected_info)
            plan = Plan(session_id=request.session_id, summary=plan_summary, details=json.dumps(collected_info))
            db.add(plan)
            db.commit()
            plan_generated = True

        return ChatResponse(
            answer=answer,
            plan_generated=plan_generated,
            plan_summary=plan_summary
        )

    def extract_info(self, history: set) -> Dict[str, str]:
        # Simple extraction - in real app, use NLP
        info = {}
        for item in self.flow:
            for msg in history:
                if item["key"].lower() in msg.lower():
                    # Extract value - simplistic
                    parts = msg.split(":")
                    if len(parts) > 1:
                        info[item["key"]] = parts[1].strip()
        return info

    def get_next_questions(self, collected_info: Dict[str, str]) -> List[Question]:
        questions = []
        for item in self.flow:
            if item["key"] not in collected_info and item["required"]:
                questions.append(Question(question=item["question"], key=item["key"]))
        return questions[:1]  # Ask only 1 question at a time

    def generate_answer(self, user_message: str, info: Dict, next_questions: List[Question]) -> str:
        system_prompt = """You are a helpful conversational chatbot that helps users book services like hotels, flights, events, etc.
        Your goal is to gather necessary information naturally through conversation and eventually generate a booking plan.
        Be friendly, concise, and ask questions one at a time when needed.
        If you have all required info, acknowledge and say you're generating the plan."""

        user_prompt = f"""
        Current collected information: {json.dumps(info)}
        Next questions to ask if needed: {[q.question for q in next_questions]}
        User's latest message: {user_message}

        Respond naturally, incorporating the information and asking the next relevant question if appropriate.
        """

        try:
            response = self.client.messages.create(
                model="claude-3-haiku-20240307",
                max_tokens=300,
                system=system_prompt,
                messages=[
                    {"role": "user", "content": user_prompt}
                ]
            )
            return response.content[0].text.strip()
        except Exception as e:
            # Fallback to simple response
            if not info:
                return "Hello! I'm here to help you book something. Let's start with some details."
            elif next_questions:
                return f"Thanks for the info. To proceed, I need: {', '.join([q.question for q in next_questions])}"
            else:
                return "Great! I have all the information I need. Generating your plan now."

    def can_generate_plan(self, info: Dict) -> bool:
        required = [item for item in self.flow if item["required"]]
        return all(item["key"] in info for item in required)

    def generate_plan(self, info: Dict) -> str:
        return f"Booking Plan: {info.get('purpose', 'Service')} on {info.get('date', 'Date')}. Guests: {info.get('guests', '1')}. Budget: {info.get('budget', 'N/A')}."