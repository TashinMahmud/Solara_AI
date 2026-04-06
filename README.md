# WanderAI (Gotrip) Backend

WanderAI is a conversational, autonomous AI booking orchestrator powered by **FastAPI** and **Claude 3.5 Sonnet**. 

Unlike a standard chatbot, WanderAI internally controls the flow of conversation to extract exact necessary booking parameters, explicitly triggers Python-native functions to scrape/search flight and hotel APIs, structures that data into a strict UI-ready JSON schema for the frontend, and finalizes outbound webhook requests to the core backend.

## Features
- **Smart Conversational Flow:** Anthropic Claude 3.5 automatically manages the conversation state to collect Location, Dates, Travelers, Budget, and Experience.
- **Native Tool Calling:** Intercepts LLM tool-use requests and seamlessly runs Python code (`hotel_service`, `flight_service`) to pull Amadeus/TripAdvisor data without exposing logic to the LLM.
- **Strict UI Schema Generation:** Returns fully hydrated `trip_card` and `trip_guide` JSON schemas designed to drop directly into a React/Vue interface.
- **SaaS Middleware Auth:** Included Dependency Injection on the `chat` endpoint ensuring only paying/valid users (`trial_user`) can consume expensive LLM inference tokens.

## Running Locally

1. Create a virtual environment and install dependencies:
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

2. Configure environment variables. Rename `.env.example` to `.env` and add your keys:
```
ANTHROPIC_API_KEY=your_key
INTERNAL_API_SUBMIT=https://your-core-backend.com/api/trips/new
```

3. Run the development server:
```bash
uvicorn app.main:app --reload
```
*Server runs at `http://127.0.0.1:8000`*

## API Endpoints

- **`POST /api/v1/chat`**: The primary conversational interface connecting the Frontend to the AI.
- **`POST /api/v1/flights/search`**: Exposes the internal Flight APIs manually.
- **`POST /api/v1/hotels/search`**: Exposes the internal Hotel APIs manually.

## Testing
An automated test suite verifies 27 separate points of JSON structural integrity as well as the 403 SaaS Auth gating logic.
```bash
python test_chat.py
```
