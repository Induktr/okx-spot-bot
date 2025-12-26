import logging
import ccxt
from hands.trader import trader
from core.config import config

logging.basicConfig(level=logging.INFO)

print("--- Trader Order Test ---")
try:
    print(f"Account Level: {trader.acct_lv}")
    print(f"Position Mode: {trader.pos_mode}")
    
    symbol = config.SYMBOL # SOL/USDT
    amount = 0.1 # Very small amount of SOL for test
    
    # We'll try to buy 0.1 SOL
    print(f"Attempting to BUY {amount} {symbol}...")
    result = trader.execute_order("BUY", amount)
    print(f"Result: {result}")

except Exception as e:
    print(f"Error: {e}")
