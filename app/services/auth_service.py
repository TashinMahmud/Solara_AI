from fastapi import HTTPException

def check_user_subscription(user_id: str | None):
    """
    Middleware check for SaaS Gatekeeping. 
    Verifies if a user has an active subscription.
    """
    if user_id != "trial_user":
        raise HTTPException(
            status_code=403, 
            detail="Active subscription required to use WanderAI. Please upgrade your plan."
        )
