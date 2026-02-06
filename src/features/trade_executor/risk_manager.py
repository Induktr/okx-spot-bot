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
                "min_confidence": 9.5,      # Almost perfect setup required
                "max_leverage": 3,          # Low leverage to survive swings
                "dd_limit": 15.0            # Strict drawdown protection
            },
            "OPTIMAL": {
                "min_confidence": 8.0,      # Good setup
                "max_leverage": 7,          # Balanced leverage
                "dd_limit": 25.0            # Standard protection
            },
            "AGGRESSIVE": {
                "min_confidence": 6.5,      # Willing to bet on weaker trends
                "max_leverage": 15,         # High leverage (requires manual skill)
                "dd_limit": 40.0            # High tolerance for account swings
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
        """Nuclear Safety: Checks if global drawdown exceeds threshold, now with Groq Smart-Check."""
        try:
            analytics = self.tracker.get_analytics()
            dd = float(analytics.get('max_drawdown_pct', 0))
            limit = self.get_limits()["dd_limit"]
            
            if dd > limit:
                logging.warning(f"🛡️ RISK: Global DD {dd}% exceeds mode {self.current_mode} limit {limit}%. Consulting Groq Smart-Guard...")
                
                # Smart Guard Check
                from src.features.sentiment_analyzer.ai_client import ai_client
                reversal_analysis = await ai_client.analyze_emergency_reversal(context or "Drawdown limit reached. Unknown context.")
                
                if reversal_analysis.get("reversal_confirmed", True):
                    logging.critical(f"🛡️ RISK: REVERSAL CONFIRMED by Smart-Guard. Liquidating! Reasoning: {reversal_analysis.get('reasoning')}")
                    liquidation_tasks = [t.emergency_liquidate_all() for t in traders.values()]
                    await asyncio.gather(*liquidation_tasks)
                    return True
                else:
                    logging.info(f"🛡️ RISK: Smart-Guard says HOLD. reasoning: {reversal_analysis.get('reasoning')}. Ignoring DD limit for this cycle.")
                    return False
            
            # --- FEATURE: THE RATCHET SHIELD (Idea 3) ---
            # Adaptive Profit Protection based on High-Water Mark
            peak_dd = float(analytics.get('drawdown_from_peak', 0))
            hwm = float(analytics.get('high_water_mark', 0))
            
            # Ratchet logic: if we are in profit (> initial) and drop 5% from peak, lock it in.
            # This is "Antifragile" because it captures gains as they happen.
            if hwm > float(analytics.get('initial_balance', 0)) and peak_dd > 5.0:
                 logging.warning(f"🛡️ RISK: Ratchet Shield Triggered! Peak DD {peak_dd}% from {hwm} USDT. Locking in profits.")
                 liquidation_tasks = [t.emergency_liquidate_all() for t in traders.values()]
                 await asyncio.gather(*liquidation_tasks)
                 return True
                 
            return False
        except Exception as e:
            logging.error(f"❌ RISK GUARDIAN ERROR: {e}")
            return False

    def validate_execution(self, analysis: Dict[str, Any]) -> bool:
        """Validates if the trade proposed by AI meets conviction criteria."""
        decision = analysis.get('action', 'WAIT').upper()
        sentiment_score = float(analysis.get('sentiment_score', 5))
        min_conf = self.get_limits()["min_confidence"]
        
        if decision == "WAIT":
            return False
            
        # Conviction is the distance from Neutral (5)
        # 0 or 10 -> High Conviction (Max 5)
        # 5 -> No Conviction (0)
        # We normalize this to 0-10 scale
        conviction = abs(sentiment_score - 5) * 2
        
        if decision in ["BUY", "SELL"] and conviction < min_conf:
            logging.info(f"🛡️ RISK: [{self.current_mode}] Conviction {conviction}/10 too low (Need {min_conf}). Blocked.")
            return False
            
        return True

    async def calculate_position_safety(self, symbol: str, trader_instance: Any, pos: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Calculates safety parameters like ATR-based trailing stops."""
        try:
            candles = await trader_instance.get_ohlcv(symbol, timeframe='1h', limit=30)
            if not candles: return None
            
            atr = tech_analysis.calculate_atr(candles)
            if atr is None: return None
            
            curr_price = float(pos.get('markPrice', 0))
            
            return {
                "atr": atr,
                "recommended_sl": float(atr) * 2.0,
                "current_price": curr_price
            }
        except Exception:
            return None
