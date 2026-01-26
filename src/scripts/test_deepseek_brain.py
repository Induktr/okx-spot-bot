import sys
import os
import logging
import json

# Add project root to path
sys.path.append(os.getcwd())

from src.features.media_core.script_writer import script_writer
from src.app.config import config

# Clean logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')

def test_deepseek_integration():
    print("\n" + "="*60)
    print("🧠 DEEPSEEK BRAIN DIAGNOSTIC TEST")
    print("="*60)

    # 1. Check Configuration
    print(f"Checking Config...")
    deepseek_key = config.DEEPSEEK_API_KEY
    if not deepseek_key or "placeholder" in deepseek_key:
        print("❌ FAILED: DEEPSEEK_API_KEY is missing in .env or config.")
        print("Please add: DEEPSEEK_API_KEY=sk-...")
        return
    else:
        print(f"✅ Key found: {deepseek_key[:5]}...{deepseek_key[-3:]}")

    # 2. Check Client Initialization
    if not script_writer.deepseek_client:
        print("❌ FAILED: DeepSeek Client not initialized in ScriptWriter.")
        return
    print("✅ Client initialized successfully.")

    # 3. Test Generative Capability
    print("\n📝 Sending test prompt to DeepSeek V3...")
    
    fake_win = {
        "symbol": "SOL/USDT",
        "roi": 420.69,
        "pnl": 5000.0,
        "id": "test_ds_001"
    }

    dummy_trends = [
        {"id": "t1", "name": "DeepSeek Test Trend", "audio_vibe": "Test Vibe", "visual_style": "FLASH_CYBER"}
    ]

    try:
        # Direct call to the method that prioritizes DeepSeek
        result = script_writer.select_trend_and_write_script(fake_win, dummy_trends)
        
        print("\n" + "="*60)
        print("💡 DEEPSEEK RESPONSE:")
        print("="*60)
        print(json.dumps(result, indent=2, ensure_ascii=False))
        
        if result.get("selected_trend_name"):
             print("\n✅ SUCCESS: Valid JSON received from DeepSeek!")
        else:
             print("\n⚠️ WARNING: JSON received but keys might be missing.")

    except Exception as e:
        print(f"\n❌ ERROR during inference: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_deepseek_integration()
