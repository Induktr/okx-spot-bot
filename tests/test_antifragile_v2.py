import unittest
from unittest.mock import MagicMock, AsyncMock, patch
import asyncio
import os
import json
from src.features.trade_executor.risk_manager import RiskManager
from src.shared.utils.portfolio_tracker import PortfolioTracker
from src.app.config import config

class TestAntifragileMaster(unittest.IsolatedAsyncioTestCase):
    """
    Ultimate Proof Suite for A.S.T.R.A v1.5.3 Antifragile Controllers.
    Verifies:
    1. Ratchet Shield (Profit Protection)
    2. Smart Guardian (Groq Reasoning)
    3. Mode-Aware Safety (Real vs Demo separation)
    """

    async def asyncSetUp(self):
        # Create a fresh tracker with test files
        self.test_real = "test_portfolio_real.json"
        self.test_demo = "test_portfolio_demo.json"
        
        # Manually create files to avoid conflict
        for f in [self.test_real, self.test_demo]:
            if os.path.exists(f): os.remove(f)
            with open(f, "w") as j: json.dump([], j)

        # We need to ensure PortfolioTracker doesn't use the default paths
        self.tracker = PortfolioTracker(filename=self.test_real)
        self.tracker.filename_real = self.test_real
        self.tracker.filename_demo = self.test_demo
        self.tracker.filename = self.test_real # Start with real
        
        self.risk = RiskManager(self.tracker)
        self.mock_trader = AsyncMock()
        self.traders = {"okx": self.mock_trader}

    async def asyncTearDown(self):
        # Close any open file handles if they existed (PortfolioTracker doesn't keep persistent ones)
        for f in [self.test_real, self.test_demo]:
            try:
                if os.path.exists(f): os.remove(f)
            except: pass

    async def test_ratchet_shield_locks_profit(self):
        """Proof: If we drop 5% from peak while in profit, we LIQUIDATE."""
        # 1. Setup History: Started at 100, peaked at 150
        self.tracker.record_snapshot(100.0)
        self.tracker.record_snapshot(150.0)
        
        # 2. Current state: 141.0 (Drop > 5% from 150)
        # We simulate the call in RiskManager which uses analytics
        with patch.object(self.tracker, 'get_analytics') as mock_analytics:
            mock_analytics.return_value = {
                "initial_balance": 100.0,
                "current_balance": 141.0,
                "high_water_mark": 150.0,
                "drawdown_from_peak": 6.0, # (150-141)/150 = 6%
                "max_drawdown_pct": 0.0
            }
            
            result = await self.risk.check_equity_guardian(self.traders)
            self.assertTrue(result, "Ratchet Shield should trigger at 6% drop from peak")
            self.mock_trader.emergency_liquidate_all.assert_called_once()

    @patch("src.features.sentiment_analyzer.ai_client.ai_client.analyze_emergency_reversal")
    async def test_smart_guardian_overrides_drawdown(self, mock_groq):
        """Proof: If DD is hit but Groq says HOLD, we don't liquidate."""
        self.risk.set_mode("OPTIMAL") # 25% limit
        
        with patch.object(self.tracker, 'get_analytics') as mock_analytics:
            mock_analytics.return_value = {
                "max_drawdown_pct": 26.0,
                "drawdown_from_peak": 0.0,
                "initial_balance": 1000.0,
                "high_water_mark": 1000.0,
                "current_balance": 740.0
            }
            
            # Groq says HOLD
            mock_groq.return_value = {"reversal_confirmed": False, "reasoning": "Fake dip"}
            
            result = await self.risk.check_equity_guardian(self.traders, context="Test News")
            self.assertFalse(result, "Smart Guardian should prevent liquidation if Groq says HOLD")
            self.mock_trader.emergency_liquidate_all.assert_not_called()

    async def test_mode_aware_safety_separation(self):
        """Proof: Real history doesn't cause false alarms in Demo mode."""
        # 1. Record REAL history with high peak
        self.tracker.set_demo_mode(False)
        self.tracker.record_snapshot(62000.0)
        
        # 2. Switch to DEMO mode (Sandbox)
        self.tracker.set_demo_mode(True)
        # Demo balance is 1000
        self.tracker.record_snapshot(1000.0)
        
        # 3. Check Guardian
        # If the separation works, the HWM for Demo is 1000, not 62000.
        # dd_from_peak should be 0, not 98%.
        
        analytics = self.tracker.get_analytics()
        self.assertEqual(analytics["high_water_mark"], 1000.0)
        self.assertEqual(analytics["drawdown_from_peak"], 0.0)
        
        result = await self.risk.check_equity_guardian(self.traders)
        self.assertFalse(result, "Demo mode should not trigger based on Real HWM")
        self.mock_trader.emergency_liquidate_all.assert_not_called()

if __name__ == "__main__":
    unittest.main()
