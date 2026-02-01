
import requests
import json
import time

BASE_URL = "http://127.0.0.1:5000"

def run_e2e_flow():
    print("Starting E2E API Flow Test...")
    
    # 1. GET Current Status
    print("[1/5] Checking Bot Status...")
    res = requests.get(f"{BASE_URL}/api/bot_status")
    initial_status = res.json().get('active')
    print(f"      Initial Status: {'ONLINE' if initial_status else 'PAUSED'}")

    # 2. Add a Test Symbol
    test_symbol = "PEPE/USDT:USDT"
    print(f"[2/5] Adding Symbol {test_symbol}...")
    res = requests.post(f"{BASE_URL}/api/symbols/add", json={"symbol": test_symbol})
    if res.status_code == 200:
        print("      Success: Symbol added.")
    else:
        print(f"      Note: {res.json().get('message')}")

    # 3. Toggle Bot
    print("[3/5] Toggling Bot Power...")
    res = requests.post(f"{BASE_URL}/api/toggle_bot")
    new_status = res.json().get('active')
    print(f"      New Status: {'ONLINE' if new_status else 'PAUSED'}")
    assert new_status != initial_status

    # 4. Fetch Global Data (Verifying Caching)
    print("[4/5] Fetching Dashboard Data (Cache Performance)...")
    start = time.perf_counter()
    res = requests.get(f"{BASE_URL}/api/data")
    latency = (time.perf_counter() - start) * 1000
    print(f"      Dashboard Data Latency: {latency:.2f}ms")
    assert res.status_code == 200
    assert 'balance' in res.json()

    # 5. Cleanup: Delete Test Symbol
    print(f"[5/5] Cleaning up: Deleting {test_symbol}...")
    res = requests.post(f"{BASE_URL}/api/symbols/delete", json={"symbol": test_symbol})
    if res.status_code == 200:
        print("      Success: Cleanup complete.")

    print("\nE2E API Flow Test Passed!")

if __name__ == "__main__":
    try:
        run_e2e_flow()
    except Exception as e:
        print(f"Test Failed: {e}")
        print("Make sure the bot is running (python main.py) before starting this test.")
