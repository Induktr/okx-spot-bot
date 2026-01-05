import schedule
import time
import logging
from src.app.config import config
from src.shared.providers.news_aggregator import news_aggregator
from src.features.sentiment_analyzer.ai_client import ai_client
from src.features.trade_executor.trader import trader, traders
from src.shared.utils.analysis import tech_analysis
from src.shared.utils.logger import scribe
from src.shared.utils.portfolio_tracker import portfolio_tracker
from src.shared.providers.telegram_provider import telegram_bot
from src.shared.utils.report_parser import report_parser
import datetime
from concurrent.futures import ThreadPoolExecutor
import os

# Configure internal logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def astra_cycle():
    """
    The opportunistic cycle of A.S.T.R.A.
    AI reviews ALL symbols (News + Technicals) and picks the best one.
    """
    if not config.BOT_ACTIVE:
        logging.info("⏸️ A.S.T.R.A. is in Sleep Mode. Cycle skipped.")
        return

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
        
        # SMART WAKE-UP CHECK
        if not news_aggregator.has_significant_events(headlines):
            logging.info("💤 Market is QUIET (No Trigger Words). Skipping AI analysis to save resources.")
            scribe.log_cycle({
                "action": "SLEEP",
                "sentiment_score": 0,
                "reasoning": "Market is Quiet (No significant news events found in the last 24h). AI is in Standby Mode to save resources."
            }, "News Filter: No significant events detected.")
            return
        
        # --- Feature 6: Black Swan Insurance ---
        raw_news_text = " ".join(headlines).lower()
        if any(word in raw_news_text for word in config.EMERGENCY_WORDS):
            logging.critical("🚨 BLACK SWAN EVENT DETECTED IN NEWS STREAM!")
            telegram_bot.send_emergency_alert("MARKET PANIC / EMERGENCY", "Critical keywords detected in global news stream. System shielding active.")
            # Auto-liquidate for safety
            for eid, t in traders.items():
                t.emergency_liquidate_all()
            scribe.log_cycle({"action": "EMERGENCY_EXIT"}, "System wide liquidation triggered by Black Swan detection.")
            return
            
        # 1. Collect Market Snapshot (Across ALL Exchanges) in Parallel
        total_balance = 0
        exchange_data_map = {} 
        
        for eid, t in traders.items():
            bal = t.get_balance()
            total_balance += bal
            exchange_data_map[eid] = {
                "balance": bal,
                "positions": t.get_positions()
            }
        
        portfolio_tracker.record_snapshot(total_balance)
        
        snapshot_lines = []
        
        def fetch_symbol_info(eid, t, sim, all_positions):
            try:
                # Grouped fetch for one symbol
                full_ticker = t.exchange.fetch_ticker(sim)
                price = full_ticker['last']
                volume_24h = float(full_ticker.get('quoteVolume', 0) or 0) / 1_000_000 
                funding_rate = t.get_funding_rate(sim) * 100 
                
                pos = [p for p in all_positions if p['symbol'] == sim]
                pos_str = "No Position"
                if pos:
                    p = pos[0]
                    nominal_val = float(p.get('notional', 0) or 0)
                    upnl = float(p.get('unrealizedPnl', 0) or 0)
                    est_total_fees = abs(nominal_val) * 0.0005 * 2 
                    net_pnl = upnl - est_total_fees
                    pos_str = f"In {p['side']} (Net PnL: {net_pnl:.2f} USDT | Upnl: {upnl:.2f} | Fees: {est_total_fees:.2f})"
                
                ta_str = "| TA: N/A"
                try:
                    candles = t.get_ohlcv(sim, timeframe='1h', limit=50)
                    if candles:
                        closes = [c[4] for c in candles]
                        rsi = tech_analysis.calculate_rsi(closes)
                        ema = tech_analysis.calculate_ema(closes)
                        trend = "BULLISH" if price > (ema or 0) else "BEARISH"
                        ta_str = f"| RSI(1h): {rsi} | Trend: {trend} | Price vs EMA: {'Above' if price > (ema or 0) else 'Below'}"
                except: pass
                
                return f"- [{eid.upper()}] {sim}: Price {price} | Vol: {volume_24h:.1f}M | Fund: {funding_rate:.4f}% {ta_str} | Status: {pos_str}"
            except Exception as e:
                return f"- [{eid.upper()}] {sim}: Error fetching data ({str(e)[:50]})"

        # Execute symbol fetches in parallel
        for eid, t in traders.items():
            ex_data = exchange_data_map[eid]
            all_positions = ex_data["positions"]
            
            with ThreadPoolExecutor(max_workers=len(config.SYMBOLS)) as executor:
                # Map symbol fetches
                future_results = [executor.submit(fetch_symbol_info, eid, t, sim, all_positions) for sim in config.SYMBOLS]
                for future in future_results:
                    snapshot_lines.append(future.result())
        
        market_snapshot = "\n".join(snapshot_lines)
        
        # INTERRUPT CHECK: Before AI Analysis
        if not config.BOT_ACTIVE: 
            logging.info("🛑 Emergency Stop: Bot paused before AI Analysis.")
            return

        # 2. Brain: AI Analysis
        logging.info("Step 2: AI Selection and Analysis...")
        try:
            analysis = ai_client.analyze_news(headlines, total_balance, market_snapshot, mood_context)
        except Exception as e:
            if "429" in str(e) or "ResourceExhausted" in str(e):
                logging.critical("🚨 Gemini API Rate Limit (429) reached! Activating Circuit Breaker (60m).")
                config.BOT_ACTIVE = False
                telegram_bot.send_emergency_alert("API CIRCUIT BREAKER", "Gemini 429 Rate Limit hit. System paused for 60 minutes to protect resources.")
                # We return here; schedule will trigger again, but config.BOT_ACTIVE will skip it 
                # Until a manual resume or we could use a timer.
                return
            raise e
        
        if not isinstance(analysis, dict):
            logging.error(f"Critical: AI returned malformed data type: {type(analysis)}")
            return

        symbol = analysis.get('target_symbol', 'NONE')
        decision = analysis.get('action', 'WAIT').upper()
        confidence = float(analysis.get('sentiment_score', 0))

        if symbol == "NONE" or decision == "WAIT":
            logging.info("AI: No action chosen.")
            scribe.log_cycle(analysis, "Cycle complete: No action.")
            return

        if decision in ["BUY", "SELL"] and confidence < 7:
            msg = f"AI Confidence ({confidence}/10) is not high enough for a new trade (Need >= 7). Standing by."
            logging.info(msg)
            scribe.log_cycle(analysis, f"Cycle complete: {msg}")
            return

        # --- Feature 5: Telegram Signal Hub ---
        if decision in ["BUY", "SELL"]:
            telegram_bot.send_trade_signal(symbol, decision, analysis.get('reasoning', 'N/A'), confidence)

        # INTERRUPT CHECK: Before Trading Execution
        if not config.BOT_ACTIVE: 
            logging.info("🛑 Emergency Stop: Bot paused before Execution.")
            return

        # 3. Hands: Execute Strategy on ALL active exchanges
        execution_results = []
        for eid, t in traders.items():
            try:
                logging.info(f"[{eid.upper()}] Applying AI decision for {symbol}...")
                
                # Check for existing positions
                symbol_positions = t.get_positions(target_symbol=symbol)
                
                if decision == "CLOSE":
                    if symbol_positions:
                        logging.info(f"[{eid.upper()}] CLOSING position for {symbol} per AI request.")
                        res = t.close_position(symbol_positions[0])
                        execution_results.append(f"{eid.upper()}: {res}")
                    else:
                        msg = f"{eid.upper()}: No position to close for {symbol}."
                        logging.warning(msg)
                        execution_results.append(msg)

                elif decision in ["BUY", "SELL"]:
                    ai_lev = int(analysis.get('leverage', 3))
                    ai_budget = float(analysis.get('budget_usdt', 0))
                    
                    if ai_budget <= 0:
                        logging.warning(f"[{eid.upper()}] AI requested a trade but proposed $0 budget. Skipping.")
                        continue
                        
                    # Handle FLIP (Reverse position) or Simple Execution
                    if symbol_positions:
                        current_side = symbol_positions[0]['side'].upper() # 'LONG' or 'SHORT'
                        target_side = "LONG" if decision == "BUY" else "SHORT"
                        
                        if current_side != target_side:
                            # ATOMIC FLIP
                            res = t.execute_flip(symbol, symbol_positions[0], decision, ai_budget, ai_lev)
                        else:
                            # SIDE MATCHES - Skip leverage update for open positions as per user request
                            res = f"SKIPPED: Leverage change ignored for existing {current_side} (Safety focus)"
                    else:
                        # NORMAL ENTRY
                        res = t.execute_order(symbol, decision, ai_budget, leverage=ai_lev)
                    
                    # Protection Sync if new or existing position exists
                    time.sleep(1)
                    updated_pos = t.get_positions(target_symbol=symbol)
                    if updated_pos:
                        sync_status = t.sync_sl_tp(
                            updated_pos[0], 
                            tp_pct=float(analysis.get('tp_pct', 0.35)), 
                            sl_pct=float(analysis.get('sl_pct', 0.2))
                        )
                        execution_results.append(f"{eid.upper()}: {res} ({sync_status})")
                    else:
                        execution_results.append(f"{eid.upper()}: {res}")
                
                elif decision == "ADJUST":
                     if symbol_positions:
                          # Skip leverage update for open positions as per user request
                          sync_status = t.sync_sl_tp(
                             symbol_positions[0], 
                             float(analysis.get('tp_pct', 0.35)), 
                             float(analysis.get('sl_pct', 0.2))
                         )
                          execution_results.append(f"{eid.upper()}: ADJUSTED ({sync_status})")
                     else:
                          execution_results.append(f"{eid.upper()}: ADJUST skipped (No position)")
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
    
    # Schedule every 60 minutes
    schedule.every(60).minutes.do(astra_cycle)
    
    logging.info("Scheduler active: Selecting the best coin to trade every 60 minutes.")
    
    while True:
        # Check if UI requested an immediate cycle (Manual Resume)
        if config.FORCE_CYCLE:
            logging.info("⚡ Immediate Cycle triggered by User (UI Force)")
            config.FORCE_CYCLE = False # Reset flag
            astra_cycle()
            
        schedule.run_pending()
        time.sleep(1)


if __name__ == "__main__":
    main()
