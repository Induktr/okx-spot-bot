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

def is_trading_time():
    """Returns True if today is a configured trading day AND current time is within trading hours."""
    now = datetime.datetime.now()
    if now.weekday() not in config.TRADING_DAYS:
        return False, "Day Not Configured"
    
    # Check Hours
    start = config.TRADING_START_HOUR
    end = config.TRADING_END_HOUR
    
    if start < end:
        if not (start <= now.hour < end):
            return False, f"Outside Hours ({start}:00 - {end}:00)"
    else: # Overnight logic (e.g. 22 to 06)
        if not (now.hour >= start or now.hour < end):
             return False, f"Outside Hours ({start}:00 - {end}:00)"
             
    return True, "Active"

def astra_cycle():
    """
    The opportunistic cycle of A.S.T.R.A.
    AI reviews ALL symbols (News + Technicals) and picks the best one.
    """
    if check_equity_guardian():
        logging.info("🛡️ Equity Guardian triggered. Cycle suspended for safety.")
        return "SUCCESS"

    is_time, reason = is_trading_time()
    if not is_time:
        logging.info(f"🛑 SCHEDULE LOCK: {reason}. Cycle skipped.")
        return "SUCCESS"

    if not config.BOT_ACTIVE:
        logging.info("⏸️ A.S.T.R.A. is in Sleep Mode. Cycle skipped.")
        return "SUCCESS"

    if not config.SYMBOLS:
        logging.warning("No symbols configured in SYMBOLS list.")
        return "SUCCESS"

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
            
            # Even in quiet mode, we must run the Trailing Stop Engine
            apply_trailing_stop_engine()
            
            scribe.log_cycle({
                "action": "SLEEP",
                "sentiment_score": 0,
                "reasoning": "Market is Quiet (No significant news events found in the last 24h). AI is in Standby Mode, but Trailing Stop is ACTIVE."
            }, "News Filter: No significant events detected. Management Active.")
            return "SUCCESS"
        
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
            
        # 1. Institutional Screener (Hybrid Market Discovery)
        logging.info("Step 1: Institutional Screener - Discovering Hot Assets...")
        primary_trader = traders.get('okx') or traders.get('binance') or list(traders.values())[0]
        
        # Collect candidates: Top 100 by Volume + User manual list + Open Positions
        top_market_symbols = primary_trader.get_top_symbols(limit=100)
        open_positions = []
        for eid, t in traders.items():
            try:
                open_positions.extend([p['symbol'] for p in t.get_positions()])
            except: pass
            
        candidate_symbols = list(set(top_market_symbols + config.SYMBOLS + open_positions))
        
        # Pre-Screening Logic (Fast Tech Analysis)
        def pre_screen_asset(sim):
            try:
                                # Quick check using primary trader
                candles = primary_trader.get_ohlcv(sim, timeframe='1h', limit=30)
                if not candles: return None
                
                closes = [c[4] for c in candles]
                volumes = [c[5] for c in candles]
                
                rvol = tech_analysis.calculate_rvol(volumes)
                rsi = tech_analysis.calculate_rsi(closes)
                
                # Scoring: Priority for Open Positions > Manual List > RVOL Spike
                score = 0
                if sim in open_positions: score += 1000 # Must analyze held assets
                if sim in config.SYMBOLS: score += 500  # High priority for watchlist
                if rvol > 1.5: score += 100 * rvol
                if rsi < 30 or rsi > 70: score += 50
                
                if score > 50: # Only return assets with some level of interest
                    return {"symbol": sim, "score": score}
                return None
            except: return None

        screened_results = []
        with ThreadPoolExecutor(max_workers=25) as executor:
            raw_scores = list(executor.map(pre_screen_asset, candidate_symbols))
            screened_results = [r for r in raw_scores if r]
        
        # Final Selection (Top 10 for AI, Top 5 for Persistent Watchlist)
        screened_results.sort(key=lambda x: x['score'], reverse=True)
        final_symbols = [r['symbol'] for r in screened_results[:10]]
        
        # Inject "Winners" into dynamic config for UI
        # Filter out open positions and manual symbols to find "New Discoveries"
        new_discoveries = [r['symbol'] for r in screened_results if r['symbol'] not in open_positions and r['symbol'] not in config.SYMBOLS]
        config.HOT_SYMBOLS = new_discoveries[:5] # Top 5 new hot picks
        
        logging.info(f"Screener: Evaluated {len(candidate_symbols)} symbols. Selected {len(final_symbols)} for deep AI analysis: {final_symbols}")

        # 2. Collect Market Snapshot (Deep Analysis for Selected Symbols)
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
                    # Multi-Timeframe and Advanced Indicators
                    tf_data = {}
                    candles_1h = t.get_ohlcv(sim, timeframe='1h', limit=50)
                    if candles_1h:
                        closes = [c[4] for c in candles_1h]
                        rsi = tech_analysis.calculate_rsi(closes)
                        ema = tech_analysis.calculate_ema(closes)
                        macd = tech_analysis.calculate_macd(closes)
                        bb = tech_analysis.calculate_bollinger_bands(closes)
                        atr = tech_analysis.calculate_atr(candles_1h)
                        rvol = tech_analysis.calculate_rvol([c[5] for c in candles_1h])
                        pivots = tech_analysis.detect_pivots(candles_1h)
                        
                        trend = "BULLISH" if price > (ema or 0) else "BEARISH"
                        bb_status = "OVERSOLD" if price < bb['lower'] else ("OVERBOUGHT" if price > bb['upper'] else "STABLE")
                        macd_status = "BULLISH_CROSS" if macd['histogram'] > 0 else "BEARISH_CROSS"
                        
                        tf_data['1h'] = f"1h:{trend}(RSI:{rsi}|MACD:{macd_status}|BB:{bb_status}|ATR:{atr}|RVOL:{rvol}|S1:{pivots['s1']}|R1:{pivots['r1']})"
                    
                    for tf in ['4h', '1d']:
                        candles = t.get_ohlcv(sim, timeframe=tf, limit=50)
                        if candles:
                            closes = [c[4] for c in candles]
                            trend = "BULLISH" if price > (tech_analysis.calculate_ema(closes) or 0) else "BEARISH"
                            tf_data[tf] = f"{tf}:{trend}"
                    
                    if tf_data:
                        ta_str = "| " + " | ".join(tf_data.values())
                except Exception as ta_err:
                    logging.debug(f"TA Error for {sim}: {ta_err}")
                
                return f"- [{eid.upper()}] {sim}: Price {price} | Vol: {volume_24h:.1f}M | Fund: {funding_rate:.4f}% {ta_str} | Status: {pos_str}"
            except Exception as e:
                return f"- [{eid.upper()}] {sim}: Error fetching data ({str(e)[:50]})"

        # Execute symbol fetches in parallel for the FINAL SELECTED symbols
        for eid, t in traders.items():
            ex_data = exchange_data_map[eid]
            all_positions = ex_data["positions"]
            
            with ThreadPoolExecutor(max_workers=len(final_symbols)) as executor:
                future_results = [executor.submit(fetch_symbol_info, eid, t, sim, all_positions) for sim in final_symbols]
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
            
            # Check if AI returned an error-indicating analysis
            if analysis.get('target_symbol') == "NONE" and "AI unavailable" in analysis.get('reasoning', ''):
                logging.error(f"AI Brain error detected: {analysis.get('reasoning')}")
                return "RETRY"
                
        except Exception as e:
            if "429" in str(e) or "ResourceExhausted" in str(e) or "403" in str(e):
                logging.critical(f"🚨 AI Brain Failure (Rate Limit/Permission): {e}")
                telegram_bot.send_emergency_alert("AI BRAIN FALLEN", f"Brain encountered a critical error: {e}. Retrying cycle in seconds...")
                return "RETRY"
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
            return "SUCCESS"

        if decision in ["BUY", "SELL"] and confidence < 9:
            msg = f"AI Confidence ({confidence}/10) is not high enough for a new trade (Need >= 9). Standing by."
            logging.info(msg)
            scribe.log_cycle(analysis, f"Cycle complete: {msg}")
            return "SUCCESS"

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

        # 4. Trailing Stop Engine (Post-Execution Check)
        apply_trailing_stop_engine()

        # 5. Scribe & Telegram: Log results
        scribe.log_cycle(analysis, f"Executed on {len(traders)} exchanges: {', '.join(execution_results)}")
        
        # Pull fresh analytics for the Telegram report
        try:
            history = []
            for eid, t in traders.items():
                try: history.extend(t.get_history(limit=50))
                except: pass
            analytics = portfolio_tracker.get_analytics(trade_history=history)
            telegram_bot.send_execution_report(symbol, decision, execution_results, analytics)
        except Exception as tg_err:
            logging.error(f"Telegram report failed: {tg_err}")

        logging.info(f"Cycle for {symbol} complete.")
        return "SUCCESS"

    except Exception as e:
        logging.error(f"CRITICAL ERROR in selective cycle: {e}")
        scribe.log_cycle(
            {"target_symbol": "ERROR", "action": "ERROR", "reasoning": str(e)},
            "Failed to complete selective cycle."
        )
        return "ERROR"

