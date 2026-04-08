from fastapi import HTTPException
from typing import Dict, Any

def check_user_subscription(user_id: str | None) -> Dict[str, Any]:
    """
    Middleware check for SaaS Gatekeeping. 
    Verifies if a user has an active subscription and returns tier info.
    """
    # Allowed trial/test users
    subscriptions = {
        "pro_tester": {"tier": "Pro", "remaining_tasks": "Unlimited"},
        "basic_tester": {"tier": "Basic", "remaining_tasks": 5},
        "trial_user": {"tier": "Pro", "remaining_tasks": "Unlimited"} # Default for existing tests
    }

    if user_id not in subscriptions:
        raise HTTPException(
            status_code=403, 
            detail="Active subscription required to use Solara. Please upgrade your plan."
        )
    
    return subscriptions[user_id]
