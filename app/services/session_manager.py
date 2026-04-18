import json
import time
import aiosqlite
import os
import logging

logger = logging.getLogger("solara.session")

# SQLite database file path. 
DB_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "sessions.db")

_db_initialized = False

async def init_db():
    global _db_initialized
    if _db_initialized:
        return
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute('''
            CREATE TABLE IF NOT EXISTS chat_sessions (
                session_id TEXT PRIMARY KEY,
                history_json TEXT,
                last_updated REAL
            )
        ''')
        await db.commit()
    _db_initialized = True
    logger.info("Session database initialized")

async def get_session_history(session_id: str) -> list:
    """Retrieve chat history array for a specific session."""
    if not session_id:
        return []
        
    await init_db()
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute('SELECT history_json FROM chat_sessions WHERE session_id = ?', (session_id,)) as cursor:
            row = await cursor.fetchone()
            if row:
                return json.loads(row[0])
            return []

async def save_session_history(session_id: str, history: list):
    """Overwrite the chat history array for a session."""
    if not session_id:
        return
        
    now = time.time()
    history_json = json.dumps(history)
    
    await init_db()
    async with aiosqlite.connect(DB_PATH) as db:
        # Upsert logic (Insert or Replace)
        await db.execute('''
            INSERT OR REPLACE INTO chat_sessions (session_id, history_json, last_updated)
            VALUES (?, ?, ?)
        ''', (session_id, history_json, now))
        await db.commit()
