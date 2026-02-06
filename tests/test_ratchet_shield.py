import unittest
from unittest.mock import MagicMock, AsyncMock, patch
import asyncio
from src.features.trade_executor.risk_manager import RiskManager

class TestRatchetShield(unittest.IsolatedAsyncioTestCase):
    """
    Test Suite for 'The Ratchet Shield' (Antifragile Profit Protection).
    Verifies that the bot locks in profits when the balance drops a certain 
    percentage from its all-time peak (High-Water Mark).
    """

    async def asyncSetUp(self):
        self.mock_tracker = MagicMock()
        self.risk = RiskManager(self.mock_tracker)
        self.risk.set_mode("OPTIMAL") # dd_limit: 25% (Standard)
        
        # Mock traders
        self.mock_trader = AsyncMock()
        self.traders = {"okx": self.mock_trader}

    async def test_ratchet_no_trigger_at_peak(self):
        """Test: Balance is at High-Water Mark -> Should NOT trigger."""
        self.mock_tracker.get_analytics.return_value = {
            "initial_balance": 100.0,
            "current_balance": 150.0,
            "high_water_mark": 150.0,
            "drawdown_from_peak": 0.0,
            "max_drawdown_pct": 0.0 # This is from initial, irrelevant here
        }
        
        result = await self.risk.check_equity_guardian(self.traders)
        self.assertFalse(result, "Should not trigger when at HWM")
        self.mock_trader.emergency_liquidate_all.assert_not_called()

    async def test_ratchet_minor_dip_no_trigger(self):
        """Test: Balance dips slightly (2%) from peak -> Should NOT trigger."""
        self.mock_tracker.get_analytics.return_value = {
            "initial_balance": 100.0,
            "current_balance": 147.0, # 150 - 2%
            "high_water_mark": 150.0,
            "drawdown_from_peak": 2.0,
            "max_drawdown_pct": 0.0
        }
        
        result = await self.risk.check_equity_guardian(self.traders)
        self.assertFalse(result, "Minor 2% dip should be allowed to survive noise")
        self.mock_trader.emergency_liquidate_all.assert_not_called()

    async def test_ratchet_major_dip_triggers_lock_in(self):
        """Test: Balance dips 6% from peak while in profit -> Should TRIGGER liquidation (Lock-in)."""
        self.mock_tracker.get_analytics.return_value = {
            "initial_balance": 100.0,
            "current_balance": 141.0, # 150 - 6%
            "high_water_mark": 150.0,
            "drawdown_from_peak": 6.0,
            "max_drawdown_pct": 0.0
        }
        
        result = await self.risk.check_equity_guardian(self.traders)
        self.assertTrue(result, "6% drop from peak should trigger Ratchet Shield to lock in profit.")
        self.mock_trader.emergency_liquidate_all.assert_called_once()

    async def test_ratchet_no_profit_no_ratchet(self):
        """Test: If we are below initial balance, ratchet shouldn't trigger (standard DD kicks in instead)."""
        self.mock_tracker.get_analytics.return_value = {
            "initial_balance": 100.0,
            "current_balance": 90.0,
            "high_water_mark": 100.0,
            "drawdown_from_peak": 10.0, # This is 10% from peak, but we are not in profit
            "max_drawdown_pct": 10.0
        }
        
        # Standard dd_limit is 25% for OPTIMAL, so 10% won't trigger standard guardian either
        result = await self.risk.check_equity_guardian(self.traders)
        self.assertFalse(result, "Ratchet shouldn't trigger if we haven't made profit above initial yet.")
        self.mock_trader.emergency_liquidate_all.assert_not_called()

if __name__ == "__main__":
    unittest.main()
