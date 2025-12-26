import logging
from hands.trader import trader
import ccxt

logging.basicConfig(level=logging.INFO)

print("--- Trader Initialization Test ---")
try:
    print(f"Account Level: {trader.acct_lv}")
    print(f"Position Mode: {trader.pos_mode}")
    balance = trader.get_balance()
    print(f"Balance: {balance} USDT")
except Exception as e:
    print(f"Error: {e}")
