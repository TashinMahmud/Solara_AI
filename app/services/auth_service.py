from fastapi import HTTPException
from typing import Dict, Any
from app.core.config import settings
import httpx

MOCK_MODE = settings.app_env == "development"

def check_user_subscription(user_id: str | None) -> Dict[str, Any]:
    """
    Middleware check for SaaS Gatekeeping. 
    Verifies if a user has an active subscription and returns tier info.
    In production: calls the backend team's subscription/auth API.
    """
    if MOCK_MODE:
        # Allowed trial/test users
        subscriptions = {
            "pro_tester": {"tier": "Pro", "remaining_tasks": "Unlimited"},
            "basic_tester": {"tier": "Basic", "remaining_tasks": 5},
            "trial_user": {"tier": "Pro", "remaining_tasks": "Unlimited"}
        }

        if user_id not in subscriptions:
            raise HTTPException(
                status_code=403, 
                detail="Active subscription required to use Solara. Please upgrade your plan."
            )
        
        return subscriptions[user_id]

    # Production: verify against backend subscription API
    try:
        with httpx.Client(timeout=10.0) as client:
            res = client.get(
                f"{settings.internal_api_loyalty}/subscription",
                params={"user_id": user_id}
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

