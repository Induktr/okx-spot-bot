
import asyncio
import logging
import os
import sys

# Add project root to sys.path
sys.path.append(os.getcwd())

from src.shared.utils.tiktok_stealth import tiktok_stealth_upload

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')

async def main():
    print("\n" + "="*60)
    print("TIKTOK STEALTH BROWSER: VISIBLE MODE")
    print("="*60)
    print("This script will open a real browser window so you can see the bot in action.")
    
    # Path settings
    video_path = "src/data/marketing_outputs/viral_DEFAULT_test_win_001.mp4"
    if not os.path.exists(video_path):
        import glob
        files = glob.glob("src/data/marketing_outputs/*.mp4")
        if files:
            video_path = files[0]
        else:
            print("[!] ERROR: No video file found. Run 'run_viral_cycle.py' first.")
            return

    cookie_path = "data/tiktok_cookies.txt"
    # We will try to connect via CDP first anyway in the stealth utility
    
    caption = "A.S.T.R.A. AI Bot identifying market trends. #trading #ai #crypto #success"
    
    print(f"[*] Video: {video_path}")
    print(f"[*] Cookies: {cookie_path}")
    print("[*] Launching browser...")

    # Set headless=False to see it
    result = await tiktok_stealth_upload(video_path, caption, cookie_path, headless=False)
    
    if result == "SUCCESS":
        print("\n[+] SUCCESS: Video posted to TikTok!")
    else:
        print(f"\n[-] FAILED: {result}")

if __name__ == "__main__":
    asyncio.run(main())
