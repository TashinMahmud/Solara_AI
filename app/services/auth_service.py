from fastapi import HTTPException
from typing import Dict, Any
from app.core.config import settings
import httpx

MOCK_MODE = settings.app_env == "development"

def check_user_subscription(subscription_plan: str | None) -> Dict[str, Any]:
    """
    Middleware check for SaaS Gatekeeping. 
    Verifies the user's subscription tier.
    In production: calls the backend team's subscription/auth API.
    """
    safe_plan = (subscription_plan or "free").lower()
    
    if MOCK_MODE:
        if safe_plan == "pro":
            return {"tier": "Pro", "remaining_tasks": "Unlimited"}
        elif safe_plan == "basic":
            return {"tier": "Basic", "remaining_tasks": 5}
        else:
            return {"tier": "Free", "remaining_tasks": 1}

    # Production: verify against backend subscription API
    try:
        with httpx.Client(timeout=10.0) as client:
            res = client.get(
                f"{settings.internal_api_loyalty}/subscription",
                params={"plan": safe_plan}
            )
            res.raise_for_status()
            data = res.json()
            # Expected response: { "tier": "Pro"|"Basic", "remaining_tasks": int|"Unlimited" }
            return data
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            raise HTTPException(
                status_code=403,
                detail="Active subscription required to use Solara. Please upgrade your plan."
            )
        raise HTTPException(status_code=502, detail="Subscription service unavailable.")
    except httpx.RequestError:
        raise HTTPException(status_code=502, detail="Subscription service unavailable.")

