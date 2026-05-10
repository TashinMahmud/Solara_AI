import json
import logging
from fastapi import APIRouter, HTTPException
from app.schemas import ChatRequest, ChatResponse, ExtractedParameters, ChatMessage
from app.services.ai_agent import run_agent
from app.services.auth_service import check_user_subscription
from app.services.session_manager import get_session_history, save_session_history

router = APIRouter()
logger = logging.getLogger("solara.chat")


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    # 1. SaaS Gatekeeping (Will raise its own 403 HTTPException if invalid)
    user_status = check_user_subscription(request.subscription_plan)

    try:
        # 2. Database History Loading
        raw_db_history = await get_session_history(request.session_id)
        parsed_history = [ChatMessage(**msg) for msg in raw_db_history]

        # 3. Free Tier Enforcement: count user turns in history and block if exhausted
        remaining = user_status.get("remaining_tasks", "Unlimited")
        if remaining != "Unlimited":
            user_turns = sum(1 for msg in raw_db_history if msg.get("role") == "user")
            if user_turns >= remaining:
                logger.warning(f"Free tier limit reached for session {request.session_id} ({user_turns}/{remaining})")
                return ChatResponse(
                    session_id=request.session_id,
                    user_id=request.user_id,
                    ai_message=f"You've used all {remaining} free task(s) this month. Upgrade to Basic or Pro for more.",
                    current_step=None,
                    parameters_extracted=None,
                    trip_card=None,
                    trip_guide=None,
                    submitted=False,
                    checkout_required=False,
                    rate_limit_exceeded=True
                )

        # 4. Agent Execution
        logger.info(f"Chat request | session={request.session_id} | plan={request.subscription_plan} | user={request.user_id}")
        result = await run_agent(
            message=request.message,
            history=parsed_history,
            user_id=request.user_id,
            subscription_plan=request.subscription_plan,
            user_status=user_status
        )
        
        # 5. Database History Saving
        raw_db_history.append({"role": "user", "content": request.message})
        raw_db_history.append({"role": "assistant", "content": json.dumps(result)})
        await save_session_history(request.session_id, raw_db_history)

        # Inject session_id and user_id back into the response payload
        result["session_id"] = request.session_id
        result["user_id"] = request.user_id

        return ChatResponse(**result)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Chat error: {type(e).__name__}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
