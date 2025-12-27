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

def astra_cycle():
    """
    The opportunistic cycle of A.S.T.R.A.
    AI reviews ALL symbols and picks the best one to act on.
    """
    if not config.SYMBOLS:
        logging.warning("No symbols configured in SYMBOLS list.")
        return

    logging.info(f"--- Starting A.S.T.R.A. Selective Cycle ---")
    
    try:
        # 0. Global Sensors: News & Sentiment
        logging.info("Step 0: Fetching global news and sentiment...")
        balance = trader.get_balance()
        headlines = news_aggregator.get_recent_headlines(hours=24)
        sentiment_idx = news_aggregator.get_market_sentiment()
        mood_context = f"Market Mood: {sentiment_idx['value']} ({sentiment_idx['classification']})"
        
        # 1. Collect Market Snapshot for ALL symbols
        logging.info("Step 1: Building market snapshot for all configured symbols...")
        all_positions = trader.get_positions()
        snapshot_lines = []
        
        for sim in config.SYMBOLS:
            price = trader.get_ticker(sim)
            pos = [p for p in all_positions if p['symbol'] == sim]
            pos_str = "No Position"
            if pos:
                p = pos[0]
                pos_str = f"In {p['side']} (PnL: {p.get('unrealizedPnl', 0)} USDT, ROE: {p.get('percentage', 0)}%)"
            
            snapshot_lines.append(f"- {sim}: Price {price} | Status: {pos_str}")
        
        market_snapshot = "\n".join(snapshot_lines)
        
        # 2. Brain: Pick the best target
        logging.info("Step 2: AI Selection and Analysis...")
        analysis = ai_client.analyze_news(headlines, balance, market_snapshot, mood_context)
        
        symbol = analysis.get('target_symbol', 'NONE')
        decision = analysis.get('action', 'WAIT').upper()

        if symbol == "NONE" or decision == "WAIT":
            logging.info("AI: No opportunistic trades or management needed at this time.")
            scribe.log_cycle(analysis, "Cycle complete: No action chosen.")
            return

        # 3. Hands: Execute Strategy for the Chosen Symbol
        tp_val = analysis.get('tp_pct', 0.3)
        sl_val = analysis.get('sl_pct', 0.2)
        ai_leverage = min(int(analysis.get('leverage', 3)), 10)
        ai_budget = float(analysis.get('budget_usdt', config.TRADE_AMOUNT))
        
        logging.info(f"[{symbol}] Chosen by AI. Decision -> {decision} (Lev: {ai_leverage}x, Budget: ${ai_budget})")
        
        execution_msg = "No execution needed."
        symbol_positions = [p for p in all_positions if p['symbol'] == symbol]

        # Manage existing entry TP/SL if open or ADJUST requested
        if symbol_positions and decision in ["WAIT", "ADJUST"]:
            logging.info(f"[{symbol}] Syncing TP/SL...")
            sync_res = trader.sync_sl_tp(symbol_positions[0], tp_pct=tp_val, sl_pct=sl_val)
            execution_msg = f"Synced/Adjusted TP/SL: {str(sync_res)}"

        if decision == "CLOSE" and symbol_positions:
            logging.info(f"[{symbol}] AI decided to CLOSE.")
            result = trader.close_position(symbol_positions[0])
            execution_msg = f"CLOSED POSITION: {str(result)}"
        elif decision in ["BUY", "SELL"]:
            # Check for Flip
            is_flip = False
            if symbol_positions:
                current_side = symbol_positions[0]['side'].upper() # 'LONG' or 'SHORT'
                target_side = "LONG" if decision == "BUY" else "SHORT"
                
                if current_side != target_side:
                    logging.info(f"[{symbol}] FLIPPING from {current_side} to {target_side}...")
                    trader.close_position(symbol_positions[0])
                    time.sleep(2) # Wait for settlement
                    is_flip = True
                else:
                    execution_msg = f"Already in {symbol} {current_side}. Action {decision} ignored."
                    logging.info(execution_msg)
                    is_flip = False

            if not symbol_positions or is_flip:
                logging.info(f"[{symbol}] Opening NEW {decision} position.")
                trader.leverage = ai_leverage
                result = trader.execute_order(symbol, decision, ai_budget)
                
                # Immediately sync TP/SL for the new position
                time.sleep(2) 
                new_positions = trader.get_positions(target_symbol=symbol)
                if new_positions:
                    sync_res = trader.sync_sl_tp(new_positions[0], tp_pct=tp_val, sl_pct=sl_val)
                    execution_msg = f"EXECUTED {decision} & SYNCED TP/SL: {str(sync_res)}"
                else:
                    execution_msg = f"EXECUTED {decision} (Sync pending): {str(result)}"


        # 4. Scribe: Log results
        scribe.log_cycle(analysis, f"[{symbol}] {execution_msg}")
        logging.info(f"Cycle for {symbol} complete. Next selective cycle in 2 hours.")

    except Exception as e:
        logging.error(f"CRITICAL ERROR in selective cycle: {e}")
        scribe.log_cycle(
            {"target_symbol": "ERROR", "action": "ERROR", "reasoning": str(e)},
            "Failed to complete selective cycle."
        )

def main():
    """Entry point of the application."""
    logging.info("Initializing A.S.T.R.A. Selective-Mode System...")
    logging.info(f"Monitoring: {config.SYMBOLS}")
    
    # Run once at startup
    astra_cycle()
    
    # Schedule every 2 hours
    schedule.every(2).hours.do(astra_cycle)
    
    logging.info("Scheduler active: Selecting the best coin to trade every 2 hours.")
    
    while True:
        schedule.run_pending()
        time.sleep(1)


if __name__ == "__main__":
    main()
