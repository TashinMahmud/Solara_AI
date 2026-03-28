from fastapi import FastAPI
from app.api.routes.chat import router as chat_router
from app.model.database import engine, Base

# Create tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Conversational Chatbot API")

app.include_router(chat_router, prefix="/api/v1")

@app.get("/")
async def root():
    return {"message": "Welcome to the Chatbot API"}