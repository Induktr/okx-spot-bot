import sys
import os
import logging
import time

# Add root to path so we can import src modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../")))

from src.app.config import config
from src.features.trade_executor.trader import traders
from src.shared.utils.logger import scribe

# Setup basic logging to console
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def test_force_entry():
    """
    Simulates a 10/10 AI signal to test execution connectivity.
    WARNING: THIS ATTEMPTS A REAL TRADE (OR DEMO IF CONFIGURED).
    """
    logging.info("🧪 STARTING MANUAL EXECUTION TEST (FAKE 10/10 SIGNAL)")
    
    # 1. Config Setup
    # Ensure traders are loaded
    if not traders:
        logging.error("❌ No traders loaded! Check your credentials in settings.json or .env")
        return

    logging.info(f"Active Exchanges: {list(traders.keys())}")
    logging.info(f"Sandbox Modes: {config.SANDBOX_MODES}")

    # Use a standard liquid pair for testing. 
    # For OKX Perpetual, formatted usually as BTC/USDT:USDT by CCXT, but let's use the user's convention
    # or let the trader class logic handle normalization if it does. 
    # We will pick DOGE/USDT for low nominal value if real.
    TEST_SYMBOL = "DOGE/USDT:USDT" # Assuming OKX linear swap convention in this project
    # If standard spot/margin: "DOGE/USDT"
    
    # Let's try to detect format from config or default to standard futures
    # If the user has symbols in config, pick one.
    if config.SYMBOLS:
        TEST_SYMBOL = config.SYMBOLS[0]
        logging.info(f"Picked symbol from config: {TEST_SYMBOL}")
    else:
        logging.info(f"No symbols in config, defaulting to: {TEST_SYMBOL}")

    # 2. Mock The AI Analysis
    fake_analysis = {
        "action": "BUY",
        "target_symbol": TEST_SYMBOL,
        "sentiment_score": 10,
        "reasoning": "MANUAL TEST: Forced 10/10 score to verify order placement logic.",
        "tp_pct": 0.05, # +5%
        "sl_pct": 0.02, # -2%
        "leverage": 2,      # Conservative leverage for test
        "budget_usdt": 15.0, # Minimum safe size (~15$)
        "risk_factor": "LOW"
    }

    logging.info(f"📝 Mock Signal Created: {fake_analysis}")

    # 3. Access Trader and Execute
    for eid, t in traders.items():
        logging.info(f"\n🚀 Sending order to {eid.upper()}...")
        
        try:
            # 1. Check Balance
            bal = t.get_balance()
            logging.info(f"[{eid}] Current Balance: {bal} USDT")
            
            if bal < 15:
                logging.warning(f"[{eid}] Insufficient balance for test! Need > 15 USDT.")
                continue

            # 2. Execute Order
            # execute_order(self, symbol, side, amount_usdt, leverage=1)
            res = t.execute_order(
                symbol=fake_analysis['target_symbol'],
                side=fake_analysis['action'],
                budget_usdt=fake_analysis['budget_usdt'],
                leverage=fake_analysis['leverage']
            )
            
            logging.info(f"✅ EXECUTION RESULT: {res}")
            
            # 3. Add SL/TP Protection
            logging.info("Waiting 3s for exchange to register position...")
            time.sleep(3)
            
            positions = t.get_positions(target_symbol=fake_analysis['target_symbol'])
            
            if positions:
                logging.info(f"🛡️ Position Confirmed: {positions[0]['symbol']} Size: {positions[0]['contracts']}")
                logging.info(f"🛡️ Syncing TP/SL...")
                
                sync_res = t.sync_sl_tp(
                    positions[0],
                    tp_pct=fake_analysis['tp_pct'],
                    sl_pct=fake_analysis['sl_pct']
                )
                logging.info(f"🛡️ Protection Sync Result: {sync_res}")
            else:
                logging.warning("⚠️ Order returned success, but position NOT found in subsequent fetch. Check exchange history.")

        except Exception as e:
            logging.error(f"❌ TEST FAILED for {eid}: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    print("\n" + "!"*60)
    print(" WARNING: THIS SCRIPT WILL EXECUTE A REAL TRADE")
    print(" (OR DEMO IF CONFIGURED IN SETTINGS).")
    print(f" Target: From Config or Default")
    print("!"*60 + "\n")
    
    confirm = input("Type 'YES' to proceed: ")
    if confirm.strip().upper() == "YES":
        test_force_entry()
    else:
        print("Test cancelled.")
