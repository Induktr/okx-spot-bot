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
        headlines = news_aggregator.get_recent_headlines(hours=24)
        context_str = f"Headlines: {headlines[:5]}\nRecent Mood: Bears on the move."

        if await self.risk.check_equity_guardian(traders, context=context_str):
            return "SUCCESS"

        logging.info("🚀 --- STARTING REFACTORED A.S.T.R.A. CYCLE ---")

        try:
            start_time = time.time()
            # 0. Context Gathering (Self-Preservation)
            # Fetch current balance and positions from all traders
            
            # 1. Schedule Check
            is_time, reason = self.is_trading_time()
            if not is_time:
                return "SUCCESS"

            # 2. Sensing (Global News)
            headlines = news_aggregator.get_recent_headlines(hours=24)
            
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
            if traders:
                try:
                    balance_tasks = [t.get_balance() for t in traders.values()]
                    balances = await asyncio.gather(*balance_tasks)
                    total_balance = sum(balances)
                except:
                    total_balance = 1000
            else:
                total_balance = 1000
                
            portfolio_tracker.record_snapshot(total_balance)
            logging.info(f"💰 Global Portfolio Status: {total_balance:.2f} USDT")

            if not news_aggregator.has_significant_events(headlines):
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

                if not is_volatile:
                    logging.warning("💤 Market is Quiet (No news/volatility). Skipping AI analysis.")
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
                
                analysis = ai_client.analyze_news(headlines, total_balance, context_for_ai)
                system_health.record_ai_call(True, int(analysis.get('sentiment_score', 0)))
            except Exception as ai_err:
                system_health.record_ai_call(False)
                raise ai_err
            
            # Record decision in memory
            memory_bank.store_analysis(target_symbol, analysis, market_snapshot)
            
            if not self.risk.validate_execution(analysis):
                scribe.log_cycle(analysis, f"Risk/Confidence check failed for {target_symbol}.")
                return "SUCCESS"

            # 6. Acting (Execution)
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
                ohlcv_task = primary_trader.get_ohlcv(sim, timeframe='1h', limit=50)
                
                price, candles = await asyncio.gather(ticker_task, ohlcv_task)
                
                if not price:
                    return f"- {sim}: Price Data Unavailable"
                
                ta_str = "N/A"
                if candles:
                    closes = [c[4] for c in candles]
                    rsi = tech_analysis.calculate_rsi(closes)
                    ema = tech_analysis.calculate_ema(closes)
                    trend = "BULLISH" if (price and ema and price > ema) else "BEARISH"
                    ta_str = f"{trend} (RSI: {rsi if rsi else '??'})"
                
                return f"- {sim}: Price {price} | TA: {ta_str}"
            except:
                return f"- {sim}: Error fetching data"

        # Gather all symbol data in parallel
        tasks = [fetch_single(s) for s in symbols]
        results = await asyncio.gather(*tasks)
        return "\n".join(results)

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
        leverage = min(int(analysis.get('leverage', 3)), limits["max_leverage"])
        budget = float(analysis.get('budget_usdt', config.TRADE_AMOUNT))

        async def execute_node(eid, t):
            try:
                # 1. Check Positions
                pos = await t.get_positions(target_symbol=symbol)
                
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
                            res = await t.execute_flip(symbol, pos[0], decision, budget, leverage)
                        else:
                            res = "RE-ALIGNED (Hold)"
                    else:
                        # NEW ENTRY
                        res = await t.execute_order(symbol, decision, budget, leverage)
                    
                    # 2. Protection Sync (SL/TP)
                    await asyncio.sleep(1) # Gap for settlement
                    updated_pos = await t.get_positions(target_symbol=symbol)
                    if updated_pos:
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

        # Final Log & Alert
        # Fix: ensure all results are strings before joining
        results_str = [str(r) for r in execution_results if r]
        result_msg = ", ".join(results_str)
        scribe.log_cycle(analysis, f"Async Orchestration Results: {result_msg}")
        telegram_bot.send_execution_report(symbol, decision, execution_results, {})
