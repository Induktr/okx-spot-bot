
import threading
import requests
import time
import statistics

# Configuration
BASE_URL = "http://127.0.0.1:5000"
ENDPOINT = "/api/data"
CONCURRENT_USERS = 50
DURATION_SECONDS = 10

results = []

def hammer_api(stop_event):
    while not stop_event.is_set():
        start = time.perf_counter()
        try:
            response = requests.get(f"{BASE_URL}{ENDPOINT}", timeout=5)
            latency = (time.perf_counter() - start) * 1000
            results.append({
                "status": response.status_code,
                "latency": latency
            })
        except Exception as e:
            results.append({
                "status": "ERROR",
                "latency": 0
            })
        time.sleep(0.1) # Small delay to simulate real user behavior

def run_load_test():
    print(f"Starting Load Test: {CONCURRENT_USERS} concurrent users for {DURATION_SECONDS}s...")
    stop_event = threading.Event()
    threads = []

    for _ in range(CONCURRENT_USERS):
        t = threading.Thread(target=hammer_api, args=(stop_event,))
        t.start()
        threads.append(t)

    time.sleep(DURATION_SECONDS)
    stop_event.set()

    for t in threads:
        t.join()

    # Analyze Results
    successes = [r for r in results if r['status'] == 200]
    latencies = [r['latency'] for r in successes]

    print("\n--- LOAD TEST RESULTS ---")
    print(f"Total Requests: {len(results)}")
    print(f"Success Rate:   {(len(successes)/len(results)*100):.2f}%")
    
    if latencies:
        print(f"Avg Latency:    {statistics.mean(latencies):.2f}ms")
        print(f"P95 Latency:    {statistics.quantiles(latencies, n=20)[18]:.2f}ms") # 19th ventile is p95
        print(f"Min/Max:        {min(latencies):.2f}ms / {max(latencies):.2f}ms")
    else:
        print("No successful requests recorded.")

if __name__ == "__main__":
    # Ensure the server is running before starting the test
    try:
        requests.get(BASE_URL)
        run_load_test()
    except requests.exceptions.ConnectionError:
        print(f"❌ Error: Dashboard server not found at {BASE_URL}. Start 'python main.py' first.")