def check_equity_guardian():
    """Nuclear Safety: Liquidate all if global drawdown > 5%."""
    try:
        a = portfolio_tracker.get_analytics()
        dd = float(a.get('max_drawdown_pct', 0))
        if dd > 5.0:
            logging.critical(f"🛡️ EQUITY GUARDIAN: Global DD {dd}% detected! LIQUIDATING ALL.")
            telegram_bot.send_emergency_alert("EQUITY GUARDIAN", f"Total Drawdown {dd}% exceeded 5% limit. Emergency closure active.")
            for eid, t in traders.items():
                t.emergency_liquidate_all()
            return True
        return False
    except Exception as e:
        logging.error(f"Equity Guardian Error: {e}")
        return False

def apply_trailing_stop_engine():
    """Independent ATR-Based Trailing Stop. Moves SL to lock in profit."""
    logging.info("🛡️ Trailing Stop Engine: Scanning positions for profit protection...")
    for eid, t in traders.items():
        try:
            positions = t.get_positions()
            for p in positions:
                symbol = p['symbol']
                candles = t.get_ohlcv(symbol, timeframe='1h', limit=30)
                if not candles: continue
                
                atr = tech_analysis.calculate_atr(candles)
                curr_price = float(p.get('markPrice', 0))
                side = p['side'].upper()
                
                # Check for "Activation Profit" (ROE > 15%)
                unrealized_pnl = float(p.get('unrealizedPnl', 0))
                notional = abs(float(p.get('notional', 0) or 1))
                roe = (unrealized_pnl / (notional / float(p.get('leverage', 1)))) * 100
                
                if roe > 15.0:
                    # Calculate Trail Price (Current Price +/- 2x ATR)
                    trail_px = curr_price - (atr * 2.0) if side == 'LONG' else curr_price + (atr * 2.0)
                    
                    # Ensure we only move SL in our favor
                    old_sl = float(p.get('stopLoss', 0))
                    if (side == 'LONG' and trail_px > old_sl) or (side == 'SHORT' and (trail_px < old_sl or old_sl == 0)):
                        t.sync_sl_tp(p, sl_price=trail_px)
                        logging.info(f"[{eid.upper()}] 🎯 TRAILING SL: {symbol} shifted to {trail_px:.2f} (ROE: {roe:.1f}%)")
        except Exception as e:
            logging.debug(f"TS Engine Error for {eid}: {e}")

