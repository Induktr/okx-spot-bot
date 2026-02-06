import unittest
from unittest.mock import MagicMock, AsyncMock, patch
import asyncio
from src.features.trade_executor.risk_manager import RiskManager

class TestSmartGuardian(unittest.IsolatedAsyncioTestCase):
    """
    Test Suite for the 'Smart Groq Guardian' functionality.
    Verifies that the bot correctly uses Groq to decide whether to 
    liquidate or hold during a drawdown limit breach.
    """
    
    async def asyncSetUp(self):
        self.mock_tracker = MagicMock()
        self.risk = RiskManager(self.mock_tracker)
        # Standard limits for testing: OPTIMAL mode (dd_limit: 25.0)
        self.risk.set_mode("OPTIMAL")
        
        # Mock traders
        self.mock_trader = AsyncMock()
        self.traders = {"okx": self.mock_trader}

    @patch("src.features.sentiment_analyzer.ai_client.ai_client.analyze_emergency_reversal")
    async def test_smart_guard_confirms_liquidation(self, mock_groq):
        """Test: Drawdown exceeded AND Groq confirms reversal -> Liquidation triggered."""
        # 1. Setup mocks
        self.mock_tracker.get_analytics.return_value = {"max_drawdown_pct": 26.0}
        mock_groq.return_value = {
            "reversal_confirmed": True,
            "reasoning": "Bearish trend confirmed by news."
        }
        
        # 2. Execute
        result = await self.risk.check_equity_guardian(self.traders)
        
        # 3. Verify
        self.assertTrue(result, "Should confirm liquidation when Groq validates reversal")
        self.mock_trader.emergency_liquidate_all.assert_called_once()

    @patch("src.features.sentiment_analyzer.ai_client.ai_client.analyze_emergency_reversal")
    async def test_smart_guard_denies_liquidation(self, mock_groq):
        """Test: Drawdown exceeded BUT Groq says it's noise -> HOLD triggered."""
        # 1. Setup mocks
        self.mock_tracker.get_analytics.return_value = {"max_drawdown_pct": 26.0}
        mock_groq.return_value = {
            "reversal_confirmed": False,
            "reasoning": "Temporary wick, primary trend still bullish."
        }
        
        # 2. Execute
        result = await self.risk.check_equity_guardian(self.traders)
        
        # 3. Verify
        self.assertFalse(result, "Should NOT liquidate when Groq says HOLD")
        self.mock_trader.emergency_liquidate_all.assert_not_called()

    async def test_no_drawdown_no_guard(self):
        """Test: No drawdown limit reached -> Groq should never even be called."""
        self.mock_tracker.get_analytics.return_value = {"max_drawdown_pct": 5.0}
        
        with patch("src.features.sentiment_analyzer.ai_client.ai_client.analyze_emergency_reversal") as mock_groq:
            result = await self.risk.check_equity_guardian(self.traders)
            self.assertFalse(result)
            mock_groq.assert_not_called()

if __name__ == "__main__":
    unittest.main()
