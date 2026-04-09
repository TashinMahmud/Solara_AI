# Solara AI — Backend API Documentation

**Author:** Tashin Mahmud Khan  
**Version:** 2.0.0  
**Last Updated:** April 2026

---

## Overview

Solara is the AI-powered travel concierge that sits at the core of the Gotrip platform. It handles the entire trip planning flow conversationally — from collecting user preferences to searching flights/hotels and finalizing bookings.

This document covers everything you need to integrate with the Solara backend: endpoints, request/response schemas, subscription-based behavior differences, and the conversation lifecycle.

---

## Base URL

```
Development: http://127.0.0.1:8000
```

Interactive API docs (Swagger UI) are available at `/docs`.

---

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/v1/chat` | Main conversational endpoint. Handles all AI interactions. |
| `POST` | `/api/v1/flights/search` | Direct flight search (standalone, outside chat). |
| `POST` | `/api/v1/hotels/search` | Direct hotel search (standalone, outside chat). |
| `GET` | `/health` | Health check. Returns `{"status": "ok", "service": "Solara"}`. |

---

## Authentication & Subscription Tiers

Every request to `/api/v1/chat` **must** include a valid `user_id`. If the `user_id` is not recognized, the API returns a `403 Forbidden`.

The backend resolves the user's subscription tier internally from the `user_id`. We do **not** need to pass any tier or subscription info in the payload — the backend handles that lookup on its own.

### Tier Behaviors

| Tier | Behavior | `submitted` | `checkout_required` |
|------|----------|:-----------:|:-------------------:|
| **Pro** | Full automation. When the user picks an option, Solara calls the internal booking service automatically. | `true` | `false` |
| **Basic** | Limited. The AI will present options but will NOT auto-book. It tells the user to check out manually and flags the response accordingly. | `false` | `true` |

### Test User IDs (for development)

| `user_id` | Tier | Tasks Remaining |
|-----------|------|-----------------|
| `pro_tester` | Pro | Unlimited |
| `basic_tester` | Basic | 5 per month |
| `trial_user` | Pro | Unlimited |

Any other `user_id` → `403 Forbidden`.

---

## Main Chat Endpoint

### `POST /api/v1/chat`

This is the primary endpoint. All conversation happens here.

### Request Body

```json
{
  "message": "I want a trip to Dubai",
  "session_id": "unique-session-id-here",
  "user_id": "pro_tester"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `message` | `string` | Yes | The user's message in plain text. |
| `session_id` | `string` | Yes | A unique ID to maintain conversation context. Use the same `session_id` across all messages in a single conversation. The backend stores history in a local SQLite DB keyed by this. |
| `user_id` | `string` | No | The authenticated user's ID. Required for subscription gating. |

> **Important:** You do NOT need to pass conversation history. The backend manages that automatically using the `session_id`. Just keep sending the same `session_id` for multi-turn conversations and Solara will remember everything.

---

### Response Body

Every response from `/api/v1/chat` follows this exact structure:

```json
{
  "ai_message": "string",
  "current_step": "location",
  "parameters_extracted": { ... } | null,
  "trip_card": { ... } | null,
  "trip_guide": { ... } | null,
  "submitted": false,
  "checkout_required": false
}
```

| Field | Type | Description |
|-------|------|-------------|
| `ai_message` | `string` | The natural language response from Solara. Render this in the chat UI. |
| `current_step` | `string` | Tells the frontend which UI component to render alongside the chat. See table below. |
| `parameters_extracted` | `object \| null` | Current state of collected trip parameters (see below). |
| `trip_card` | `object \| null` | Summary card for the trip. Populated once all parameters are collected and searches are done. |
| `trip_guide` | `object \| null` | Detailed trip info — flights, hotels, weather, tips, safety, visa. Populated after search tools run. |
| `submitted` | `boolean` | `true` if Solara successfully submitted the booking to the backend (Pro users only). |
| `checkout_required` | `boolean` | `true` if the user needs to be redirected to manual checkout (Basic users only). |

### `current_step` Values

This field tells the frontend exactly which interactive UI component to display alongside the chat message. The frontend should always render`ai_message` in the chat bubble AND mount the corresponding UI element based on this value.

| `current_step` | Frontend Should Render |
|---|---|
| `"location"` | Destination cards (popular locations from Figma) |
| `"dates"` | Date picker component |
| `"travelers_budget"` | Traveler type cards + Budget tier selector |
| `"experience"` | Experience type cards (Relaxation, Adventure, etc.) |
| `"citizenship"` | Passport/nationality input or dropdown |
| `"selection"` | Flight & Hotel gallery cards (from `flight_options[]` / `hotel_options[]`) |
| `"complete"` | Success screen (Pro) or Checkout redirect button (Basic) |

The user can either **click a UI card** or **type their answer** — both send the next message to the same `/api/v1/chat` endpoint.
current_step value ("location", "dates", "travelers_budget", "experience", "citizenship", "selection", "complete")
---

### `parameters_extracted`

This object is returned on **every** response once the user starts providing trip details. It always contains all 7 keys. Unknown values are set to `null`.

```json
{
  "location": "Dubai",
  "start_date": "2025-08-10",
  "end_date": "2025-08-18",
  "travelers": "Solo",
  "budget": "Moderate",
  "experience": "Mix of everything",
  "citizenship": "US Passport"
}
```

| Field | Type | Possible Values |
|-------|------|-----------------|
| `location` | `string \| null` | Any destination name |
| `start_date` | `string \| null` | `YYYY-MM-DD` format |
| `end_date` | `string \| null` | `YYYY-MM-DD` format |
| `travelers` | `string \| null` | `"Solo"`, `"Couple"`, `"Family"` |
| `budget` | `string \| null` | `"Budget"`, `"Moderate"`, `"Luxury"` |
| `experience` | `string \| null` | `"Relaxation"`, `"Adventure"`, `"Shopping"`, `"Culture"`, `"Mix of everything"` |
| `citizenship` | `string \| null` | Free text (e.g. `"US Passport"`, `"Bangladeshi Passport"`) |

Use this to build a live progress tracker on the frontend showing which fields have been collected.

---

### `trip_card`

A high-level summary card, generated once Solara has all parameters and has run searches. Good for rendering a destination preview card in the UI.

```json
{
  "destination": "Dubai, UAE",
  "description": "A dazzling blend of ultramodern architecture, luxury shopping...",
  "rating": 4.8,
  "distance_km": 11000,
  "restaurants_available": 1200,
  "total_price_per_person": 1862,
  "parameters_extracted": { ... }
}
```

---

### `trip_guide`

This is the big one — the detailed travel package. It contains flight/hotel galleries, weather data, cultural tips, safety info, and visa status.

```json
{
  "flight": { ... } | null,
  "hotel": { ... } | null,
  "flight_options": [ ... ],
  "hotel_options": [ ... ],
  "weather": { ... },
  "travel_tips": [ "tip1", "tip2" ],
  "culture_etiquette": [ "etiquette1" ],
  "safety_info": { ... },
  "visa_status": "Visa Free — US Passport holders receive..."
}
```

**How the flow works:**

1. When Solara first fetches results, `flight` and `hotel` are `null`, and the options arrays (`flight_options`, `hotel_options`) are populated with **5 results each** — this is the gallery the user picks from.
2. After the user selects their preferred option, Solara locks the chosen items into `flight` and `hotel` (single objects), and clears the options arrays.

---

### Flight Object

Each flight (both in `flight_options[]` and the final `flight`) looks like this:

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
  "image_url": "https://images.unsplash.com/photo-14364918..."
}
```

| Field | Type | Description |
|-------|------|-------------|
| `route` | `string` | Origin → Destination display string |
| `stops` | `string` | `"Non-stop"`, `"1 stop"`, etc. |
| `duration` | `string` | Flight duration (e.g. `"13h 50m"`) |
| `price_usd` | `float` | Price per person in USD |
| `carrier_code` | `string` | Airline code or partner label |
| `loyalty_points_earned` | `int` | Points earned for this booking |
| `baggage_policy` | `string` | Human-readable baggage allowance |
| `pnr_status` | `string` | `"OPEN"`, `"GUARANTEED"`, `"LIMITED SEATS"` |
| `image_url` | `string` | High-quality image URL for gallery rendering |

---

### Hotel Object

Each hotel (both in `hotel_options[]` and the final `hotel`) looks like this:

```json
{
  "name": "Grand Hyatt Dubai",
  "nights": 8,
  "rating": 4.7,
  "price_per_night_usd": 150.0,
  "amenities": ["Free WiFi", "Pool", "Gym", "Breakfast"],
  "review_count": 1240,
  "tripadvisor_rating": 4.6,
  "cancellation_policy": "Free cancellation up to 72 hours before check-in.",
  "check_in_instructions": "Check-in from 3:00 PM. Photo ID required.",
  "amenities_icons": ["wifi", "pool", "fitness_center", "free_breakfast"],
  "image_url": "https://images.unsplash.com/photo-15660737..."
}
```

| Field | Type | Description |
|-------|------|-------------|
| `name` | `string` | Hotel name |
| `nights` | `int` | Number of nights |
| `rating` | `float` | Star rating (out of 5) |
| `price_per_night_usd` | `float` | Nightly rate in USD |
| `amenities` | `string[]` | Human-readable amenity list |
| `review_count` | `int` | Number of guest reviews |
| `tripadvisor_rating` | `float` | TripAdvisor score |
| `cancellation_policy` | `string` | Cancellation terms |
| `check_in_instructions` | `string` | How to check in |
| `amenities_icons` | `string[]` | Icon keys for UI rendering (e.g. `"wifi"`, `"pool"`, `"spa"`, `"free_breakfast"`, `"fitness_center"`, `"airport_shuttle"`, `"rooftop"`, `"room_service"`, `"beach_access"`, `"tour"`, `"cultural_activity"`, `"reception_bell"`) |
| `image_url` | `string` | High-quality image URL for gallery rendering |

---

### Weather Object

```json
{
  "date": "2025-08-10",
  "condition": "Sunny & Very Hot",
  "temperature_celsius": 42
}
```

---

### Safety Info Object

```json
{
  "safety_level": "Very High",
  "tips": ["Dubai is one of the safest cities..."],
  "restrictions": ["Certain medications may be restricted..."]
}
```

`safety_level` is one of: `"Very High"`, `"High"`, `"Moderate"`, `"Low"`, `"Very Low"`.

---

## Conversation Flow

Solara collects information in a strict sequence. It asks **one question at a time** and will not skip ahead. Here's the exact order:

| Step | What Solara Asks | Parameter Filled | `current_step` |
|------|-----------------|------------------|----------------|
| 1 | Where do you want to go? | `location` | `"location"` |
| 2 | When are you planning to travel? | `start_date`, `end_date` | `"dates"` |
| 3 | Who is traveling and what's your budget? | `travelers`, `budget` | `"travelers_budget"` |
| 4 | What kind of experience? | `experience` | `"experience"` |
| 5 | Which passport are you traveling on? | `citizenship` | `"citizenship"` |
| 6 | *(Auto)* Searches flights & hotels, presents 5 options each | `trip_guide` populated | `"selection"` |
| 7 | User picks an option | Final `flight` & `hotel` locked in | `"complete"` |
| 8 | Booking finalized (Pro) or checkout flagged (Basic) | `submitted` or `checkout_required` flips | `"complete"` |

You can also skip the sequential flow entirely by providing all parameters in a single message:

```json
{
  "message": "I want a solo trip to Dubai from August 10-18, moderate budget, mix of everything, US Passport.",
  "session_id": "quick-test",
  "user_id": "pro_tester"
}
```

Solara is smart enough to extract everything from one message and jump straight to searching.

---

## Frontend Decision Logic

Here's a simple cheat sheet for what the frontend should do based on the response flags:

```
// 1. Always render the chat message
renderChatBubble(response.ai_message)

