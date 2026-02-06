import unittest
from unittest.mock import AsyncMock, patch, MagicMock
import asyncio
from src.features.sentiment_analyzer.ai_client import AIAgent
from src.app.orchestrator import AstraOrchestrator

class TestAITradeLogic(unittest.IsolatedAsyncioTestCase):
    """
    End-to-End Simulation Test for A.S.T.R.A. v1.5
    This test simulates a full orchestrator cycle to ensure all modules 
    (Orchestrator, AI, Trader, RiskManager) work together in harmony.
    """
    async def asyncSetUp(self):
        # 1. Setup Mock dependencies
        self.mock_trader = MagicMock()
        self.mock_trader.exchange_id = 'okx'
        self.mock_trader.get_ticker = AsyncMock(return_value=2500.0)
        self.mock_trader.get_ohlcv = AsyncMock(return_value=[[0, 2400, 2600, 2300, 2500, 1000] for _ in range(50)])
        self.mock_trader.get_positions = AsyncMock(return_value=[])
        self.mock_trader.execute_order = AsyncMock(return_value="SUCCESS: Simulated Order")
        self.mock_trader.sync_sl_tp = AsyncMock(return_value="SUCCESS: Sync")
        
        self.mock_ai = MagicMock()
        self.mock_ai.analyze_market = AsyncMock()
        
        self.mock_tracker = MagicMock()
        self.mock_tracker.get_analytics = MagicMock(return_value={"max_drawdown_pct": 0.0})
        
        # 2. Patch the global 'traders' dictionary in orchestrator
        with patch('src.app.orchestrator.traders', {'okx': self.mock_trader}):
            self.orchestrator = AstraOrchestrator()
            self.orchestrator.ai = self.mock_ai
            self.orchestrator.risk.tracker = self.mock_tracker

    async def test_full_successful_buy_cycle(self):
        """Simulate a complete cycle from Market Data -> AI Decision (BUY) -> Execution."""
        # 1. Mock AI Decision
        self.mock_ai.analyze_market.return_value = {
            "action": "BUY",
            "target_symbol": "ETH/USDT",
            "sentiment_score": 9.5, # High Conviction
            "reasoning": "Bullish breakout confirmed by test",
            "tp_pct": 5.0,
            "sl_pct": 2.0,
            "leverage": 3,
            "budget_usdt": 1000
        }

        # 2. Run Orchestrator Cycle
        with patch('src.app.orchestrator.traders', {'okx': self.mock_trader}), \
             patch('src.app.orchestrator.ai_client', self.mock_ai), \
             patch('src.app.orchestrator.news_aggregator', MagicMock(get_recent_headlines=MagicMock(return_value="Test News"))):
            # We override select_assets to return our test symbol
            self.orchestrator.screener.select_assets = MagicMock(return_value=["ETH/USDT"])
            result = await self.orchestrator.run_cycle()

        # 3. Verify Harmony
        self.assertEqual(result, "SUCCESS")
        
        # Check if Trader was called to execute the order
        self.mock_trader.execute_order.assert_called_once_with("ETH/USDT", "BUY", 1000.0, 3)
        
        # Check if SL/TP sync was called (logic: check positions again after order)
        # In orchestrator, get_positions is called before AND after execution
        self.assertGreaterEqual(self.mock_trader.get_positions.call_count, 2)

    async def test_risk_guardian_block(self):
        """Simulate a scenario where RiskManager blocks a weak AI decision."""
        # 1. Mock AI weak Decision
        self.mock_ai.analyze_market.return_value = {
            "action": "BUY",
            "sentiment_score": 6.0, # Too low for OPTIMAL mode (Need 8.0)
            "target_symbol": "ETH/USDT"
        }

        # 2. Run Cycle
        with patch('src.app.orchestrator.traders', {'okx': self.mock_trader}), \
             patch('src.app.orchestrator.ai_client', self.mock_ai), \
             patch('src.app.orchestrator.news_aggregator', MagicMock(get_recent_headlines=MagicMock(return_value="Weak News"))):
            self.orchestrator.screener.select_assets = MagicMock(return_value=["ETH/USDT"])
            result = await self.orchestrator.run_cycle()

        # 3. Verify that execution was BLOCKED
        # Order should NOT be executed because risk manager returns False in validate_execution
        self.mock_trader.execute_order.assert_not_called()
        self.assertEqual(result, "SUCCESS") # The cycle finished, but did nothing (correct behavior)

    async def test_error_handling(self):
        """Verify that the system doesn't crash if a module fails."""
        # Simulate AI crash
        self.mock_ai.analyze_market.side_effect = Exception("AI Brain Offline")

        with patch('src.app.orchestrator.traders', {'okx': self.mock_trader}):
            result = await self.orchestrator.run_cycle(symbols=["ETH/USDT"])

        self.assertEqual(result, "ERROR")
        # Ensure it didn't crash the whole thread (caught by orchestrator try/except)

if __name__ == "__main__":
    unittest.main()
