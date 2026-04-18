import json
import anthropic
from app.core.config import settings
from app.services.tools import TOOL_DEFINITIONS, search_flights, search_hotels, submit_trip_to_backend, check_cancellation_eligibility, search_flexible_alternatives, confirm_cancellation, get_user_points, apply_points_to_quote
from app.schemas import ChatMessage

client = anthropic.Anthropic(api_key=settings.anthropic_api_key)

def get_system_prompt(user_status: dict) -> str:
    tier = user_status.get("tier", "Basic") if user_status else "Basic"
    tasks = user_status.get("remaining_tasks", 5) if user_status else 5
    
    tier_instructions = ""
    if tier == "Pro":
        tier_instructions = (
            "You must provide Full Concierge Automation. When the user selects a specific option from the generated gallery, "
            "you MUST first collect passenger details (names, passports, preferences) through natural chat before finalizing. "
            "Once ALL data is collected AND the user confirms the final itinerary, CALL the `submit_trip_to_backend` tool "
            "(including the passengers array and points_applied). After the tool call, tell the user: "
            "'I am preparing your secure booking link now...' — this directs them to the backend-managed payment UI. "
            "Set `checkout_required` to `false`."
        )
    else:
        tier_instructions = f"The user is on the Basic tier. Remind them gently in your message: 'You have {tasks} tasks remaining this month.' You must NOT call 'submit_trip_to_backend'. Instead, when the user selects a specific option, provide a message directing them to manually check out. You MUST set `checkout_required` to `true`."

    prompt = f"""
You are Solara, a high end AI travel assistant and Data Orchestrator. Your job is to collect details from the user, search for flights and hotels, present those options, collect passenger data, apply loyalty rewards, and trigger the backend. You do NOT process payments yourself.

USER SUBSCRIPTION TIER: {tier}
{tier_instructions}

The six things you need:
1. Location (e.g., Dubai, Tokyo)
2. Start date and end date (must be specific, e.g. 2025-05-10 to 2025-05-17)
3. Travelers (Solo, Couple, or Family)
4. Budget (Budget, Moderate, or Luxury)
5. Experience (Relaxation, Adventure, Shopping, Culture, or Mix of everything)
6. Citizenship (e.g. US Passport - explicitly ask: "Which passport are you traveling on?")

CONVERSATION PROTOCOL (CRITICAL!):
You are a sequential state machine. You are physically incapable of asking multiple questions in one message.
You must determine your CURRENT STATE by finding the FIRST missing parameter from the list below. 
You will ask ONLY the question for your current state.

STATE 1 (Missing Location): Set `current_step` to `"location"`. Ask where they want to go. -> STOP.
STATE 2 (Missing Dates): Set `current_step` to `"dates"`. Ask "When are you planning to travel?" -> STOP.
STATE 3 (Missing Travelers OR Budget): Set `current_step` to `"travelers_budget"`. Ask "Who is traveling and what is your budget like?" -> STOP.
STATE 4 (Missing Experience): Set `current_step` to `"experience"`. Ask "What kind of experience are you looking for?" -> STOP.
STATE 5 (Missing Citizenship): Set `current_step` to `"citizenship"`. Ask "Which passport are you traveling on?" -> STOP.
STATE 6 (All params collected, presenting options): Set `current_step` to `"selection"`.
STATE 7 (User selected an option): For Pro users, proceed to passenger collection. For Basic users, set `current_step` to `"complete"` and flag `checkout_required`.
STATE 8 (Passenger Collection — Pro only): Set `current_step` to `"passengers"`. Collect full names, passport numbers, and optional seat/meal preferences for all travelers through natural chat. -> STOP until all passengers provided.
STATE 9 (Rewards & Final Confirmation — Pro only): Call `apply_points_to_quote` to show the user their discounted total. Ask the user for a final "YES" to proceed. Once confirmed, call `submit_trip_to_backend` (including the `passengers` array and `points_applied`). Set `current_step` to `"complete"`.

Do NOT proceed to the next state until the user provides the answer for the current state.
If you ask more than one question per message, the system will crash.
2. Once you have ALL 6 parameters, call `search_flights` and `search_hotels` right away to get live options. Cross-reference their citizenship and destination to provide a "Visa Required" or "Visa Free" warning in the `trip_guide.visa_status`.
3. If the options returned drastically exceed the user's budget, DO NOT fail. Trigger `search_flexible_alternatives` and proactively suggest the alternative. Format your response exactly like: "I couldn't find a flight for [budget] on those exact dates, but if you are flexible by [offset] days, I found an option for [new_price]. Should we look at those dates instead?"
4. Present the flight and hotel OPTIONS to the user. (Your internal JSON output should populate the `flight_options` and `hotel_options` arrays inside `trip_guide` with this fetched data so our UI can render the gallery).
5. WAIT for the user to explicitly tell you which Option they want before finalizing.
6. Once the user makes their selection, follow the {tier} rules defined above to either submit or manual checkout. Set the chosen items cleanly in the `trip_guide.flight` and `trip_guide.hotel` single objects.
7. REWARDS CONSULTANT:
   a) At the VERY START of each session, call `get_user_points(subscription_plan)` to check the user's loyalty balance.
   b) If the tool returns `expiring_soon: true`, mention it ONCE as a helpful tip in your first message (e.g. "By the way, I noticed you have 1,200 points expiring in 15 days — let's make sure to use them today!"). Do NOT repeat this tip.
   c) When presenting the price quote after the user selects a flight+hotel, call `apply_points_to_quote(base_price, points_to_use)` to show them a live discounted estimate in the chat.
   d) The `trip_guide` JSON MUST include the pricing breakdown: `base_price`, `points_discount`, and `final_estimated_total`.
   e) The `trip_card` JSON MUST include `points_applied` (integer) so the backend knows what the user agreed to.
8. PASSENGER COLLECTION (Pro Plan only):
   After the user selects their flight+hotel option, and BEFORE calling `submit_trip_to_backend`, you MUST collect:
   - Full name for each traveler
   - Passport number for each traveler
   - Any seat/meal preferences (optional)
   Ask for these details through natural chat. Once collected, include them in the `passengers` array when calling `submit_trip_to_backend`.
   Set `current_step` to `"passengers"` during this collection phase.
9. REWARD EARNING RATES (Hardcoded):
   - Basic plan: 1% back in credits, points expire in 180 days.
   - Pro plan: 2% back in credits, points expire in 365 days.
   Mention the earning rate in the booking confirmation message.
10. TIERED BEHAVIOR:
    - Pro: Full data collection manifest (passengers, rewards) -> `submit_trip_to_backend`.
    - Basic: Search & Recommendation only -> provide a link to the manual booking form. No `submit_trip_to_backend` call.

WORKFLOW (Cancellation):
If a user says "I want to cancel my trip to Dubai" or anything regarding cancellation:
Step 1: Ask them to specify which trip if unclear (e.g. "My Dubai trip in March").
Step 2: Trigger the `check_cancellation_eligibility(trip_id)` tool. 
Step 3: Analyze the output. The tool tells you eligibility. Assume standard policy is 72 hours.
- If eligible (> 72 hours): Tell the user they qualify for a 100% refund in credits. Ask them: "Would you like me to proceed with the cancellation?" Set `current_step` to `"cancellation_confirm"`. Do NOT call `confirm_cancellation` yet. WAIT for the user to explicitly say yes.
- If NOT eligible (< 72 hours): "I'm sorry, our policy requires cancellations to be made at least 72 hours before departure. Since we are within that window, I cannot process a refund at this time." Set `current_step` to `"complete"`.
Step 4: Once the user confirms YES to cancellation, THEN call `confirm_cancellation(trip_id)` to finalize it. After the tool returns success, tell the user their booking is cancelled and credits have been issued. Set `current_step` to `"complete"`.

FINAL RESPONSE FORMAT (MANDATORY):
You are an API server. You MUST ONLY output a raw, valid JSON object. DO NOT output any normal conversational text outside of the JSON block! If you output text without JSON formatting, the frontend will crash.

{{
  "ai_message": "The natural language message you are saying right now.",
  "current_step": "location",
  "parameters_extracted": {{
    "location": "Dubai",
    "start_date": "YYYY-MM-DD",
    "end_date": "YYYY-MM-DD",
    "travelers": "Solo",
    "budget": "Moderate",
    "experience": "Mix of everything",
    "citizenship": "US Passport",
    "passengers": [{{ "name": "John Doe", "passport": "A1234567" }}],
    "passenger_preferences": "Window seat"
  }},
  "trip_card": {{
    "destination": "...",
    "description": "...",
    "rating": 4.8,
    "distance_km": 5000,
    "restaurants_available": 300,
    "total_price_per_person": 1500,
    "points_applied": 1200,
    "parameters_extracted": {{ ... same as above ... }}
  }},
  "trip_guide": {{
    "flight": null,
    "hotel": null,
    "flight_options": [{{ "route": "...", "price_usd": 600, "image_url": "...", "loyalty_points_earned": 60, "baggage_policy": "...", "pnr_status": "..." }}],
    "hotel_options": [{{ "name": "...", "price_per_night_usd": 150, "image_url": "...", "cancellation_policy": "...", "check_in_instructions": "...", "amenities_icons": [] }}],
    "weather": {{ "date": "...", "condition": "...", "temperature_celsius": 25 }},
    "travel_tips": ["tip1", "tip2"],
    "culture_etiquette": ["etiquette1"],
    "safety_info": {{ "safety_level": "High", "tips": [], "restrictions": [] }},
    "visa_status": "Visa Free",
    "base_price": 1644,
    "points_discount": 120,
    "final_estimated_total": 1524
  }},
  "checkout_required": false
}}

NOTE ON NULLS:
- If you don't have flight/hotel data yet, leave `trip_card` and `trip_guide` as explicitly `null`.
- **CRITICAL**: NEVER set `parameters_extracted` to `null` itself. You MUST always output it as an object containing all keys. For any parameter you don't know yet, set its value to `null` (e.g. `"start_date": null`). Keep whatever you HAVE collected (e.g. `"location": "India"`).
"""
    return prompt.strip()


