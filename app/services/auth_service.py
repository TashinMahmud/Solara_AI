from fastapi import HTTPException
from typing import Dict, Any
from app.core.config import settings
import httpx

MOCK_MODE = settings.app_env == "development"

def check_user_subscription(subscription_plan: str | None) -> Dict[str, Any]:
    """
    Middleware check for SaaS Gatekeeping. 
    Verifies the user's subscription tier.
    Limits are enforced locally by the AI service based on the provided plan.
    """
    safe_plan = (subscription_plan or "free").lower()
    
    if safe_plan == "pro":
        return {"tier": "Pro", "remaining_tasks": "Unlimited"}
    elif safe_plan == "basic":
        return {"tier": "Basic", "remaining_tasks": "Unlimited"}
    else:
        return {"tier": "Free", "remaining_tasks": 5}

