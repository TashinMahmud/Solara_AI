import json
import anthropic
from app.core.config import settings
from app.services.tools import TOOL_DEFINITIONS, search_flights, search_hotels, submit_trip_to_backend, check_cancellation_eligibility, search_flexible_alternatives
from app.schemas import ChatMessage

client = anthropic.Anthropic(api_key=settings.anthropic_api_key)

def get_system_prompt(user_status: dict) -> str:
    tier = user_status.get("tier", "Basic") if user_status else "Basic"
    tasks = user_status.get("remaining_tasks", 5) if user_status else 5
    
    tier_instructions = ""
    if tier == "Pro":
        tier_instructions = "You must provide Full Concierge Automation. When the user selects a specific option from the generated gallery, you MUST explicitly tell the user 'I am preparing your secure booking link now...' and CALL the `submit_trip_to_backend` tool to finalize the booking."
    else:
        tier_instructions = f"The user is on the Basic tier. Remind them gently in your message: 'You have {tasks} tasks remaining this month.' You must NOT call 'submit_trip_to_backend'. Instead, when the user selects a specific option, provide a message directing them to the manual checkout page ('checkout/XYZ') and explicitly tell them they must proceed there to conclude the booking."

    prompt = f"""
You are Solara, a friendly AI travel assistant. Your job is to collect 5 details from the user, search for flights and hotels, present those options, and guide the user.

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

STATE 1 (Missing Location): Ask where they want to go. -> STOP.
STATE 2 (Missing Dates): Ask "When are you planning to travel?" -> STOP.
STATE 3 (Missing Travelers OR Budget): Ask "Who is traveling and what is your budget like?" -> STOP.
STATE 4 (Missing Experience): Ask "What kind of experience are you looking for?" -> STOP.
STATE 5 (Missing Citizenship): Ask "Which passport are you traveling on?" -> STOP.

Do NOT proceed to the next state until the user provides the answer for the current state.
If you ask more than one question per message, the system will crash.
2. Once you have ALL 6 parameters, call `search_flights` and `search_hotels` right away to get live options. Cross-reference their citizenship and destination to provide a "Visa Required" or "Visa Free" warning in the `trip_guide.visa_status`.
3. If the options returned drastically exceed the user's budget, DO NOT fail. Trigger `search_flexible_alternatives` and proactively suggest the alternative. Format your response exactly like: "I couldn't find a flight for [budget] on those exact dates, but if you are flexible by [offset] days, I found an option for [new_price]. Should we look at those dates instead?"
4. Present the flight and hotel OPTIONS to the user. (Your internal JSON output should populate the `flight_options` and `hotel_options` arrays inside `trip_guide` with this fetched data so our UI can render the gallery).
5. WAIT for the user to explicitly tell you which Option they want before finalizing.
6. Once the user makes their selection, follow the {tier} rules defined above to either submit or manual checkout. Set the chosen items cleanly in the `trip_guide.flight` and `trip_guide.hotel` single objects.

WORKFLOW (Cancellation):
If a user says "I want to cancel my trip to Dubai" or anything regarding cancellation:
Step 1: Ask them to specify which trip if unclear (e.g. "My Dubai trip in March").
Step 2: Trigger the `check_cancellation_eligibility(trip_id)` tool. 
Step 3: Analyze the output. The tool tells you eligibility. Assume standard policy is 72 hours.
- If eligible (> 72 hours): "I've checked your booking... Since we are more than 72 hours away, you are eligible for a 100% refund in credits. To finalize this and receive your credits within 2-3 days, please click the 'Confirm Cancellation' button that I've just highlighted in your My Trip dashboard."
- If NOT eligible (< 72 hours): "I'm sorry, our policy requires cancellations to be made at least 72 hours before departure. Since we are within that window, I cannot process a refund at this time."

FINAL RESPONSE FORMAT (MANDATORY):
You are an API server. You MUST ONLY output a raw, valid JSON object. DO NOT output any normal conversational text outside of the JSON block! If you output text without JSON formatting, the frontend will crash.

{{
  "ai_message": "The natural language message you are saying right now.",
  "parameters_extracted": {{
    "location": "Dubai",
    "start_date": "YYYY-MM-DD",
    "end_date": "YYYY-MM-DD",
    "travelers": "Solo",
    "budget": "Moderate",
    "experience": "Mix of everything",
    "citizenship": "US Passport"
  }},
  "trip_card": {{
    "destination": "...",
    "description": "...",
    "rating": 4.8,
    "distance_km": 5000,
    "restaurants_available": 300,
    "total_price_per_person": 1500,
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
    "visa_status": "Visa Free"
  }}
}}

NOTE ON NULLS:
- If you don't have flight/hotel data yet, leave `trip_card` and `trip_guide` as explicitly `null`.
- **CRITICAL**: NEVER set `parameters_extracted` to `null` itself. You MUST always output it as an object containing all 7 keys. For any parameter you don't know yet, set its value to `null` (e.g. `"start_date": null`). Keep whatever you HAVE collected (e.g. `"location": "India"`).
"""
    return prompt.strip()


async def _dispatch_tool(tool_name: str, tool_input: dict, user_id: str = None) -> str:
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
            user_id=user_id,
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
    else:
        result = {"error": f"Unknown tool: {tool_name}"}

    return json.dumps(result)


async def run_agent(message: str, history: list[ChatMessage], user_id: str = None, user_status: dict = None) -> dict:
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
                    tool_output = await _dispatch_tool(block.name, block.input, user_id=user_id)
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
    try:
        start_idx = cleaned.find("{")
        end_idx = cleaned.rfind("}")
        if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
            json_str = cleaned[start_idx:end_idx+1]
            data = json.loads(json_str)
            return data
    except Exception:
        pass

    return {"ai_message": cleaned, "parameters_extracted": None, "trip_card": None, "trip_guide": None}
