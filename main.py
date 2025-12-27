import schedule
import time
import logging
from core.config import config
from sensors.news_aggregator import news_aggregator
from brain.ai_client import ai_client
from hands.trader import trader
from scribe.logger import scribe

# Configure internal logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Global state to keep track of the current symbol index
current_symbol_index = 0

def astra_cycle():
    """
    The slow autonomous cycle of A.S.T.R.A.
    Processes ONLY ONE symbol per call, then moves to the next in the next call.
    """
    global current_symbol_index
    
    if not config.SYMBOLS:
        logging.warning("No symbols configured in SYMBOLS list.")
        return

    # Pick the current symbol
    symbol = config.SYMBOLS[current_symbol_index % len(config.SYMBOLS)]
    
    logging.info(f"--- Starting A.S.T.R.A. Slow Cycle (Step {current_symbol_index + 1}) ---")
    logging.info(f"Target Symbol: {symbol}")
    
    try:
        # 0. Global Sensors: News & Sentiment
        logging.info("Step 0: Fetching global news and sentiment...")
        balance = trader.get_balance()
        headlines = news_aggregator.get_recent_headlines(hours=24) # Increased for slower cycles
        sentiment_idx = news_aggregator.get_market_sentiment()
        mood_context = f"Market Mood (Fear & Greed Index): {sentiment_idx['value']} ({sentiment_idx['classification']})"
        
        logging.info(f"Balance: {balance} USDT | Cycle Symbol: {symbol}")

        # 1. Fetch Symbol Data
        logging.info(f"Step 1: Checking status for {symbol}...")
        current_price = trader.get_ticker(symbol)
        all_positions = trader.get_positions()
        symbol_positions = [p for p in all_positions if p['symbol'] == symbol]
        
        # Format position data for AI context
        pos_context = f"Coin: {symbol}. No current positions."
        if symbol_positions:
            p = symbol_positions[0]
            unrealized_pnl = p.get('unrealizedPnl', 0)
            percentage = p.get('percentage', 0)
            side = p.get('side', 'unknown')
            entry = p.get('entryPrice', 0)
            
            pos_context = (
                f"Position: {side.upper()} {symbol}\n"
                f"Entry Price: {entry}\n"
                f"Current Price: {current_price}\n"
                f"Unrealized PnL: {unrealized_pnl} USDT\n"
                f"ROE: {percentage}%"
            )
            logging.info(f"[{symbol}] In position: {side.upper()} | PnL: {unrealized_pnl} | ROE: {percentage}%")

        # 2. Brain: Analyze Symbol
        logging.info(f"Step 2: AI Analysis for {symbol}...")
        analysis = ai_client.analyze_news(headlines, pos_context, mood_context)
        
        # 3. Hands: Execute Strategy
        decision = analysis.get('action', 'WAIT').upper()
        tp_val = analysis.get('tp_pct', 0.3)
        sl_val = analysis.get('sl_pct', 0.2)
        ai_leverage = min(int(analysis.get('leverage', 3)), 10) # Cap at 10x
        
        logging.info(f"[{symbol}] AI Decision -> {decision} (Lev: {ai_leverage}x)")
        
        # --- TEST OVERRIDE: FORCE BUY IF WAIT AND NO POSITIONS ---
        if decision == "WAIT" and not symbol_positions:
            logging.warn(f"!!! FORCING TEST BUY FOR {symbol} despite AI WAIT signal !!!")
            decision = "BUY"
        # --------------------------------------------------------
        
        execution_msg = "No execution needed."

        # Manage existing entry TP/SL if open or ADJUST requested
        if symbol_positions and decision in ["WAIT", "ADJUST"]:
            logging.info(f"[{symbol}] Syncing TP/SL...")
            sync_res = trader.sync_sl_tp(symbol_positions[0], tp_pct=tp_val, sl_pct=sl_val)
            execution_msg = f"Synced/Adjusted TP/SL: {str(sync_res)}"

        if decision == "CLOSE" and symbol_positions:
            logging.info(f"[{symbol}] AI decided to CLOSE.")
            result = trader.close_position(symbol_positions[0])
            execution_msg = f"CLOSED POSITION: {str(result)}"
        elif decision in ["BUY", "SELL"] and not symbol_positions:
            logging.info(f"[{symbol}] Opening NEW {decision} position.")
            # Set leverage before order
            trader.leverage = ai_leverage
            result = trader.execute_order(symbol, decision, config.TRADE_AMOUNT)

            
            # Immediately sync TP/SL for the new position
            time.sleep(2) 
            new_positions = trader.get_positions(target_symbol=symbol)
            if new_positions:
                sync_res = trader.sync_sl_tp(new_positions[0], tp_pct=tp_val, sl_pct=sl_val)
                execution_msg = f"EXECUTED {decision} & SYNCED TP/SL: {str(sync_res)}"
            else:
                execution_msg = f"EXECUTED {decision} (Sync pending): {str(result)}"
        elif decision in ["BUY", "SELL"] and symbol_positions:
            execution_msg = f"Already in {symbol} position. Decision {decision} ignored."

        # 4. Scribe: Log results
        scribe.log_cycle(analysis, f"[{symbol}] {execution_msg}")

        # Update index for the NEXT call (2 hours later)
        current_symbol_index += 1
        logging.info(f"Cycle for {symbol} complete. Next coin scheduled in 2 hours.")

    except Exception as e:
        logging.error(f"CRITICAL ERROR in cycle for {symbol}: {e}")
        scribe.log_cycle(
            {"sentiment_score": 0, "action": "ERROR", "reasoning": str(e)},
            f"Failed to process {symbol}."
        )

def main():
    """Entry point of the application."""
    logging.info("Initializing A.S.T.R.A. Slow-Mode System...")
    logging.info(f"Queue: {config.SYMBOLS}")
    
    # Run once at startup
    astra_cycle()
    
    # Schedule to process exactly ONE coin every 2 hours
    schedule.every(2).hours.do(astra_cycle)
    
    logging.info("Scheduler active: Processing one coin from the list every 2 hours.")
    
    while True:
        schedule.run_pending()
        time.sleep(1)

if __name__ == "__main__":
    main()
