
import subprocess
import os
import sys

def start_chrome():
    # Common paths for Chrome
    paths = [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        os.path.expanduser("~") + r"\AppData\Local\Google\Chrome\Application\chrome.exe"
    ]
    
    chrome_path = None
    for p in paths:
        if os.path.exists(p):
            chrome_path = p
            break
            
    if not chrome_path:
        print("❌ Chrome not found! Please provide the path to chrome.exe manually.")
        return

    # Use a separate user data dir to avoid messing with real cookies but still be a 'real' browser
    user_data_dir = os.path.abspath("data/chrome_debug_profile")
    if not os.path.exists(user_data_dir):
        os.makedirs(user_data_dir)

    print(f"🚀 Launching Chrome in Debug mode (Port 9222)...")
    print(f"📂 Profile: {user_data_dir}")
    
    command = [
        chrome_path,
        f"--remote-debugging-port=9222",
        f"--user-data-dir={user_data_dir}",
        "--no-first-run",
        "--no-default-browser-check"
    ]
    
    # Start process and don't wait
    subprocess.Popen(command)
    print("✅ Chrome started! You can now run 'python src/scripts/farm_hedra.py'")

if __name__ == "__main__":
    start_chrome()
