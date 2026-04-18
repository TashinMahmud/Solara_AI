# Solara AI — Backend API Integration Guide

**Version:** 2.1.0  
**Last Updated:** April 2026

## Overview
Technical reference for Solara AI conversational backend. Covers endpoints, request/response schemas, subscription behavior (free/basic/pro), and conversation state machine.

---

## Base Configuration

**Development URL:** `http://127.0.0.1:8000`  
**Swagger UI:** `/docs`

---

## Endpoint Details

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/v1/chat` | Main orchestrator endpoint. Sends messages, returns state and gallery options. |
| `POST` | `/api/v1/flights/search` | Direct internal flight search. |
| `POST` | `/api/v1/hotels/search` | Direct internal hotel search. |
| `GET` | `/health` | Health check. |

---

## Main Chat Endpoint

### `POST /api/v1/chat`

Handles all prompt routing, tool calling, history continuity, and JSON schema extraction. 

### Request Schema

```json
{
  "message": "I want a trip to Dubai",
  "session_id": "sess_12345",
  "subscription_plan": "pro",
  "user_id": "usr_abc890"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `message` | `string` | Yes | Raw user prompt. |
| `session_id` | `string` | Yes | Unique conversation ID. Maps to backend SQLite history. |
| `subscription_plan`| `string` | No (default: `free`) | Determines auth gatekeeping and AI automation tier. Values: `free`, `basic`, `pro`. |
| `user_id` | `string` | No | ID for individual loyalty tracking and booking history. |

> **Note:** Backend manages message history automatically via `session_id`. Do not pass array history.

---

### Response Schema

Every 200 OK response strictly matches this structure.

```json
{
  "session_id": "sess_12345",
  "user_id": "usr_abc890",
  "ai_message": "string",
  "current_step": "location",
  "parameters_extracted": { ... } | null,
  "trip_card": { ... } | null,
  "trip_guide": { ... } | null,
  "submitted": false,
  "checkout_required": false
}
```

| Field | Description |
|-------|-------------|
| `session_id` | Echoes input session_id. |
| `user_id` | Echoes input user_id. |
| `ai_message` | Natural language LLM output. Render in chat bubble. |
| `current_step` | Flag for frontend UI mounting (see `current_step` mapping). |
| `parameters_extracted`| Live JSON state of requested trip params. |
| `trip_card` | Quick summary widget data. |
| `trip_guide` | Core gallery and travel data (flights, hotels, rewards discount). |
| `submitted` | True if AI successfully orchestrated booking via backend tool (Pro tier). |
| `checkout_required`| True if AI prompts manual payment fallback (Basic tier). |

### `current_step` Mapping

Render corresponding UI component based on `current_step` string:

| Value | Frontend UI Component |
|-------|-----------------------|
| `"location"` | Destination discovery cards. |
| `"dates"` | Calendar/Date picker. |
| `"travelers_budget"`| Group size / Budget tier selector. |
| `"experience"` | Category cards (Relaxation, Culture, etc). |
| `"citizenship"` | Passport input field. |
| `"passengers"` | Passenger manifest form. |
| `"selection"` | Dual gallery view (`flight_options`, `hotel_options`). |
| `"complete"` | Success confirmation / Checkout redirect. |

---

### `parameters_extracted` Object

Tracks live parameter extraction.

```json
{
  "location": "Dubai",
  "start_date": "2025-08-10",
  "end_date": "2025-08-18",
  "travelers": "Solo",
  "budget": "Moderate",
  "experience": "Culture",
  "citizenship": "US Passport",
  "passengers": [
     { "name": "John Doe", "passport": "12345" }
  ]
}
```

---

### `trip_card` Object

Quick summary widget generated when all parameters are collected.

```json
{
  "destination": "Dubai, UAE",
  "description": "Dazzling blend of ultramodern architecture and luxury.",
  "rating": 4.8,
  "distance_km": 11000,
  "restaurants_available": 1200,
  "total_price_per_person": 1862,
  "points_applied": 1200,
  "parameters_extracted": { ... }
}
```

---

### `trip_guide` Object

Generated when search tools execute. Populates gallery lists first, then locks selection into single objects.

```json
{
  "flight": { ... } | null,
  "hotel": { ... } | null,
  "flight_options": [ ... ],
  "hotel_options": [ ... ],
  "weather": { "date": "...", "condition": "...", "temperature_celsius": 42 },
  "travel_tips": [ ... ],
  "culture_etiquette": [ ... ],
  "safety_info": { "safety_level": "High", "tips": [...] },
  "visa_status": "Visa Free",
  "base_price": 1500,
  "points_discount": 100,
  "final_estimated_total": 1400
}
```

1. **Search Phase:** `flight` and `hotel` are null. `flight_options` and `hotel_options` contain array of 5 dicts. Render gallery.
2. **Selection Phase:** User selects option. `flight_options` empty. Chosen item locked into `flight` and `hotel`.

### Flight Object Details

```json
{
  "route": "NEW YORK → Dubai",
  "stops": "Non-stop",
  "duration": "13h 50m",
  "price_usd": 980.0,
  "carrier_code": "EK",
  "loyalty_points_earned": 98,
  "baggage_policy": "1 carry-on + 1 checked bag (23kg)",
  "pnr_status": "OPEN",
  "image_url": "https://images.unsplash.com/photo-1436..."
}
```

### Hotel Object Details

```json
{
  "name": "Grand Hyatt Dubai",
  "nights": 8,
  "rating": 4.7,
  "price_per_night_usd": 150.0,
  "amenities": ["Free WiFi", "Gym", "Breakfast"],
  "review_count": 1240,
  "tripadvisor_rating": 4.6,
  "cancellation_policy": "Free cancellation up to 72 hours.",
  "check_in_instructions": "Check-in from 3:00 PM.",
  "amenities_icons": ["wifi", "fitness_center", "free_breakfast"],
  "image_url": "https://images.unsplash.com/photo-1566..."
}
```

---

## Subscription Authorization

Middleware authenticates via `subscription_plan`. The API response dictates checkout workflow via two strict boolean flags: `submitted` and `checkout_required`.

| Tier | AI Booking Behavior | API Outcome |
|------|---------------------|-------------|
| `pro` | Fully Autonomous. AI submits payload to internal booking API seamlessly. | `submitted: true`<br>`checkout_required: false` |
| `basic` | Restricted. AI halts at final confirmation and prompts manual payment. | `submitted: false`<br>`checkout_required: true` |
| `free` | Restricted/Denied limit. | 403 Forbidden |

**Frontend Logic Rule:**
Always check these flags when `current_step == "complete"`. If `submitted` is true, render a Success/Booking Confirmation screen. If `checkout_required` is true, render a "Proceed to Manual Checkout" button linking to the standard payment gateway.

---

## Error Handling

| Code | Cause |
|------|-------|
| `403`| Invalid subscription / Rate limit reached. |
| `502`| Internal backend tool timeout (loyalty, checkout APIs down). |
| `500`| LLM routing parser failure / Unknown error. |

---

## Quick Test payload

Use Swagger (`http://127.0.0.1:8000/docs`) -> `POST /api/v1/chat`

**Turn 1:**
```json
{
  "message": "Solo trip to Tokyo, Oct 1 to 10. Luxury budget, culture focus. US Passport.",
  "session_id": "test_1",
  "subscription_plan": "pro",
  "user_id": "usr_999"
}
```

**Turn 2:**
```json
{
  "message": "I'll take the first flight and second hotel.",
  "session_id": "test_1",
  "subscription_plan": "pro",
  "user_id": "usr_999"
}
```
