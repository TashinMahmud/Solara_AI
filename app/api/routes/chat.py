from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.model.database import get_db
from app.schemas.chat import ChatRequest, ChatResponse
from app.services.chat_service import ChatService

router = APIRouter()

@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest, db: Session = Depends(get_db)):
    service = ChatService()
    return service.process_message(db, request)