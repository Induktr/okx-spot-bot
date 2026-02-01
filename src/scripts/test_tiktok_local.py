import asyncio
import logging
import os
import sys
import io

# Force UTF-8 for Windows Console
if sys.platform == 'win32':
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')
    except:
        pass

# Add project root to path
sys.path.append(os.getcwd())

from src.shared.utils.tiktok_stealth import tiktok_stealth_upload
from src.app.config import config

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

async def run_local_tiktok_test():
    """
    Tests the TikTok stealth upload using an EXISTING local video file.
    No rendering, no AI generation - just pure uploading test.
    """
    print("\n" + "="*60)
    print("🚀 TIKTOK LOCAL UPLOAD TEST: GHOST PROTOCOL")
    print("="*60)

    # 1. Path to existing video file
    # Choosing one of your recent exports
    video_path = os.path.abspath("src/shared/data/marketing_outputs/Export_20260131_214210.mp4")
    
    if not os.path.exists(video_path):
        print(f"❌ ERROR: Video file not found at: {video_path}")
        return

    caption = "A.S.T.R.A Project v1.5 | Stealth Posting Test 🤖 #trading #ai #automation"
    
    # Path to our manual session profile
    cookie_path = os.path.join(os.getcwd(), "src", "shared", "data", "tiktok_cookies.txt") # Standard path but we use profile

    # Proxy from config (SSH SOCKS5)
    proxy = getattr(config, 'TIKTOK_PROXY', "socks5://127.0.0.1:1080")
    
    print(f"FILE: {os.path.basename(video_path)}")
    print(f"PROXY: {proxy}")
    print(f"HEADLESS: {config.HEADLESS_MODE}")
    print("-" * 60)

    try:
        logging.info("🎬 Starting upload...")
        result = await tiktok_stealth_upload(
            video_path=video_path,
            caption=caption,
            cookie_path=cookie_path,
            headless=config.HEADLESS_MODE,
            proxy=proxy
        )
        
        if result == "SUCCESS":
            print("\n" + "✅" * 20)
            print("  SUCCESS: TIKTOK POSTED LOCALLY!")
            print("✅" * 20 + "\n")
        else:
            print(f"\n❌ FAILED: {result}")
            
    except Exception as e:
        print(f"\n❌ CRITICAL ERROR: {e}")

if __name__ == "__main__":
    asyncio.run(run_local_tiktok_test())
