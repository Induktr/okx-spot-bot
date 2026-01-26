
import asyncio
import logging
import sys
import os

# Добавляем путь к проекту
sys.path.append(os.getcwd())

from src.shared.providers.inworld_provider import inworld_provider
from src.app.config import config

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')

async def test_inworld_api():
    print("\n" + "="*60)
    print("=== TESTING INWORLD AI OFFICIAL API ===")
    print("="*60)
    
    if not config.INWORLD_API_KEY:
        print("\n❌ ERROR: INWORLD_API_KEY not found in .env or settings.json")
        print("Please add: INWORLD_API_KEY=your_key_here to your .env file.")
        return

    script = "Victory! Our A.S.T.R.A algorithms just identified a massive long entry on Ethereum. Profits are soaring at 300 percent. Join the elite circle of AI traders today."
    
    try:
        path = await inworld_provider.generate_speech(script, "inworld_api_test")
        if path and os.path.exists(path):
            print(f"\n✅ SUCCESS! API Audio saved to: {path}")
            print(f"Size: {os.path.getsize(path)} bytes")
        else:
            print("\n❌ FAILED: Check the error logs above.")
    except Exception as e:
        print(f"\n❌ FATAL ERROR: {e}")

if __name__ == "__main__":
    asyncio.run(test_inworld_api())
