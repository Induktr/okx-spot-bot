import logging
import asyncio
import datetime
import time
import os
from typing import Dict, Any, List

# Core Modules
from src.features.trade_executor.screener import MarketScreener
from src.features.trade_executor.risk_manager import RiskManager
from src.shared.utils.memory_bank import memory_bank
from src.shared.utils.kaizen_manager import kaizen_manager
from src.shared.utils.system_health import system_health
from src.features.sentiment_analyzer.ai_client import ai_client
from src.features.trade_executor.trader import trader, traders
from src.shared.utils.analysis import tech_analysis
from src.shared.utils.logger import scribe
from src.app.config import config
from src.shared.providers.news_aggregator import news_aggregator
from src.shared.utils.portfolio_tracker import portfolio_tracker
from src.shared.providers.telegram_provider import telegram_bot
from src.shared.providers.macro_guardian import macro_guardian
from src.shared.providers.whale_detector import whale_detector
from src.shared.providers.price_observer import price_observer

class AstraOrchestrator:
    """
    The Grand Orchestrator (Refactored Stage 1-3).
    Coordinates separate modules to perform the trading cycle.
    """
    def __init__(self):
        self.screener = MarketScreener(traders)
        self.risk = RiskManager(portfolio_tracker)
        
        # Deployment: Switch to AGGRESSIVE to stop "cowardly" behavior
        self.risk.set_mode("AGGRESSIVE")
        logging.info("🚀 ORCHESTRATOR: Risk mode initialized to AGGRESSIVE.")
        
        # Background Guardian (v1.5.1)
        self.guardian_active = True
        asyncio.create_task(self._position_guardian())

    async def _position_guardian(self):
        """High-frequency background task to manage Trailing Stop-Losses."""
        logging.info("🛡️ POSITION GUARDIAN: Started. Monitoring for Trailing Stops...")
        while self.guardian_active:
            try:
                if not config.BOT_ACTIVE:
                    await asyncio.sleep(10)
                    continue

                for eid, t in traders.items():
                    positions = await t.get_positions()
                    for pos in positions:
                        # Only sync if we have a real position
                        if float(pos.get('contracts', 0)) != 0:
                            # Use default/conservative SL/TP for auto-syncing if not during main cycle
                            await t.sync_sl_tp(pos, tp_pct=0.3, sl_pct=0.1)
                
                # Check every 60 seconds (or 30 if you need faster)
                await asyncio.sleep(60)
            except Exception as e:
                logging.error(f"❌ GUARDIAN ERROR: {e}")
                await asyncio.sleep(10)
        
    async def run(self):
        """Main Loop: The Heart of Astra v1.5"""
        logging.info("🚀 ASTRA v1.5: SYSTEM CORES ENGAGED.")
        
        # Start high-speed price observer (Idea 3)
        await price_observer.start()
        
        while True:
            await asyncio.sleep(10)
        
    def is_trading_time(self):
        now = datetime.datetime.now()
        if now.weekday() not in config.TRADING_DAYS:
            return False, "Day Not Configured"
        start, end = config.TRADING_START_HOUR, config.TRADING_END_HOUR
        if start < end:
            if not (start <= now.hour < end): return False, f"Outside Hours ({start}-{end})"
        else:
            if not (now.hour >= start or now.hour < end): return False, f"Outside Hours"
        return True, "Active"

    async def run_cycle(self):
        """Unified cycle using decoupled modules."""
        # 1. Schedule & Safety Baseline
        is_time, reason = self.is_trading_time()
        if not is_time or not config.BOT_ACTIVE:
            logging.info(f"⏸️ SYSTEM STANDBY: {reason}")
            return "SUCCESS"

        # Sensing (Global News) for Smart Guard context
        headlines = await news_aggregator.get_recent_headlines(hours=24)
        context_str = f"Headlines: {headlines[:5]}\nRecent Mood: Bears on the move."

        if await self.risk.check_equity_guardian(traders, context=context_str):
            return "SUCCESS"

        # --- FEATURE: BLACKOUT MODE (MACRO PROTECTION) ---
        # Update calendar once an hour (or if never updated)
        if not macro_guardian.last_update or (datetime.datetime.now() - macro_guardian.last_update).total_seconds() > 3600:
            await macro_guardian.update_calendar()
            
        blackout = macro_guardian.get_blackout_status()
        is_blackout = blackout["active"]
        
        if is_blackout:
            logging.warning(f"🛡️ MACRO: BLACKOUT MODE ACTIVE! Event: {blackout['event']} in {blackout['minutes_to_event']}m. Switching to Safe-Exit Mode.")

        logging.info("🚀 --- STARTING REFACTORED A.S.T.R.A. CYCLE ---")

        try:
            start_time = time.time()
            # 0. Context Gathering (Self-Preservation)
            # Fetch current balance and positions from all traders
            
            # 1. Schedule Check
            is_time, reason = self.is_trading_time()
            if not is_time:
                return "SUCCESS"

            # 4. Context Extraction (News & Whales)
            headlines = await news_aggregator.get_recent_headlines(hours=6)
            await whale_detector.update()
            whale_summary = whale_detector.get_summary()

            # --- AI BRAIN: MULTI-LEVEL ANALYSIS ---
            input_context = {
                "balance": 0, # Will be updated after portfolio snapshot
                "news": headlines,
                "whale_data": whale_summary,
                "symbols_data": []
            }

            # --- FEATURE 6: BLACK SWAN INSURANCE ---
            raw_news_text = " ".join(headlines).lower()
            if any(word in raw_news_text for word in config.EMERGENCY_WORDS):
                logging.critical("🚨 BLACK SWAN EVENT DETECTED!")
                telegram_bot.send_emergency_alert("MARKET PANIC / EMERGENCY", "Critical keywords detected in news stream. Shielding active.")
                # Parallel Liquidation
                await asyncio.gather(*[t.emergency_liquidate_all() for t in traders.values()])
                scribe.log_cycle({"action": "EMERGENCY_EXIT"}, "System wide liquidation triggered.")
                return "SUCCESS"

            # 3. Global Portfolio Update (Always recording, even if quiet)
            total_balance = 0
            all_positions = []
            if traders:
                try:
                    balance_tasks = [t.get_balance() for t in traders.values()]
                    pos_tasks = [t.get_positions() for t in traders.values()]
                    raw_results = await asyncio.gather(*(balance_tasks + pos_tasks))
                    results: List[Any] = list(raw_results)
                    
                    trader_count = len(traders)
                    balances = [float(b) for b in results[:trader_count]]
                    pos_lists = results[trader_count:]
                    
                    total_balance = float(sum(balances))
                    for lst in pos_lists: 
                        if isinstance(lst, list): all_positions.extend(lst)
                    
                    # --- FEATURE 3: AUTONOMOUS RECONCILIATION ---
                    await self.reconcile_active_trades(all_positions)
                    
                except Exception as gather_err:
                    logging.error(f"Error gathering balance/positions: {gather_err}")
                    total_balance = 1000
            else:
                total_balance = 1000
                
            portfolio_tracker.record_snapshot(total_balance)
            logging.info(f"💰 Global Portfolio Status: {total_balance:.2f} USDT | Active Positions: {len(all_positions)}")

            # --- BLACKOUT EXIT LOGIC ---
            # If Blackout is active and we have NO positions, we can safely skip the rest.
            # If we HAVE positions, we MUST proceed to allow AI to potentially CLOSE them.
            if is_blackout and not all_positions:
                logging.info("🛡️ MACRO: Blackout active and no positions to manage. Skipping cycle.")
                return "SUCCESS"

            if not is_blackout and not news_aggregator.has_significant_events(headlines):
                # Volatility Wake-up: Even if news is quiet, check if BTC is dumping or pumping hard
                is_volatile = False
                primary_trader = list(traders.values())[0]
                try:
                    btc_price = await primary_trader.get_ticker("BTC/USDT:USDT")
                    # Check 1h candles
                    btc_candles = await primary_trader.get_ohlcv("BTC/USDT:USDT", timeframe='1h', limit=3)
                    if btc_candles and len(btc_candles) >= 2:
                        try:
                            last_close = float(btc_candles[-2][4])
                            price_move = abs(btc_price - last_close) / last_close
                            if price_move > 0.015: # 1.5% in 1h is a trigger
                                is_volatile = True
                                logging.info(f"⚡ VOLATILITY WAKE-UP: BTC moved {price_move*100:.2f}%. Analyzing market despite quiet news.")
                        except (IndexError, TypeError, ValueError):
                            pass
                except: pass

                if not is_volatile and not all_positions:
                    logging.warning("💤 Market is Quiet (No news/volatility/positions). Skipping AI analysis.")
                    return "SUCCESS"

            # 4. Screening (Asset Selection)
            final_symbols = await self.screener.get_final_selection(limit=10)
            if not final_symbols:
                return "SUCCESS"
            
            # 5. Deep Analysis & Memory Recall
            target_symbol = final_symbols[0]
            memory_summary = memory_bank.get_context_summary(target_symbol)
            market_snapshot = await self._build_snapshot(final_symbols)
            
            context_for_ai = f"{market_snapshot}\n\n{memory_summary}"
            logging.critical("📊 AI BRAIN INPUT SNAPSHOT:\n" + context_for_ai)
            
            try:
                if "RSI: ??" in context_for_ai or "TA: N/A" in context_for_ai:
                     logging.warning(f"⚠️ Technical data for {target_symbol} is incomplete. AI response might be degraded.")
                
                analysis = ai_client.analyze_news(headlines, total_balance, context_for_ai, whale_data=whale_summary, blackout_active=is_blackout)
                
                # Logic for score mapping (Dashboard expects sentiment_score)
                score = analysis.get('conviction_score', analysis.get('sentiment_score', 0))
                try:
                    score = float(score)
                except:
                    score = 0
                
                analysis['sentiment_score'] = score # Bridge for dashboard/logs
                system_health.record_ai_call(True, int(score))
            except Exception as ai_err:
                system_health.record_ai_call(False)
                raise ai_err
            
            # Record decision in memory
            memory_bank.store_analysis(target_symbol, analysis, market_snapshot)
            
            # 6. Acting (Execution) - Strict Safety Filter
            if not self.risk.validate_execution(analysis, total_balance):
                scribe.log_cycle(analysis, f"Risk/Sanity check failed for {target_symbol}.")
                return "SUCCESS"

            decision = analysis.get('action', 'WAIT').upper()
            
            # --- FEATURE 4: SUICIDAL ENTRY PREVENTION ---
            primary_trader = list(traders.values())[0] if traders else None
            if primary_trader and decision in ["BUY", "SELL"]:
                if not await self.risk.check_market_state_sanity(target_symbol, primary_trader, decision):
                    scribe.log_cycle(analysis, f"Suicidal entry blocked by Sanity Guard for {target_symbol}.")
                    return "SUCCESS"

            if is_blackout and decision in ["BUY", "SELL"]:
                logging.warning(f"🛡️ MACRO: Blocking {decision} order during Blackout. Only CLOSE allowed.")
                scribe.log_cycle(analysis, f"Blocked {decision} due to active Blackout Mode.")
                return "SUCCESS"

            await self._execute_ai_decision(analysis)
            
            # 7. Post-Cycle Development (Kaizen)
            asyncio.create_task(kaizen_manager.start_kaizen_session(target_symbol, headlines))
            
            # Record health
            latency = (time.time() - start_time) * 1000
            system_health.record_cycle(latency)
            
            return "SUCCESS"

        except Exception as e:
            logging.error(f"❌ ORCHESTRATOR ERROR: {e}")
            return "ERROR"

    async def _build_snapshot(self, symbols: List[str]) -> str:
        """Deep Analysis Snapshot for Selected Symbols (Async Parallel)."""
        if not traders: return "No Trading Nodes Active."
        
        primary_trader = list(traders.values())[0]
        
        async def fetch_single(sim):
            try:
                # Fetching multiple data points in parallel for each symbol
                ticker_task = primary_trader.get_ticker(sim)
                ohlcv_1h_task = primary_trader.get_ohlcv(sim, timeframe='1h', limit=50)
                ohlcv_15m_task = primary_trader.get_ohlcv(sim, timeframe='15m', limit=50)
                
                price, candles_1h, candles_15m = await asyncio.gather(ticker_task, ohlcv_1h_task, ohlcv_15m_task)
                
                if not price:
                    return f"- {sim}: Price Data Unavailable"
                
                ta_str = "N/A"
                if candles_1h:
                    closes_1h = [c[4] for c in candles_1h]
                    rsi_1h = tech_analysis.calculate_rsi(closes_1h)
                    ema_1h = tech_analysis.calculate_ema(closes_1h)
                    trend_1h = "BULLISH" if (price and ema_1h and price > ema_1h) else "BEARISH"
                    
                    perf_1h = 0.0
                    if len(closes_1h) >= 2:
                        perf_1h = ((price - closes_1h[-2]) / closes_1h[-2]) * 100
                    
                    # Advanced Indicators
                    macd_data = tech_analysis.calculate_macd(closes_1h)
                    bb_data = tech_analysis.calculate_bollinger_bands(closes_1h)
                    adx_val = tech_analysis.calculate_adx(candles_1h)
                    
                    macd_str = f"MACD: {macd_data['histogram']:+.4f} (Hist)" if macd_data else "MACD: N/A"
                    bb_str = f"BB: {bb_data['lower']:.1f}-{bb_data['upper']:.1f}" if bb_data else "BB: N/A"
                    adx_str = f"ADX: {adx_val:.1f} ({'Strong' if adx_val and adx_val > 25 else 'Weak'})" if adx_val else "ADX: N/A"

                    # Quantum Indicators (Idea 5)
                    hurst_val = tech_analysis.calculate_hurst(closes_1h)
                    fisher_val = tech_analysis.calculate_fisher(closes_1h)
                    
                    # Interpret Hurst
                    hurst_type = "RANDOM"
                    if hurst_val > 0.6: hurst_type = "TRENDY"
                    elif hurst_val < 0.4: hurst_type = "CHOPPY"
                    
                    hurst_str = f"Hurst: {hurst_val:.3f} ({hurst_type})"
                    fisher_str = f"Fisher: {fisher_val:+.3f}"

                    # 15m Confluence
                    confluence = "Neutral"
                    if candles_15m:
                        closes_15m = [c[4] for c in candles_15m]
                        rsi_15m = tech_analysis.calculate_rsi(closes_15m)
                        ema_15m = tech_analysis.calculate_ema(closes_15m)
                        trend_15m = "BULLISH" if (price and ema_15m and price > ema_15m) else "BEARISH"
                        
                        if trend_1h == trend_15m:
                            confluence = f"STRONG {trend_1h}"
                        else:
                            confluence = f"MIXED ({trend_1h} 1h / {trend_15m} 15m)"
                        
                        ta_str = f"Trend: {confluence} | RSI: {rsi_1h:.1f}(1h)/{rsi_15m:.1f}(15m) | {macd_str} | {bb_str} | {adx_str} | {hurst_str} | {fisher_str}"
                    else:
                        ta_str = f"Trend: {trend_1h} | RSI: {rsi_1h:.1f} | {macd_str} | {bb_str} | {adx_str} | {hurst_str} | {fisher_str}"
                
                return f"- {sim}: Price {price} | DATA: {ta_str}"
            except:
                return f"- {sim}: Error fetching data"

        # 1. Fetch Market Data
        tasks = [fetch_single(s) for s in symbols]
        results = await asyncio.gather(*tasks)
        market_data = "\n".join(results)

        # 2. Fetch Position Data
        active_pos_str = "None"
        try:
            all_active = []
            for eid, t in traders.items():
                p = await t.get_positions()
                for pos in p:
                    # ROE detection (same as RiskManager)
                    roe_raw = pos.get('percentage') or pos.get('unrealizedRoe')
                    if roe_raw is None and 'info' in pos: roe_raw = pos['info'].get('uplRatio')
                    roe = float(roe_raw or 0)
                    if -1.0 < roe < 1.0: roe *= 100
                    
                    all_active.append(f"[{eid}] {pos['symbol']} {pos['side'].upper()} | Size: {pos.get('contracts', 0)} | ROE: {roe:+.2f}%")
            
            if all_active:
                active_pos_str = "\n".join(all_active)
        except: pass

        return f"--- MARKET DATA ---\n{market_data}\n\n--- CURRENT EXPOSURE ---\n{active_pos_str}"

    async def _execute_ai_decision(self, analysis: Dict[str, Any]):
        """Executes AI decision asynchronously across all active trading nodes."""
        symbol = analysis.get('target_symbol')
        decision = analysis.get('action', 'WAIT').upper()
        confidence = float(analysis.get('sentiment_score', 0))
        
        if decision == "WAIT" or symbol == "NONE":
            return

        logging.info(f"🎬 ORCHESTRATOR: Async Execution Start -> {decision} on {symbol}")

        # Risk parameters from current mode
        limits = self.risk.get_limits()
        
        # --- FEATURE: DYNAMIC SIZING (Kelly-light) ---
        base_budget = float(analysis.get('budget_usdt', config.TRADE_AMOUNT))
        confidence = float(analysis.get('conviction_score') or analysis.get('sentiment_score') or 5)
        
        if config.DYNAMIC_SIZING_ACTIVE:
            # Scale budget: 0-4 (0.5x), 5-7 (0.8x), 8-9 (1.0x), 10 (1.2x)
            multiplier = 0.5
            if confidence >= 10: multiplier = 1.2
            elif confidence >= 8: multiplier = 1.0
            elif confidence >= 5: multiplier = 0.8
            
            budget = base_budget * multiplier
            logging.info(f"⚖️ DYNAMIC SIZING: Multiplier {multiplier}x applied (Conviction: {confidence}). Budget: {budget:.2f} USDT")
        else:
            budget = base_budget

        # --- FEATURE: ADAPTIVE LEVERAGE (ATR-based) ---
        default_leverage = min(int(analysis.get('leverage', 3)), limits["max_leverage"])
        
        # Fetch ATR safety if available
        leverage = default_leverage
        async def execute_node(eid, t):
            try:
                # 1. Check Positions
                pos = await t.get_positions(target_symbol=symbol)
                
                # ATR check for adaptive leverage (optional refinement)
                node_leverage = leverage
                if not pos and decision in ["BUY", "SELL"]:
                    safety_data = await self.risk.calculate_position_safety(symbol, t, {})
                    if safety_data:
                        # If current ATR is > 2% of price, reduce leverage by half
                        atr_pct = (safety_data['atr'] / safety_data['current_price']) * 100
                        if atr_pct > 2.0:
                            node_leverage = max(1, node_leverage // 2)
                            logging.warning(f"🛡️ ADAPTIVE LEVERAGE: High volatility ({atr_pct:.2f}% ATR). Reducing leverage to {node_leverage}x.")

                if decision == "CLOSE":
                    if pos: 
                        res = await t.close_position(pos[0])
                        return f"{eid}: {res}"
                    return f"{eid}: No pos"

                elif decision in ["BUY", "SELL"]:
                    if pos:
                        current_side = pos[0]['side'].upper()
                        target_side = "LONG" if decision == "BUY" else "SHORT"
                        if current_side != target_side:
                            # ATOMIC FLIP
                            res = await t.execute_flip(symbol, pos[0], decision, budget, node_leverage)
                        else:
                            res = "RE-ALIGNED (Hold)"
                    else:
                        # NEW ENTRY
                        res = await t.execute_order(symbol, decision, budget, node_leverage)
                    
                    # 2. Protection Sync (SL/TP)
                    await asyncio.sleep(1) # Gap for settlement
                    updated_pos = await t.get_positions(target_symbol=symbol)
                    if updated_pos:
                        # --- FEATURE: QUANTUM TRACE (Idea 5) ---
                        try:
                            # Capture metrics at entry
                            latest_candles = await t.get_ohlcv(symbol, timeframe='1h', limit=50)
                            if latest_candles:
                                c_prices = [float(c[4]) for c in latest_candles]
                                h_val = tech_analysis.calculate_hurst(c_prices)
                                f_val = tech_analysis.calculate_fisher(c_prices)
                                
                                # Log to Trace Database
                                from src.shared.providers.db_provider import db_engine
                                db_engine.update_active_trade(
                                    symbol=symbol,
                                    side=updated_pos[0]['side'],
                                    size=float(updated_pos[0]['contracts']),
                                    price=float(updated_pos[0].get('entryPrice', 0)),
                                    leverage=int(updated_pos[0].get('leverage', 1)),
                                    hurst=h_val,
                                    fisher=f_val
                                )
                                logging.info(f"🧬 QUANTUM TRACE: Captured entry state for {symbol} (H:{h_val}, F:{f_val})")
                        except Exception as q_err:
                            logging.error(f"⚠️ Trace Error: {q_err}")

                        await t.sync_sl_tp(
                            updated_pos[0], 
                            tp_pct=float(analysis.get('tp_pct', 0.3)), 
                            sl_pct=float(analysis.get('sl_pct', 0.1))
                        )
                    return f"{eid}: {res}"
            except Exception as node_err:
                return f"{eid}: Error ({str(node_err)[:30]})"

        # Execute across ALL traders in parallel
        node_tasks = [execute_node(eid, t) for eid, t in traders.items()]
        execution_results = await asyncio.gather(*node_tasks)

        # Final Log & Alert (Anti-Spam Filter)
        results_str = [str(r) for r in execution_results if r]
        result_msg = ", ".join(results_str)
        scribe.log_cycle(analysis, f"Async Orchestration Results: {result_msg}")

        # ONLY send Telegram if there was an actual action taken on at least one node
        # We skip 'RE-ALIGNED (Hold)' and 'No pos' to avoid 5-minute interval spam.
        is_meaningful = any(
            "SUCCESS" in r.upper() or 
            "FLIP" in r.upper() or 
            "CLOSED" in r.upper() or 
            "SENT" in r.upper() 
            for r in results_str
        )

        if is_meaningful:
            # Fetch latest analytics for the report
            from src.shared.utils.portfolio_tracker import portfolio_tracker
            # Use current balance if available from traders
            current_bal = None
            try:
                first_trader = list(traders.values())[0] if traders else None
                if first_trader:
                    current_bal = await first_trader.get_balance()
            except: pass
            
            analytics = portfolio_tracker.get_analytics(live_balance=current_bal)
            telegram_bot.send_execution_report(symbol, decision, execution_results, analytics)
        else:
            logging.info(f"🔕 TELEGRAM: Skipping report for {symbol} (Decision: {decision} | Result: {result_msg}) to prevent spam.")

    async def reconcile_active_trades(self, exchange_positions: List[Dict[str, Any]]):
        """
        Anti-fragile Engine (Idea 3).
        Synchronizes internal DB state with exchange reality.
        Ensures target state matches actual state across cycle restarts.
        """
        try:
            from src.shared.providers.db_provider import db_engine
            
            target_trades = db_engine.get_active_trades() # From DB
            
            # --- 1. Detect untracked positions (Exist on exchange, missing in DB) ---
            for pos in exchange_positions:
                symbol = pos['symbol']
                if symbol not in target_trades:
                    logging.info(f"🔄 RECONCILIATION: Found untracked position for {symbol}. Restoring to Target State.")
                    
                    # Quantum Trace for untracked (best effort)
                    h_val, f_val = 0.5, 0.0
                    try:
                        primary = list(traders.values())[0] if traders else None
                        if primary:
                            c = await primary.get_ohlcv(symbol, timeframe='1h', limit=50)
                            if c:
                                cp = [float(cl[4]) for cl in c]
                                h_val = tech_analysis.calculate_hurst(cp)
                                f_val = tech_analysis.calculate_fisher(cp)
                    except: pass

                    db_engine.update_active_trade(
                        symbol=symbol,
                        side=pos['side'],
                        size=float(pos['contracts']),
                        price=float(pos.get('entryPrice') or pos.get('info', {}).get('avgPx', 0)),
                        leverage=int(pos.get('leverage', 1)),
                        hurst=h_val,
                        fisher=f_val
                    )
            
            # --- 2. Detect phantom positions (Exist in DB, missing on exchange) ---
            exchange_symbols = {p['symbol'] for p in exchange_positions}
            for symbol in list(target_trades.keys()):
                if symbol not in exchange_symbols:
                    logging.warning(f"🔄 RECONCILIATION: Trade for {symbol} found in DB but missing on exchange. Clearing state.")
                    db_engine.close_active_trade(symbol)
                    
            return True
        except Exception as e:
            logging.error(f"❌ RECONCILIATION ERROR: {e}")
            return False
