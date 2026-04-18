# Solara AI Microservice — Production Integration Guide

**Last Updated:** April 2026

This document outlines end-to-end requirements for deploying the Solara AI microservice and connecting it to the primary backend.

---

## 1. Architecture

Solara is a **stateless AI orchestration layer**. It does not store user data, bookings, or payment info. It receives a chat message, processes it through Claude, executes backend tool calls, and returns a structured JSON response.

```
Frontend → Primary Backend (auth, JWT) → Solara AI → Claude API
                  ↑                          │
                  └──────── HTTP tool calls ──┘
```

The primary backend acts as the gateway. It validates user auth, resolves `subscription_plan` and `user_id`, then proxies to Solara.

---

## 2. Environment Configuration

Set these in the AI microservice's `.env` or deployment pipeline. Setting `APP_ENV=production` disables all internal mock responses.

```env
APP_ENV=production
ANTHROPIC_API_KEY=<required>

INTERNAL_API_FLIGHTS=https://api.domain.com/v1/flights/search
INTERNAL_API_HOTELS=https://api.domain.com/v1/hotels/search
INTERNAL_API_SUBMIT=https://api.domain.com/v1/trips/new
INTERNAL_API_CANCELLATION=https://api.domain.com/v1/cancellations
INTERNAL_API_LOYALTY=https://api.domain.com/v1/loyalty
INTERNAL_API_PRICING=https://api.domain.com/v1/pricing
```

---

## 3. Running the AI Service

