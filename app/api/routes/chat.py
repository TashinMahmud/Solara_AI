from fastapi import APIRouter, HTTPException
from app.schemas import ChatRequest, ChatResponse, ExtractedParameters, ChatMessage
from app.services.ai_agent import run_agent
from app.services.auth_service import check_user_subscription
from app.services.session_manager import get_session_history, save_session_history

router = APIRouter()


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    # 1. SaaS Gatekeeping (Will raise its own 403 HTTPException if invalid)
    check_user_subscription(request.user_id)

    try:
        # 2. Database History Loading
        raw_db_history = await get_session_history(request.session_id)
        parsed_history = [ChatMessage(**msg) for msg in raw_db_history]

        # 3. Agent Execution
        result = await run_agent(request.message, parsed_history, user_id=request.user_id)
        
        # 4. Database History Saving
        # Instead of the frontend passing huge arrays back and forth, the backend secretly appends the exchanges.
        raw_db_history.append({"role": "user", "content": request.message})
        raw_db_history.append({"role": "assistant", "content": result["ai_message"]})
        await save_session_history(request.session_id, raw_db_history)

        # Build ChatResponse directly. `run_agent` returns the json dict natively.
        return ChatResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
