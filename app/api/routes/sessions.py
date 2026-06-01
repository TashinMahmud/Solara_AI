from fastapi import APIRouter, HTTPException
from app.services.session_manager import delete_all_sessions, get_session_history

router = APIRouter()

@router.get("/{session_id}/messages")
async def get_messages(session_id: str):
    """
    Returns the full chat history for a given session_id.
    Each entry has a 'role' (user/assistant) and 'content'.
    """
    history = await get_session_history(session_id)
    if not history:
        raise HTTPException(status_code=404, detail=f"No session found with id '{session_id}'.")
    return {"session_id": session_id, "message_count": len(history), "messages": history}

@router.delete("/clear-all")
async def clear_all():
    """
    Wipes the entire local SQLite session database.
    Use this during testing to reset message counts and history.
    """
    await delete_all_sessions()
    return {"status": "success", "message": "All chat sessions cleared from database."}