def trigger_mindless_safety():
    """Mindless Safety Guard: Executed when AI is down."""
    logging.info("🛡️ Mindless Safety Guard: Scanning all active positions...")
    for eid, t in traders.items():
        try:
            positions = t.get_positions()
            for p in positions:
                symbol = p['symbol']
                unrealized_pnl = float(p.get('unrealizedPnl', 0) or 0)
                notional = abs(float(p.get('notional', 0) or 1))
                pnl_pct = (unrealized_pnl / notional) * 100
                
                should_close = False
                reason = ""
                if pnl_pct > 0.5: 
                    should_close, reason = True, f"Taking Profit ({pnl_pct:.2f}%)"
                elif pnl_pct < -10: 
                    should_close, reason = True, f"Deep Loss Cut ({pnl_pct:.2f}%)"
                elif -10 <= pnl_pct <= -1:
                    should_close, reason = True, f"Moderate Loss Cut ({pnl_pct:.2f}%)"
                
                if should_close:
                    logging.warning(f"🛡️ SAFETY TRIGGER: Closing {symbol} on {eid.upper()} ({reason})")
                    t.close_position(p)
                    telegram_bot.send_emergency_alert("MINDLESS SAFETY", f"Closed {symbol} on {eid.upper()}. Reason: {reason}")
        except Exception as e:
            logging.error(f"Error in Mindless Safety: {e}")

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
    
    # AI Failure Tracking for Antifragile Safety
    consecutive_ai_failures = 0
    FAILURE_THRESHOLD = 2 # Trigger mindless safety after 2 fails
    
    # Run once at startup and manage loop manually for dynamic scheduling
    # We remove the static 60-minute schedule to support "antifragile" retries
    # schedule.every(60).minutes.do(astra_cycle)
    
    next_run_time = datetime.datetime.now()
    logging.info("Adaptive Scheduler active: 1h on success, 10s on AI failure.")
    
    # Feature 5: Start Telegram Command Listener (Interactive)
    def start_tg_listener():
        try:
            telegram_bot.setup_commands(traders, portfolio_tracker)
            telegram_bot.start_polling()
        except Exception as e:
            logging.error(f"Telegram listener failed: {e}")

    import threading
    tg_thread = threading.Thread(target=start_tg_listener, daemon=True)
    tg_thread.start()

    while True:
        now = datetime.datetime.now()

        # 1. Check if it's time for a scheduled run or a forced cycle
        if now >= next_run_time or config.FORCE_CYCLE:
            is_forced = config.FORCE_CYCLE
            config.FORCE_CYCLE = False # Reset flag
            
            if is_forced:
                logging.info("⚡ Immediate Cycle triggered by User (UI Force)")
            
            status = astra_cycle()
            
            if status == "RETRY":
                consecutive_ai_failures += 1
                # AI FAILED: Retry in 10 seconds (Antifragile logic)
                delay_sec = 10
                next_run_time = datetime.datetime.now() + datetime.timedelta(seconds=delay_sec)
                logging.warning(f"🔄 AI Brain was down ({consecutive_ai_failures}/{FAILURE_THRESHOLD}). Antifragile retry in {delay_sec} seconds...")
                
                # --- MINDLESS SAFETY GUARD ---
                if consecutive_ai_failures >= FAILURE_THRESHOLD:
                    logging.critical(f"🧠 AI Brain is unresponsive for {consecutive_ai_failures} cycles. Activating Mindless Safety Guard...")
                    trigger_mindless_safety()
            else:
                # SUCCESS: Reset counter and wait 1 hour
                if status == "SUCCESS":
                    consecutive_ai_failures = 0
                
                next_run_time = datetime.datetime.now() + datetime.timedelta(minutes=config.CYCLE_INTERVAL_MINUTES)
                logging.info(f"✅ Cycle complete. Next run at: {next_run_time.strftime('%H:%M:%S')}")
            
        schedule.run_pending()
        time.sleep(1)


if __name__ == "__main__":
    main()
