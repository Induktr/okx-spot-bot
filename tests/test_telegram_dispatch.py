import logging
import sys
import os

# Add project root to path
sys.path.append(os.getcwd())

from src.shared.providers.telegram_provider import TelegramProvider
from src.app.config import config

logging.basicConfig(level=logging.INFO)

def test_telegram_dispatch():
    print("Starting Telegram Dispatch Test...")
    
    # Check tokens
    if not config.TELEGRAM_TOKEN:
        print("Error: TELEGRAM_TOKEN not found.")
        return
    if not config.TELEGRAM_CHAT_ID:
        print("Error: TELEGRAM_CHAT_ID (TG_CHAT_ID) not found.")
        return

    tp = TelegramProvider()
    
    if not tp.bot:
        print("Error: Bot failed to initialize.")
        return
    
    print(f"Bot initialized for Chat ID: {config.TELEGRAM_CHAT_ID}")

    # Mock Data
    symbol = "BTC/USDT"
    side = "BUY"
    results = ["OKX: SUCCESS - Executed at 45000"]
    analytics = {
        'current_balance': 1250.50,
        'total_profit': 150.25,
        'roi_pct': 12.5
    }

    print("Sending Mock Execution Report...")
    
    try:
        # This will send a private message to the main chat ID
        res = tp.send_execution_report(symbol, side, results, analytics)
        if res:
            print("Report sent successfully to your main Telegram chat.")
        else:
            print("Report failed. Check your token and Chat ID.")
            
    except Exception as e:
        print(f"Test Crashed: {e}")

if __name__ == "__main__":
    test_telegram_dispatch()
