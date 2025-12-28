import schedule
import time
import logging
from src.app.config import config
from src.shared.providers.news_aggregator import news_aggregator
from src.features.sentiment_analyzer.ai_client import ai_client
from src.features.trade_executor.trader import trader, traders
from src.shared.utils.analysis import tech_analysis
from src.shared.utils.logger import scribe

# Configure internal logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def astra_cycle():
    """
    The opportunistic cycle of A.S.T.R.A.
    AI reviews ALL symbols (News + Technicals) and picks the best one.
    """
    if not config.SYMBOLS:
        logging.warning("No symbols configured in SYMBOLS list.")
        return

    logging.info(f"--- Starting A.S.T.R.A. Selective Cycle ---")
    
    try:
        # 0. Global Sensors: News & Sentiment
        logging.info("Step 0: Fetching global news and sentiment...")
        headlines = news_aggregator.get_recent_headlines(hours=24)
        sentiment_idx = news_aggregator.get_market_sentiment()
        mood_context = f"Market Mood: {sentiment_idx['value']} ({sentiment_idx['classification']})"
        
        # 1. Collect Market Snapshot (Across ALL Exchanges)
        logging.info(f"Step 1: Building combined snapshot for {len(traders)} exchanges...")
        total_balance = 0
        snapshot_lines = []
        
        for eid, t in traders.items():
            bal = t.get_balance()
            total_balance += bal
            all_positions = t.get_positions()
            
            for sim in config.SYMBOLS:
                price = t.get_ticker(sim)
                pos = [p for p in all_positions if p['symbol'] == sim]
                pos_str = "No Position"
                if pos:
                    p = pos[0]
                    pos_str = f"In {p['side']} (PnL: {p.get('unrealizedPnl', 0)} USDT)"
                
                snapshot_lines.append(f"- [{eid.upper()}] {sim}: Price {price} | Status: {pos_str}")
        
        market_snapshot = "\n".join(snapshot_lines)
        
        # 2. Brain: AI Analysis
        logging.info("Step 2: AI Selection and Analysis...")
        analysis = ai_client.analyze_news(headlines, total_balance, market_snapshot, mood_context)
        
        symbol = analysis.get('target_symbol', 'NONE')
        decision = analysis.get('action', 'WAIT').upper()

        if symbol == "NONE" or decision == "WAIT":
            logging.info("AI: No action chosen.")
            scribe.log_cycle(analysis, "Cycle complete: No action.")
            return

        # 3. Hands: Execute Strategy on ALL active exchanges
        execution_results = []
        for eid, t in traders.items():
            try:
                logging.info(f"[{eid.upper()}] Applying AI decision for {symbol}...")
                
                # Check for existing positions to handle FLIP
                symbol_positions = t.get_positions(target_symbol=symbol)
                if symbol_positions:
                    current_side = symbol_positions[0]['side'].upper() # 'LONG' or 'SHORT'
                    target_side = "LONG" if decision == "BUY" else "SHORT"
                    
                    if decision in ["BUY", "SELL"] and current_side != target_side:
                        logging.info(f"[{eid.upper()}] FLIPPING detected. Closing {current_side} before opening {target_side}...")
                        t.close_position(symbol_positions[0])
                        time.sleep(2) # Wait for settlement
                
                # Execute new order
                t.leverage = min(int(analysis.get('leverage', 3)), 10)
                res = t.execute_order(symbol, decision, float(analysis.get('budget_usdt', 10)))
                
                # 4. Immediate Protection Sync
                time.sleep(2)
                new_pos = t.get_positions(target_symbol=symbol)
                if new_pos:
                    sync_status = t.sync_sl_tp(
                        new_pos[0], 
                        tp_pct=float(analysis.get('tp_pct', 0.3)), 
                        sl_pct=float(analysis.get('sl_pct', 0.2))
                    )
                    execution_results.append(f"{eid.upper()}: {res} ({sync_status})")
                else:
                    execution_results.append(f"{eid.upper()}: {res}")
            except Exception as exchange_err:
                error_log = f"{eid.upper()} Failed: {str(exchange_err)}"
                logging.error(error_log)
                execution_results.append(error_log)

        # 4. Scribe: Log results
        scribe.log_cycle(analysis, f"Executed on {len(traders)} exchanges: {', '.join(execution_results)}")

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

    # Step 5: Start Dashboard (The Watcher)
    try:
        from src.app.dashboard.app import run_dashboard
        import threading
        db_thread = threading.Thread(target=run_dashboard, daemon=True)
        db_thread.start()
        logging.info("Dashboard active at: http://localhost:5000")
    except Exception as e:
        logging.error(f"Failed to start dashboard: {e}")
    
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