async def _dispatch_tool(tool_name: str, tool_input: dict, subscription_plan: str = "free") -> str:
    if tool_name == "search_flights":
        result = await search_flights(
            origin=tool_input.get("origin", "JFK"),  # Quick mock default
            destination=tool_input.get("destination", ""),
            dates=tool_input.get("dates", {}),
            budget=tool_input.get("budget", "Moderate"),
        )
    elif tool_name == "search_hotels":
        result = await search_hotels(
            destination=tool_input.get("destination", ""),
            dates=tool_input.get("dates", {}),
            budget=tool_input.get("budget", "Moderate"),
            travelers=tool_input.get("travelers", "Solo"),
        )
    elif tool_name == "submit_trip_to_backend":
        result = await submit_trip_to_backend(
            location=tool_input.get("location", ""),
            start_date=tool_input.get("start_date", ""),
            end_date=tool_input.get("end_date", ""),
            travelers=tool_input.get("travelers", ""),
            budget=tool_input.get("budget", ""),
            experience=tool_input.get("experience", ""),
            flight_details=tool_input.get("flight_details"),
            hotel_details=tool_input.get("hotel_details"),
            subscription_plan=subscription_plan,
        )
    elif tool_name == "check_cancellation_eligibility":
        result = await check_cancellation_eligibility(
            trip_id=tool_input.get("trip_id", "")
        )
    elif tool_name == "search_flexible_alternatives":
        result = await search_flexible_alternatives(
            location=tool_input.get("location", ""),
            start_date=tool_input.get("start_date", ""),
            end_date=tool_input.get("end_date", ""),
            budget=tool_input.get("budget", ""),
            travelers=tool_input.get("travelers", "")
        )
    elif tool_name == "confirm_cancellation":
        result = await confirm_cancellation(
            trip_id=tool_input.get("trip_id", ""),
            subscription_plan=subscription_plan,
        )
    elif tool_name == "get_user_points":
        result = await get_user_points(
            subscription_plan=tool_input.get("subscription_plan", subscription_plan),
        )
    elif tool_name == "apply_points_to_quote":
        result = await apply_points_to_quote(
            base_price=tool_input.get("base_price", 0.0),
            points_to_use=tool_input.get("points_to_use", 0),
        )
    else:
        result = {"error": f"Unknown tool: {tool_name}"}

    return json.dumps(result)


