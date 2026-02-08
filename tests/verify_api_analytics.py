import requests
import json
import time

def test_api():
    base_url = "http://127.0.0.1:5000"
    
    print("1. Fetching current data...")
    try:
        r = requests.get(f"{base_url}/api/data")
        r.raise_for_status()
        data = r.json()
        bal = data['balance']
        analytics = data['analytics']
        print(f"Current Balance: {bal}")
        print(f"Initial Balance: {analytics.get('initial_balance')}")
        print(f"Net Profit: {analytics.get('net_profit')}")
        
        # 2. Simulate Reset
        test_val = 50000.00
        print(f"\n2. Resetting portfolio to {test_val}...")
        r = requests.post(f"{base_url}/api/portfolio/reset", json={"balance": test_val})
        r.raise_for_status()
        print(f"Reset Response: {r.json()}")
        
        # 3. Verify Update
        print("\n3. Verifying update...")
        time.sleep(1) # Small gap for cache update
        r = requests.get(f"{base_url}/api/data")
        r.raise_for_status()
        data = r.json()
        new_analytics = data['analytics']
        print(f"New Initial Balance: {new_analytics.get('initial_balance')}")
        print(f"New Net Profit: {new_analytics.get('net_profit')}")
        
        if abs(new_analytics.get('initial_balance') - test_val) < 0.01:
            print("\n[SUCCESS] Initial Balance matches reset value.")
        else:
            print("\n[FAILURE] Initial Balance mismatch!")
            
        expected_profit = round(data['balance'] - test_val, 2)
        if abs(new_analytics.get('net_profit') - expected_profit) < 0.01:
            print(f"[SUCCESS] Net Profit ({new_analytics.get('net_profit')}) correctly calculated.")
        else:
             print(f"[FAILURE] Net Profit mismatch! Expected ~{expected_profit}, got {new_analytics.get('net_profit')}")

    except Exception as e:
        print(f"[ERROR] API TEST ERROR: {e}")

if __name__ == "__main__":
    test_api()
