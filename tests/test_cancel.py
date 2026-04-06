import httpx
import json

CHAT_URL = "http://127.0.0.1:8000/api/v1/chat"

PAYLOAD = {
    "message": "I need to cancel my Dubai trip please.",
    "history": [],
    "user_id": "trial_user"
}

def confirm_cancel():
    print(f"Sending Cancellation Request...")
    r = httpx.post(CHAT_URL, json=PAYLOAD, timeout=60)
    data = r.json()
    ai_message = data.get("ai_message", "")
    print(f"\nAI Response:\n{ai_message}\n")
    if "72 hours" in ai_message or "My Trip dashboard" in ai_message:
        print("SUCCESS! AI evaluated cancellation tool and outputted the correct dashboard workflow.")
    else:
        print("WARNING! AI did not output the formal cancellation rule phrasing.")

import subprocess, time, sys
server_proc = subprocess.Popen(
    [sys.executable, "-m", "uvicorn", "app.main:app", "--port", "8000"],
    stdout=subprocess.DEVNULL,
    stderr=subprocess.DEVNULL,
)
time.sleep(2)  # wait for server
try:
    confirm_cancel()
finally:
    server_proc.terminate()