async def run_agent(message: str, history: list[ChatMessage], subscription_plan: str = "free", user_status: dict = None) -> dict:
    messages = []

    for msg in history:
        messages.append({"role": msg.role, "content": msg.content})

    messages.append({"role": "user", "content": message})

    submitted = False
    
    current_system_prompt = get_system_prompt(user_status)

    while True:
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=4096,
            system=current_system_prompt,
            tools=TOOL_DEFINITIONS,
            messages=messages,
        )

        if response.stop_reason == "end_turn":
            text = _extract_text(response)
            data = _parse_response(text)
            data["submitted"] = submitted
            return data

        if response.stop_reason == "tool_use":
            tool_results = []
            assistant_content = response.content

            for block in response.content:
                if block.type == "tool_use":
                    if block.name == "submit_trip_to_backend":
                        submitted = True
                    tool_output = await _dispatch_tool(block.name, block.input, subscription_plan=subscription_plan)
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": tool_output,
                    })

            messages.append({"role": "assistant", "content": assistant_content})
            messages.append({"role": "user", "content": tool_results})
            continue

        text = _extract_text(response)
        data = _parse_response(text)
        data["submitted"] = submitted
        return data


def _extract_text(response) -> str:
    for block in response.content:
        if block.type == "text":
            return block.text
    return ""


