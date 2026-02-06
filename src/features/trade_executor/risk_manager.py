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

    async def check_equity_guardian(self, traders: Dict[str, Any]) -> bool:
        """Nuclear Safety: Checks if global drawdown exceeds threshold."""
        try:
            analytics = self.tracker.get_analytics()
            dd = float(analytics.get('max_drawdown_pct', 0))
            limit = self.get_limits()["dd_limit"]
            
            if dd > limit:
                logging.critical(f"🛡️ RISK: Global DD {dd}% exceeds mode {self.current_mode} limit {limit}%!")
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
