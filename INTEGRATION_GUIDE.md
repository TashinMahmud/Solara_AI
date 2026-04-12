# Solara AI Microservice: Production Integration Guide

This document outlines the strict requirements for deploying the Solara AI microservice and connecting it to the primary backend infrastructure.

## 1. Environment Configuration

To disable the internal MOCK_MODE and route traffic to the primary backend, the following environment variables must be provisioned in the AI microservice's `.env` or deployment pipeline.

```env
APP_ENV=production
ANTHROPIC_API_KEY=<required>

# Route Targets (Replace domains with production/staging URLs)
INTERNAL_API_FLIGHTS=https://api.domain.com/v1/flights/search
INTERNAL_API_HOTELS=https://api.domain.com/v1/hotels/search
INTERNAL_API_SUBMIT=https://api.domain.com/v1/trips/new
INTERNAL_API_CANCELLATION=https://api.domain.com/v1/cancellations
INTERNAL_API_LOYALTY=https://api.domain.com/v1/loyalty
INTERNAL_API_PRICING=https://api.domain.com/v1/pricing
```

## 2. Running the AI Service

The AI microservice is built on FastAPI. It should be deployed as a standalone stateless service.

**Start Command:**
```bash
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

**Health Check endpoint:** `GET /`

---

## 3. Required API Contracts (Primary Backend)

The primary backend must expose the following 6 endpoints. The AI microservice acts as an HTTP Client and will execute `POST` or `GET` requests to these targets during user conversation loops. 

Ensure the primary backend accepts these exact Request structures and returns the exact Response structures defined below.

### 3.1. Auth & Tier Gatekeeping
**Route:** `GET {INTERNAL_API_LOYALTY}/subscription`
**Trigger:** On every chat request to verify access rights.

*Request Params:*
`?user_id=<str>`

*Expected Response (200 OK):*
```json
{
  "tier": "Pro", 
  "remaining_tasks": "Unlimited"
}
```
*(Return 403 or 404 if the user has no active subscription).*

---

### 3.2. Fetch User Loyalty Points
**Route:** `GET {INTERNAL_API_LOYALTY}/points`
**Trigger:** Session start.

*Request Params:*
`?user_id=<str>`

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

### 3.3. Verify Cancellation Eligibility
**Route:** `POST {INTERNAL_API_CANCELLATION}/eligibility`
**Trigger:** User asks to cancel an existing trip prior to confirmation.

*Request Body:*
```json
{"trip_id": "<str>"}
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

### 3.4. Confirm Cancellation
**Route:** `POST {INTERNAL_API_SUBMIT}/cancel`
**Trigger:** User confirms they want to proceed with canceling a trip.

*Request Body:*
```json
{
  "trip_id": "<str>",
  "user_id": "<str>"
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

### 3.5. Execute Pricing & Point Application
**Route:** `POST {INTERNAL_API_PRICING}/apply-points`
**Trigger:** Price finalization step prior to checkout.

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

### 3.6. Submit Iterinary & Passenger Manifest
**Route:** `POST {INTERNAL_API_SUBMIT}`
**Trigger:** "Pro" tier users confirm final passenger entry and state "yes".

*Request Body:*
```json
{
  "user_id": "<str>",
  "location": "<str>",
  "start_date": "YYYY-MM-DD",
  "end_date": "YYYY-MM-DD",
  "travelers": "Solo|Couple|Family",
  "budget": "Budget|Moderate|Luxury",
  "experience": "<str>",
  "flight_details": { "route": "US -> Japan", "price_usd": 1920 },
  "hotel_details": { "name": "Boutique Nest Japan", "price_per_night_usd": 360 },
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

## 4. Notes on Agentic Loop

The AI agent executes a recursive LLM tool-calling loop. When a tool `POST`s to the primary backend and receives the specified JSON response, it parses that JSON directly to craft its natural language response to the user.
* Do not alter keys (`tier`, `points`, `base_price`, etc.) in the expected JSON responses without coordinating a `tools.py` update, as the AI's internal parser relies on specific dictionary schemas.