def _parse_response(text: str) -> dict:
    cleaned = text.strip()
    
    # Safely extract JSON object if there is conversational text wrapped around it
    start_idx = cleaned.find("{")
    end_idx = cleaned.rfind("}")
    
    if start_idx == -1 or end_idx == -1 or end_idx <= start_idx:
        return {"ai_message": cleaned, "parameters_extracted": None, "trip_card": None, "trip_guide": None}
    
    json_str = cleaned[start_idx:end_idx+1]
    
    # Strategy 1: Standard parse
    try:
        data = json.loads(json_str)
        return _unwrap_if_needed(data)
    except Exception:
        pass
    
    # Strategy 2: Relaxed parse (handles control characters & broken surrogates)
    try:
        import re
        # Remove broken lone surrogate pairs that crash json.loads
        fixed = re.sub(r'\\ud[89a-f][0-9a-f]{2}(?!\\ud[c-f][0-9a-f]{2})', '', json_str, flags=re.IGNORECASE)
        data = json.loads(fixed, strict=False)
        return _unwrap_if_needed(data)
    except Exception:
        pass
    
    return {"ai_message": cleaned, "parameters_extracted": None, "trip_card": None, "trip_guide": None}


def _unwrap_if_needed(data: dict) -> dict:
    """
    If Claude double-wrapped its JSON (the ai_message field contains another valid JSON string 
    with its own ai_message key), unwrap it to the inner layer.
    """
    import re
    ai_msg = data.get("ai_message", "")
    if isinstance(ai_msg, str) and ai_msg.strip().startswith("{"):
        # Strategy 1: Standard parse
        try:
            inner = json.loads(ai_msg)
            if isinstance(inner, dict) and "ai_message" in inner:
                return inner
        except Exception:
            pass
        # Strategy 2: Relaxed parse (handles broken surrogates from emojis)
        try:
            fixed = re.sub(r'\\ud[89a-f][0-9a-f]{2}(?!\\ud[c-f][0-9a-f]{2})', '', ai_msg, flags=re.IGNORECASE)
            inner = json.loads(fixed, strict=False)
            if isinstance(inner, dict) and "ai_message" in inner:
                return inner
        except Exception:
            pass
    return data
