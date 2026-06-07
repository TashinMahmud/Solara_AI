# ✈️ Solara AI — Conversational AI Booking Orchestrator

<div align="center">

[![FastAPI](https://img.shields.io/badge/FastAPI-005571?style=for-the-badge&logo=fastapi&logoColor=white)](#prerequisites)
[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![Anthropic Claude](https://img.shields.io/badge/Claude-3.5_Sonnet-D97706?style=for-the-badge&logo=anthropic&logoColor=white)](https://www.anthropic.com/)
[![SQLite](https://img.shields.io/badge/SQLite-Database-003B57?style=for-the-badge&logo=sqlite&logoColor=white)](#session-management)

---

**Solara AI** is a high-performance, conversational AI travel orchestration layer. Powered by **Claude 3.5 Sonnet** and **FastAPI**, it manages multi-turn travel booking conversations, extracts key parameters, triggers live search APIs for flights and hotels, and formats data into structured, frontend-ready JSON.

</div>

---

## 🛠️ Technical Architecture

Solara AI acts as a middleware orchestration layer between the user interface and downstream travel APIs (Amadeus, TripAdvisor).

```
+-------------------------------------------------------------+
|                      CLIENT FRONTEND                        |
|   Sends User Messages  <--->  Receives Hydrated UI Schemas  |
+------------------------------+------------------------------+
                               | (HTTP POST /chat)
                               v
+-------------------------------------------------------------+
|                     FASTAPI APPLICATION                     |
|  Exposes Gated Routers, Manages CORSMiddleware, Logs Calls  |
+------------------------------+------------------------------+
                               | (Dependency Injection)
                               v
+-------------------------------------------------------------+
|                  SaaS GATEKEEPER & AUTH                     |
|  Validates user subscription plans and remaining API turns  |
+------------------------------+------------------------------+
                               | (If Valid)
                               v
+-------------------------------------------------------------+
|                 CLAUDE 3.5 SONNET AGENT                     |
|  Maintains conversation flow & issues tool calls for search |
+--------------+-----------------------+----------------------+
               |                       |
               v                       v
+--------------+-------+       +-------+----------------------+
|   EXTERNAL APIs      |       |      SESSION PERSISTENCE     |
| - Amadeus API        |       | - SQLite Database            |
| - TripAdvisor API    |       | - Local Session History      |
+----------------------+       +------------------------------+
```

### Core Code Modules & Responsibilities

*   `app/api/` Layer:
    *   [`routes/chat.py`](app/api/routes/chat.py): Main chat endpoint with subscription-based access gating, turn limit verification, and state tracking.
    *   [`routes/flights.py`](app/api/routes/flights.py): Standalone route exposing the Amadeus flight search client.
    *   [`routes/hotels.py`](app/api/routes/hotels.py): Standalone route exposing the TripAdvisor hotel search client.
*   `app/services/` Layer:
    *   [`ai_agent.py`](app/services/ai_agent.py): Claude 3.5 tool-calling agent loop, system prompt configuration, and JSON formatting schemas.
    *   [`amadeus_service.py`](app/services/amadeus_service.py): Client handler for flight search, credential caching, and response sanitization.
    *   [`tripadvisor_service.py`](app/services/tripadvisor_service.py): Client handler for searching hotels and locations on TripAdvisor.
    *   [`session_manager.py`](app/services/session_manager.py): SQLite session history loader and saver using async database connections.

---

## ⚡ Core Integration Interfaces

<details>
<summary><b>🏨 TripAdvisor Locations & Hotels Search</b></summary>

The service integrates with the TripAdvisor Content API. It translates unstructured locations into geocoded coordinates, searches local properties matching user constraints, and structures results into a clean UI-ready format.
</details>

<details>
<summary><b>✈️ Amadeus Flight Search Client</b></summary>

Coordinates OAuth tokens and executes queries for multi-destination flights. Handles price formatting, segment parsing, and airline code mappings.
</details>

<details>
<summary><b>🔒 SaaS Subscription Gatekeeper</b></summary>

Uses FastAPI dependency injection to check user plans. Gated tiers (`trial_user`, `basic_user`, `pro_user`) are checked dynamically, limiting usage for unpaid accounts to protect LLM token expenditures.
</details>

---

## 🚀 Getting Started

### 1. Requirements
*   Python 3.10+
*   Virtual environment manager (`venv` or `uv`)
*   SQLite 3

### 2. Configurations Setup
1.  Copy `.env.example` to a new file named `.env`:
    ```bash
    cp .env.example .env
    ```
2.  Fill in your API keys:
    ```env
    ANTHROPIC_API_KEY=your_claude_3.5_sonnet_key_here
    AMADEUS_CLIENT_ID=your_amadeus_id_here
    AMADEUS_CLIENT_SECRET=your_amadeus_secret_here
    TRIPADVISOR_API_KEY=your_tripadvisor_key_here
    INTERNAL_API_SUBMIT=https://your-core-backend.com/api/trips/new
    ```

### 3. Compilation & Execution
Initialize the virtual environment and install dependencies:
```bash
python -m venv .venv
# On Windows
.venv\Scripts\activate
# On macOS/Linux
source .venv/bin/activate

pip install -r requirements.txt
```

Run the development server using Uvicorn:
```bash
uvicorn app.main:app --reload
```
The server will start at `http://127.0.0.1:8000`.

### 4. Running Tests
Solara AI includes a comprehensive test suite covering JSON structures and subscription authorization gates:
```bash
pytest
# Or run direct scripts
python -m unittest tests/test_chat.py
```

---

## 📜 License

This project is licensed under the [MIT License](LICENSE).