// 2. Render the correct UI component based on current_step
switch (response.current_step) {
    case "location":
        showDestinationCards()       // Popular location cards from Figma
        break
    case "dates":
        showDatePicker()             // Calendar component
        break
    case "travelers_budget":
        showTravelerAndBudgetCards() // Solo/Couple/Family + Budget/Moderate/Luxury
        break
    case "experience":
        showExperienceCards()        // Relaxation, Adventure, Culture, etc.
        break
    case "citizenship":
        showPassportInput()          // Text input or dropdown
        break
    case "selection":
        showFlightGallery(response.trip_guide.flight_options)
        showHotelGallery(response.trip_guide.hotel_options)
        break
    case "complete":
        if (response.submitted) showSuccessScreen()
        if (response.checkout_required) showCheckoutButton()
        break
}

// 3. Update the progress tracker sidebar
if (response.parameters_extracted) {
    updateProgressTracker(response.parameters_extracted)
}
```

---

## Cancellation Flow

If a user mentions cancellation (e.g. "I want to cancel my trip"), Solara handles it within the same `/api/v1/chat` endpoint. No separate endpoint needed.

The AI will:
1. Ask the user to clarify which trip (if unclear).
2. Run an internal eligibility check.
3. Respond with one of:
   - **Eligible (>72 hrs before departure):** "You are eligible for a 100% refund in credits."
   - **Not Eligible (<72 hrs):** "Our policy requires cancellations at least 72 hours before departure."

---

## Error Responses

| Status Code | Meaning |
|-------------|---------|
| `200` | Success. JSON body contains the full response. |
| `403` | Invalid or missing `user_id`. User doesn't have an active subscription. |
| `500` | Internal server error. Check the `detail` field for specifics. |

Example 403:
```json
{
  "detail": "Active subscription required to use Solara. Please upgrade your plan."
}
```

---

## Notes for the Backend Team

- **Session Management:** Conversation history is stored server-side in SQLite, keyed by `session_id`. The frontend doesn't need to manage or pass history — just keep the `session_id` consistent within a conversation.
- **Mock Data:** Flight and hotel results are currently mock data. Each search returns 5 diverse options — 3 styled as GDS/API feeds (Amadeus, Booking.com) and 2 as curated partner deals. When we integrate real APIs (Amadeus, SerpAPI), the response structure stays identical.
- **Image URLs:** All flight and hotel options include `image_url` fields pointing to Unsplash. These are placeholder-quality but render perfectly for frontend gallery testing.
- **Submission Payload:** When `submit_trip_to_backend` fires (Pro users), it POSTs the full trip payload (location, dates, travelers, budget, experience, chosen flight/hotel details, user_id) to the configured internal API endpoint. In development mode, this is mocked and logged to console.

---

## Quick Test (Copy-Paste for Swagger)

Open `http://127.0.0.1:8000/docs`, expand `POST /api/v1/chat`, click "Try it out", and paste:

**Message 1:**
```json
{
  "message": "I want a solo trip to Tokyo from October 1st to 10th on a luxury budget for culture. US Passport.",
  "session_id": "docs-test-001",
  "user_id": "pro_tester"
}
```

**Message 2 (after receiving options):**
```json
{
  "message": "I'll take the first flight and the third hotel.",
  "session_id": "docs-test-001",
  "user_id": "pro_tester"
}
```

You should see `"submitted": true` in the response.

---

*If you have questions or need clarification on any of these schemas, reach out to me directly.*
