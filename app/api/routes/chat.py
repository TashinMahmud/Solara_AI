from fastapi import APIRouter, HTTPException
from app.schemas import ChatRequest, ChatResponse, ExtractedParameters, ChatMessage
from app.services.ai_agent import run_agent
from app.services.auth_service import check_user_subscription
from app.services.session_manager import get_session_history, save_session_history

router = APIRouter()


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    # 1. SaaS Gatekeeping (Will raise its own 403 HTTPException if invalid)
    user_status = check_user_subscription(request.subscription_plan)

    try:
        # 2. Database History Loading
        raw_db_history = await get_session_history(request.session_id)
        parsed_history = [ChatMessage(**msg) for msg in raw_db_history]

        # 3. Agent Execution
        result = await run_agent(request.message, parsed_history, subscription_plan=request.subscription_plan, user_status=user_status)
        
        # 4. Database History Saving
        # Instead of the frontend passing huge arrays back and forth, the backend secretly appends the exchanges.
        import json
        raw_db_history.append({"role": "user", "content": request.message})
        # MUST save the full JSON result to history so Claude sees its previous JSON outputs and maintains the format!
        raw_db_history.append({"role": "assistant", "content": json.dumps(result)})
        await save_session_history(request.session_id, raw_db_history)

        # Inject session_id back into the response payload
        result["session_id"] = request.session_id

        # Build ChatResponse directly. `run_agent` returns the json dict natively.
        return ChatResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