```bash
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

**Health Check:** `GET /health` → `{"status": "ok", "service": "Solara"}`

---

## 4. Solara Input/Output

### Request (from primary backend → Solara)

```
POST /api/v1/chat
```

```json
{
  "message": "I want to go to Japan",
  "session_id": "sess_abc123",
  "subscription_plan": "pro",
  "user_id": "usr_789"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `message` | string | Yes | User's chat message. |
| `session_id` | string | Yes | Unique conversation ID. Solara manages history via this key. |
| `subscription_plan` | string | No (default: `free`) | `free`, `basic`, or `pro`. Controls AI behavior and tool access. |
| `user_id` | string | No | Used for loyalty point lookups and booking attribution. |

### Response (Solara → primary backend)

```json
{
  "session_id": "sess_abc123",
  "user_id": "usr_789",
  "ai_message": "Welcome! Where would you like to go?",
  "current_step": "location",
  "parameters_extracted": { "location": null, ... },
  "trip_card": null,
  "trip_guide": null,
  "submitted": false,
  "checkout_required": false
}
```

---

## 5. Required API Contracts (Primary Backend)

The primary backend must expose the following 8 endpoints. Solara calls these during the AI tool loop.

Do not alter response keys without coordinating a `tools.py` update — the AI parser relies on exact key names.

---

### 5.1. Flight Search
**Route:** `POST {INTERNAL_API_FLIGHTS}`
**Trigger:** All 5 travel parameters collected.

*Request Body:*
```json
{
  "origin": "JFK",
  "destination": "Tokyo",
  "dates": { "start": "2025-10-01", "end": "2025-10-10" },
  "budget": "Luxury"
}
```

*Expected Response (200 OK):*
Array of flight objects. Each must include: `route`, `stops`, `duration`, `price_usd`, `carrier_code`, `loyalty_points_earned`, `baggage_policy`, `pnr_status`, `image_url`.

---

### 5.2. Hotel Search
**Route:** `POST {INTERNAL_API_HOTELS}`
**Trigger:** All 5 travel parameters collected (called alongside flight search).

*Request Body:*
```json
{
  "destination": "Tokyo",
  "dates": { "start": "2025-10-01", "end": "2025-10-10" },
  "budget": "Luxury",
  "travelers": "Solo"
}
```

*Expected Response (200 OK):*
Array of hotel objects. Each must include: `name`, `nights`, `rating`, `price_per_night_usd`, `amenities`, `review_count`, `tripadvisor_rating`, `cancellation_policy`, `check_in_instructions`, `amenities_icons`, `image_url`.

---

### 5.3. Flexible Alternatives Search
**Route:** `POST {INTERNAL_API_FLIGHTS}/flexible`
**Trigger:** Search results exceed user's budget.

*Request Body:*
```json
{
  "location": "Japan",
  "start_date": "2025-10-01",
  "end_date": "2025-10-10",
  "budget": "Budget",
  "travelers": "Solo"
}
```

*Expected Response (200 OK):*
```json
{
  "alternative_found": true,
  "suggested_location": "Japan",
  "suggested_dates": { "start": "2025-10-12", "end": "2025-10-17" },
  "original_price": 1200,
  "new_price": 850
}
```

---

### 5.4. Subscription Verification
**Route:** `GET {INTERNAL_API_LOYALTY}/subscription`
**Trigger:** Every chat request (gatekeeping).

*Request Params:*
`?plan=pro`

*Expected Response (200 OK):*
```json
{
  "tier": "Pro",
  "remaining_tasks": "Unlimited"
}
```

Return 403/404 if invalid. Solara will block the user with a 403.

---

### 5.5. Fetch User Loyalty Points
**Route:** `GET {INTERNAL_API_LOYALTY}/points`
**Trigger:** Start of each session (AI calls this tool automatically).

*Request Params:*
`?user_id=usr_789`

*Expected Response (200 OK):*
```json
{
  "points": 1200,
  "expiring_soon": true,
  "expiry_days": 15,
  "earning_rate": "2%",
  "expiry_window": "365 days"
}
```

---

### 5.6. Cancellation Eligibility Check
**Route:** `POST {INTERNAL_API_CANCELLATION}/eligibility`
**Trigger:** User mentions cancelling a trip.

*Request Body:*
```json
{ "trip_id": "WDR-2025-123" }
```

*Expected Response (200 OK):*
```json
{
  "eligible": true,
  "refund_amount_credits": 1000,
  "days_valid": 30
}
```

---

### 5.7. Confirm Cancellation
**Route:** `POST {INTERNAL_API_SUBMIT}/cancel`
**Trigger:** User explicitly confirms cancellation after eligibility check.

*Request Body:*
```json
{
  "trip_id": "WDR-2025-123",
  "subscription_plan": "pro"
}
```

*Expected Response (200 OK):*
```json
{
  "status": "cancelled",
  "refund_credits_issued": 1000,
  "refund_delivery": "2-3 business days",
  "booking_status": "CANCELLED"
}
```

---

### 5.8. Apply Points to Quote
**Route:** `POST {INTERNAL_API_PRICING}/apply-points`
**Trigger:** User selects flight+hotel, AI calculates discounted price.

*Request Body:*
```json
{
  "base_price": 5160,
  "points_to_use": 1200
}
```

*Expected Response (200 OK):*
```json
{
  "base_price": 5160,
  "points_discount": 120,
  "final_estimated_total": 5040
}
```

---

### 5.9. Submit Itinerary & Passenger Manifest
**Route:** `POST {INTERNAL_API_SUBMIT}`
**Trigger:** Pro tier user confirms final booking (says "YES").

*Request Body:*
```json
{
  "subscription_plan": "pro",
  "user_id": "usr_789",
  "location": "Japan",
  "start_date": "2025-10-01",
  "end_date": "2025-10-10",
  "travelers": "Solo",
  "budget": "Luxury",
  "experience": "Culture",
  "flight_details": { "route": "JFK → Tokyo", "price_usd": 1920 },
  "hotel_details": { "name": "Grand Hyatt Tokyo", "price_per_night_usd": 450 },
  "passengers": [
    { "name": "John Doe", "passport": "A1234567" }
  ],
  "points_applied": 1200
}
```

*Expected Response (200 OK):*
```json
{
  "status": "confirmed",
  "booking_reference": "WDR-2025-JPN-8847",
  "pnr": "XKQF7R",
  "e_ticket_url": "https://gotrip.com/tickets/XKQF7R.pdf",
  "payment_link": "https://gotrip.com/checkout/WDR-2025-JPN-8847"
}
```

The AI reads this response and presents the booking reference and links to the user in the chat.

---

## 6. AI Agent Behavior Notes

- The agent executes a bounded tool-calling loop (max 10 iterations per request).
- Tool errors are caught gracefully and returned to Claude as error JSON, not thrown as HTTP exceptions.
- Chat history is stored in local SQLite keyed by `session_id`. History is auto-truncated to the last 40 messages to prevent context overflow.
- Free tier users are hard-blocked after their `remaining_tasks` limit is hit (counted by user turns in session history).
- Structured logs are output under the `solara.*` namespace (`solara.agent`, `solara.chat`, `solara.session`).
