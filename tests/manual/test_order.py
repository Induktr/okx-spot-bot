import logging
import ccxt
import time
from src.features.trade_executor.trader import trader
from src.app.config import config

logging.basicConfig(level=logging.INFO)

print("--- Trader Order Test (Multi-Coin Fixed) ---")
try:
    print(f"Account Level: {trader.acct_lv}")
    print(f"Position Mode: {trader.pos_mode}")
    
    # Test with the first symbol in the list
    symbol = config.SYMBOLS[0] 
    amount = config.TRADE_AMOUNT
    
    # 1. Test EXECUTE ORDER (Market)
    print(f"\nStep 1: Attempting to BUY {amount} {symbol}...")
    order_res = trader.execute_order(symbol, "BUY", amount)
    print(f"Order Result: {order_res}")
    
    if isinstance(order_res, dict) and 'id' in order_res:
        print("\nStep 2: Order successful. Waiting 2s for position to register...")
        time.sleep(2)
        
        # 2. Test SYNC SL TP
        print(f"Step 3: Fetching positions for {symbol}...")
        positions = trader.get_positions(target_symbol=symbol)
        
        if positions:
            print(f"Found position: {positions[0]['side']} {positions[0]['contracts']}")
            print("Attempting to sync TP (30%) and SL (20%)...")
            sync_res = trader.sync_sl_tp(positions[0], tp_pct=0.3, sl_pct=0.2)
            print(f"Sync Result: {sync_res}")
        else:
            print("No position found to sync TP/SL. Check if order was actually filled.")
    else:
        print("\nOrder failed or result is not as expected. Skipping TP/SL sync.")

except Exception as e:
    print(f"\nCRITICAL ERROR: {e}")
    import traceback
    traceback.print_exc()
