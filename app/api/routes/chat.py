from fastapi import APIRouter, HTTPException
from app.schemas import ChatRequest, ChatResponse, ExtractedParameters
from app.services.ai_agent import run_agent
from app.services.auth_service import check_user_subscription

router = APIRouter()


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    # 1. SaaS Gatekeeping (Will raise its own 403 HTTPException if invalid)
    check_user_subscription(request.user_id)

    try:
        # 2. Agent Execution
        result = await run_agent(request.message, request.history, user_id=request.user_id)
        
        # Build ChatResponse directly. `run_agent` returns the json dict natively.
        return ChatResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
