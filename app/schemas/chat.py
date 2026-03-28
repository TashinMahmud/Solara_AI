from pydantic import BaseModel, Field
from typing import List, Optional

class Question(BaseModel):
    question: str
    key: str

class ChatRequest(BaseModel):
    user_id: str = Field(examples=["user123"])
    session_id: str = Field(examples=["session123"])
    message: str = Field(examples=["I want to book travel to Maldives"])

class ChatResponse(BaseModel):
    answer: str
    plan_generated: bool = False
    plan_summary: Optional[str] = None