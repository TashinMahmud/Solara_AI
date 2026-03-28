# Conversational Chatbot API

A FastAPI-based conversational chatbot that gathers user information through questions and generates booking plans.

## Features

- User and session management
- Conversational flow to collect booking details
- Automatic plan generation
- SQLite database for persistence

## Installation

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Run the application:
   ```bash
   uvicorn app.main:app --reload
   ```

## API Usage

### Chat Endpoint

POST `/api/v1/chat`

Request body:
```json
{
  "user_id": 1,
  "session_id": "session123",
  "message": "Hello"
}
```

Response:
```json
{
  "answer": "Hello! I'm here to help you book something. Let's start with some details.",
  "questions": [
    {"question": "What's your name?", "key": "name"},
    {"question": "What's your email?", "key": "email"}
  ],
  "plan_generated": false,
  "plan_summary": null
}
```

Continue the conversation by sending responses to the questions, and once all required info is collected, a plan will be generated.