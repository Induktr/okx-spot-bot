import logging
import asyncio
from typing import Dict, Any, List, Optional
from src.app.config import config
from src.shared.utils.analysis import tech_analysis

class RiskManager:
    """
    Module 3: RiskManager
    Responsibility: Validating AI decisions against safety limits and equity protection.
    Supports dynamic modes: CONSERVATIVE, OPTIMAL, AGGRESSIVE.
    """
    def __init__(self, portfolio_tracker: Any):
        self.tracker = portfolio_tracker
        
        # Risk Profiles
        self.modes = {
            "CONSERVATIVE": {
                "min_confidence": 9.2,      # Ultra precise selections only
                "max_leverage": 3,
                "dd_limit": 20.0
            },
            "OPTIMAL": {
                "min_confidence": 8.2,      # High conviction balance
                "max_leverage": 10,
                "dd_limit": 35.0
            },
            "AGGRESSIVE": {
                "min_confidence": 7.5,      # More frequent trades (Standard momentum)
                "max_leverage": 20,
                "dd_limit": 60.0
            }
        }
        
        # Current active mode (default to OPTIMAL for Astra v1.5)
        self.current_mode = "OPTIMAL"

    def set_mode(self, mode_name: str):
        if mode_name in self.modes:
            self.current_mode = mode_name
            logging.info(f"🛡️ RISK: Profile switched to {mode_name}")

    def get_limits(self):
        return self.modes[self.current_mode]

    async def check_equity_guardian(self, traders: Dict[str, Any], context: Optional[str] = None) -> bool:
        """Nuclear Safety: Checks global drawdown, loss streaks, and market volatility."""
        try:
            analytics = self.tracker.get_analytics()
            dd = float(analytics.get('max_drawdown_pct', 0))
            limit = self.get_limits()["dd_limit"]
            loss_streak = int(analytics.get('loss_streak', 0))
            
            # --- 1. Drawdown Limit ---
            if dd > limit:
                logging.critical(f"🛡️ RISK: Global DD {dd}% exceeds limit {limit}%. Executing Emergency Exit!")
                liquidation_tasks = [t.emergency_liquidate_all() for t in traders.values()]
                await asyncio.gather(*liquidation_tasks)
                return True
            
            # --- 2. Loss-Streak Cooldown ---
            if loss_streak >= config.MAX_LOSS_STREAK:
                logging.warning(f"🛡️ RISK: Loss streak {loss_streak} reached! Enforcing cooling-off period.")
                # We return True to skip the cycle, but don't liquidate unless drawdown is high
                return True

            # --- 3. Market Circuit Breaker (Black Swan 2.0) ---
            if traders:
                primary_trader = list(traders.values())[0]
                btc_price = await primary_trader.get_ticker("BTC/USDT:USDT")
                btc_candles = await primary_trader.get_ohlcv("BTC/USDT:USDT", timeframe='1h', limit=5)
                if btc_candles and len(btc_candles) >= 2:
                    last_close = float(btc_candles[-2][4])
                    move = abs(btc_price - last_close) / last_close
                    if move >= config.CIRCUIT_BREAKER_THRESHOLD:
                        logging.critical(f"🚨 CIRCUIT BREAKER: BTC moved {move*100:.2f}% in 1h (Threshold: {config.CIRCUIT_BREAKER_THRESHOLD*100}%). Pausing all new entries.")
                        return True

            # --- 4. Ratchet Shield ---
            peak_dd = float(analytics.get('drawdown_from_peak', 0))
            hwm = float(analytics.get('high_water_mark', 0))
            if hwm > float(analytics.get('initial_balance', 0)) and peak_dd > 10.0:
                 logging.warning(f"🛡️ RISK: Ratchet Shield Triggered! Peak DD {peak_dd}% from {hwm} USDT. Locking in profits.")
                 liquidation_tasks = [t.emergency_liquidate_all() for t in traders.values()]
                 await asyncio.gather(*liquidation_tasks)
                 return True
                 
            return False
        except Exception as e:
            logging.error(f"❌ RISK GUARDIAN ERROR: {e}")
            return False

    def validate_execution(self, analysis: Dict[str, Any], total_balance: float = 1000.0) -> bool:
        """
        Anti-fragile Sanity Guard (Idea 4).
        Prevents AI 'hallucination' trades by enforcing hard mathematical limits.
        """
        decision = analysis.get('action', 'WAIT').upper()
        if decision == "WAIT": return False
        
        # 1. Conviction Check (VOSS scale 0-10)
        conviction = float(analysis.get('conviction_score') or analysis.get('sentiment_score') or 0)
        min_conf = self.get_limits()["min_confidence"]
        
        if conviction < min_conf:
            logging.info(f"🛡️ RISK: [{self.current_mode}] Conviction {conviction}/10 too low (Need {min_conf}). Blocked.")
            return False

        # 2. Hard Budget Limit (Anti-Hallucination)
        proposed_budget = float(analysis.get('budget_usdt', config.TRADE_AMOUNT))
        # Hard limit: Never allow single trade > 25% of total balance
        max_safe_budget = total_balance * 0.25
        if proposed_budget > max_safe_budget:
            logging.critical(f"🛡️ SANITY GUARD: Proposed budget {proposed_budget} exceeds 25% of balance ({max_safe_budget}). Blocked.")
            return False

        # 3. Leverage Safety
        leverage = int(analysis.get('leverage', 3))
        max_lev = self.get_limits()["max_leverage"]
        if leverage > max_lev or leverage > 15: # Hard max 15x safety
             logging.warning(f"🛡️ SANITY GUARD: Leverage {leverage} exceeds safety limit {max_lev}. Blocked.")
             return False

        return True

    async def check_market_state_sanity(self, symbol: str, trader_instance: Any, decision: str) -> bool:
        """
        Anti-fragile Engine (Idea 4).
        Blocks trades that are mathematically suicidal (e.g. buying at absolute local peak).
        """
        try:
             # Fetch 1h candles to check Bollinger Bands
             candles = await trader_instance.get_ohlcv(symbol, timeframe='1h', limit=50)
             if not candles: return True # Fallback: Allow if data unavailable
             
             closes = [float(c[4]) for c in candles]
             last_price = closes[-1]
             
             bb = tech_analysis.calculate_bollinger_bands(closes)
             if not bb: return True
             
             # 1. PEAK PROTECTION: Refuse to BUY if price is > 0.5% above Upper BB
             if decision == "BUY" and last_price > bb['upper'] * 1.005:
                 logging.warning(f"🛡️ SANITY GUARD: Refusing to BUY {symbol} at local peak ({last_price:.2f} > BB Upper {bb['upper']:.2f}).")
                 return False
             
             # 2. BOTTOM PROTECTION: Refuse to SELL if price is < 0.5% below Lower BB
             if decision == "SELL" and last_price < bb['lower'] * 0.995:
                 logging.warning(f"🛡️ SANITY GUARD: Refusing to SELL {symbol} at local bottom ({last_price:.2f} < BB Lower {bb['lower']:.2f}).")
                 return False
                 
             return True
        except Exception as e:
            logging.error(f"❌ SANITY CHECK ERROR: {e}")
            return True # Don't block on error, just log it

    async def calculate_position_safety(self, symbol: str, trader_instance: Any, pos: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Calculates safety parameters like ATR-based trailing stops."""
        try:
            candles = await trader_instance.get_ohlcv(symbol, timeframe='1h', limit=30)
            if not candles: return None
            
            atr = tech_analysis.calculate_atr(candles)
            if atr is None: return None
            
            # Fix: Defensive float conversion (ID: a5db315e)
            curr_price = float(pos.get('markPrice') or pos.get('info', {}).get('last', 0))
            
            return {
                "atr": atr,
                "recommended_sl": float(atr) * 2.0,
                "current_price": curr_price
            }
        except Exception:
            return None
