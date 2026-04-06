import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
import time
import json
import subprocess
import httpx

BASE_URL = "http://127.0.0.1:8000"
CHAT_URL = f"{BASE_URL}/api/v1/chat"

PAYLOAD = {
    "message": "I want to go to Dubai for a solo trip from March 10th to 18th on a moderate budget for a mix of everything. I am traveling on a US Passport.",
    "session_id": "test_session_123",
    "history": [],
}

GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BOLD = "\033[1m"
RESET = "\033[0m"


def ok(label):
    print(f"  {GREEN}✓{RESET} {label}")


def fail(label, detail=""):
    print(f"  {RED}✗{RESET} {label}")
    if detail:
        print(f"    {YELLOW}→ {detail}{RESET}")


def assert_check(condition, label, detail=""):
    if condition:
        ok(label)
        return True
    else:
        fail(label, detail)
        return False


def wait_for_server(timeout=20):
    start = time.time()
    while time.time() - start < timeout:
        try:
            r = httpx.get(f"{BASE_URL}/health", timeout=2)
            if r.status_code == 200:
                return True
        except Exception:
            pass
        time.sleep(1)
    return False


def run_test():
    PAYLOAD_UNAUTH = PAYLOAD.copy()
    PAYLOAD_UNAUTH["user_id"] = "invalid_user"
    
    print(f"\n{BOLD}-- Sending UNAUTHORIZED request to {CHAT_URL} --{RESET}")
    try:
        response_unauth = httpx.post(CHAT_URL, json=PAYLOAD_UNAUTH, timeout=10)
        if response_unauth.status_code == 403:
            ok("Status 403 Forbidden received as expected for invalid/missing user_id")
        else:
            fail(f"Expected 403, got {response_unauth.status_code}", response_unauth.text)
            return False
    except httpx.RequestError as e:
        print(f"{RED}Request failed: {e}{RESET}")
        return False

    PAYLOAD_AUTH = PAYLOAD.copy()
    PAYLOAD_AUTH["user_id"] = "trial_user"

    print(f"\n{BOLD}-- Sending AUTHORIZED request to {CHAT_URL} --{RESET}")
    print(f"  Message: \"{PAYLOAD_AUTH['message']}\"\n")

    try:
        response = httpx.post(CHAT_URL, json=PAYLOAD_AUTH, timeout=60)
    except httpx.RequestError as e:
        print(f"{RED}Request failed: {e}{RESET}")
        return False

    passed = 0
    total = 0

    def check(cond, label, detail=""):
        nonlocal passed, total
        total += 1
        if assert_check(cond, label, detail):
            passed += 1

    # ── HTTP layer ──────────────────────────────────────────
    print(f"{BOLD}HTTP{RESET}")
    check(response.status_code == 200, f"Status 200 (got {response.status_code})")

    try:
        data = response.json()
    except Exception:
        fail("Response is valid JSON", response.text[:300])
        return False

    # ── Top-level structure ─────────────────────────────────
    print(f"\n{BOLD}Top-level fields{RESET}")
    check("ai_message" in data, "ai_message present")
    check(bool(data.get("ai_message")), "ai_message is non-empty")
    check("trip_card" in data, "trip_card present")
    check(data.get("trip_card") is not None, "trip_card is not null")
    check("submitted" in data, "submitted flag is present")

    trip_card = data.get("trip_card") or {}

    # ── trip_card fields ────────────────────────────────────
    print(f"\n{BOLD}trip_card{RESET}")
    check(bool(trip_card.get("destination")), "destination present")
    check(
        "dubai" in str(trip_card.get("destination", "")).lower(),
        'destination contains "Dubai"',
        f"got: {trip_card.get('destination')}",
    )
    check(bool(trip_card.get("description")), "description present")
    check(isinstance(trip_card.get("rating"), (int, float)), "rating is a number")
    check(isinstance(trip_card.get("distance_km"), int), "distance_km is an integer")
    check(isinstance(trip_card.get("restaurants_available"), int), "restaurants_available is an integer")
    check(isinstance(trip_card.get("total_price_per_person"), int), "total_price_per_person is an integer")

    # ── parameters_extracted ────────────────────────────────
    print(f"\n{BOLD}parameters_extracted{RESET}")
    params = trip_card.get("parameters_extracted") or {}
    check(bool(params), "parameters_extracted present")
    check(
        "dubai" in str(params.get("location", "")).lower(),
        'location = "Dubai"',
        f"got: {params.get('location')}",
    )
    check(
        params.get("travelers") == "Solo",
        'travelers = "Solo"',
        f"got: {params.get('travelers')}",
    )
    check(
        params.get("budget") == "Moderate",
        'budget = "Moderate"',
        f"got: {params.get('budget')}",
    )
    check(
        params.get("experience") == "Mix of everything",
        'experience = "Mix of everything"',
        f"got: {params.get('experience')}",
    )
    check(
        params.get("citizenship") is not None,
        'citizenship is extracted',
        f"got: {params.get('citizenship')}",
    )
    check(bool(params.get("start_date")), "start_date extracted")
    check(bool(params.get("end_date")), "end_date extracted")

    # ── trip_guide (optional but expected here) ─────────────
    print(f"\n{BOLD}trip_guide{RESET}")
    trip_guide = data.get("trip_guide") or {}
    check(bool(trip_guide), "trip_guide present")
    check(bool(trip_guide.get("flight")), "flight info present")
    check(bool(trip_guide.get("hotel")), "hotel info present")
    check(bool(trip_guide.get("weather")), "weather info present")
    check(isinstance(trip_guide.get("travel_tips"), list), "travel_tips is a list")
    check(isinstance(trip_guide.get("culture_etiquette"), list), "culture_etiquette is a list")
    check(bool(trip_guide.get("safety_info")), "safety_info present")

    # ── Summary ─────────────────────────────────────────────
    print(f"\n{BOLD}-- Full Response JSON --{RESET}")
    print(json.dumps(data, indent=2))

    status = f"{GREEN}PASSED{RESET}" if passed == total else f"{RED}FAILED{RESET}"
    print(f"\n{BOLD}Result: {status} — {passed}/{total} checks passed{RESET}\n")
    return passed == total


def main():
    server_proc = None
    server_already_up = False

    # Check if server is already running
    try:
        r = httpx.get(f"{BASE_URL}/health", timeout=2)
        if r.status_code == 200:
            server_already_up = True
            print(f"{GREEN}Server already running at {BASE_URL}{RESET}")
    except Exception:
        pass

    if not server_already_up:
        print(f"{YELLOW}Starting uvicorn server...{RESET}")
        server_proc = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "app.main:app", "--port", "8000"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        if not wait_for_server(timeout=20):
            print(f"{RED}Server failed to start within 20 seconds.{RESET}")
            server_proc.terminate()
            sys.exit(1)
        print(f"{GREEN}Server ready.{RESET}")

    try:
        success = run_test()
    finally:
        if server_proc:
            server_proc.terminate()
            print(f"{YELLOW}Server stopped.{RESET}")

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
