
import asyncio
import logging
import sys
import os

# Добавляем путь к проекту
sys.path.append(os.getcwd())

from src.shared.providers.elevenlabs_stealth import elevenlabs_stealth

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')

async def test_stealth():
    # Just try to see if it reaches the synthesis page
    script = "Testing cookie injection. If you hear this, automation worked."
    result = await elevenlabs_stealth.generate_speech_stealth(script, "test_speech")
    if result:
        print(f"SUCCESS: Saved to {result}")
    else:
        print("FAILED: Check logs.")

if __name__ == "__main__":
    asyncio.run(test_stealth())
