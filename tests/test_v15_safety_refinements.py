import unittest
import asyncio
import datetime
import logging
from unittest.mock import MagicMock, AsyncMock, patch, ANY
from src.app.orchestrator import AstraOrchestrator
from src.features.trade_executor.risk_manager import RiskManager
from src.features.sentiment_analyzer.ai_client import AIAgent

class TestV15SafetyRefinements(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        # Initialize Orchestrator
        self.orchestrator = AstraOrchestrator()
        
        # Define patchers
        self.patchers = [
            patch('src.app.orchestrator.news_aggregator'),
            patch('src.app.orchestrator.whale_detector'),
            patch('src.app.orchestrator.macro_guardian'),
            patch('src.app.orchestrator.memory_bank'),
            patch('src.app.orchestrator.kaizen_manager'),
            patch('src.app.orchestrator.scribe'),
            patch('src.app.orchestrator.system_health'),
            patch('src.app.orchestrator.ai_client'),
            patch('src.app.orchestrator.traders', spec=dict)
        ]
        
        self.mocks = {}
        for p in self.patchers:
            mocked = p.start()
            # Extract name from target path (e.g. 'news_aggregator')
            name = p.attribute
            self.mocks[name] = mocked

        # Configure Mocks
        self.mocks['news_aggregator'].get_recent_headlines = AsyncMock(return_value=["Market is up"])
        self.mocks['news_aggregator'].has_significant_events.return_value = True
        
        self.mocks['whale_detector'].update = AsyncMock()
        self.mocks['whale_detector'].get_summary = MagicMock(return_value="No whales")
        
        self.mocks['macro_guardian'].last_update = datetime.datetime.now()
        self.mocks['macro_guardian'].get_blackout_status.return_value = {"active": False}
        self.mocks['macro_guardian'].update_calendar = AsyncMock()
        
        self.mocks['memory_bank'].get_context_summary = MagicMock(return_value="Memory")
        self.mocks['memory_bank'].store_analysis = MagicMock()
        
        self.mocks['kaizen_manager'].start_kaizen_session = AsyncMock()
        self.mocks['scribe'].log_cycle = MagicMock()
        
        self.mocks['system_health'].record_ai_call = MagicMock()
        self.mocks['system_health'].record_cycle = MagicMock()
        
        # AI Client - analyze_news is SYNC
        self.mocks['ai_client'].analyze_news = MagicMock(return_value={
            "action": "WAIT", "target_symbol": "BTC/USDT", "sentiment_score": 5, "reasoning": "Neutral"
        })
        
        # Traders
        self.mock_trader = AsyncMock()
        self.mock_trader.get_balance = AsyncMock(return_value=1200.0)
        self.mock_trader.get_positions = AsyncMock(return_value=[{"symbol": "BTC/USDT", "side": "long"}])
        self.mock_trader.get_ticker = AsyncMock(return_value=60000.0)
        self.mock_trader.get_ohlcv = AsyncMock(return_value=[[0,0,0,0,60000],[0,0,0,0,60100]])
        
        # Configure the traders dict mock
        self.mocks['traders'].values.return_value = [self.mock_trader]
        self.mocks['traders'].items.return_value = [("okx", self.mock_trader)]
        self.mocks['traders'].__len__.return_value = 1

        # Orchestrator Internal Mocks
        self.orchestrator.is_trading_time = MagicMock(return_value=(True, "OK"))
        self.orchestrator.screener = MagicMock()
        self.orchestrator.screener.get_final_selection = AsyncMock(return_value=["BTC/USDT"])
        self.orchestrator._build_snapshot = AsyncMock(return_value="Snap")
        self.orchestrator.risk = MagicMock()
        self.orchestrator.risk.check_equity_guardian = AsyncMock(return_value=False)
        self.orchestrator.risk.validate_execution.return_value = True

    async def asyncTearDown(self):
        for p in self.patchers:
            p.stop()

    async def test_blackout_logic(self):
        """Verify Blackout Mode prevents new entries but allows EXITS."""
        # 1. Active Blackout
        self.mocks['macro_guardian'].get_blackout_status.return_value = {
            "active": True, "event": "FOMC", "minutes_to_event": 5
        }
        
        # 2. Case A: AI tries to BUY -> BLOCK
        self.mocks['ai_client'].analyze_news.return_value = {
            "action": "BUY", "target_symbol": "BTC/USDT", "sentiment_score": 9, "reasoning": "Bullish"
        }
        with patch.object(self.orchestrator, '_execute_ai_decision', new_callable=AsyncMock) as mock_exec:
            await self.orchestrator.run_cycle()
            mock_exec.assert_not_called()
            # Verify blocked reason was logged
            self.mocks['scribe'].log_cycle.assert_called_with(ANY, "Blocked BUY due to active Blackout Mode.")

        # 3. Case B: AI says CLOSE -> ALLOW
        self.mocks['ai_client'].analyze_news.return_value = {
            "action": "CLOSE", "target_symbol": "BTC/USDT", "sentiment_score": 5, "reasoning": "Exit"
        }
        with patch.object(self.orchestrator, '_execute_ai_decision', new_callable=AsyncMock) as mock_exec:
            await self.orchestrator.run_cycle()
            mock_exec.assert_called_once()
            
    def test_dynamic_sizing_rules(self):
        """Verify AI system prompt contains the new trade sizing rules."""
        agent = AIAgent()
        self.assertIn("TRADE SIZING", agent.system_instruction)
        self.assertIn("If balance < $500", agent.system_instruction)
        self.assertIn("If balance >= $500", agent.system_instruction)

if __name__ == "__main__":
    unittest.main()
