
import unittest
from unittest.mock import MagicMock, patch
from src.features.trade_executor.trader import Trader
from src.app.main import astra_cycle
from src.app.config import config

class TestAIPositionManagement(unittest.TestCase):
    def setUp(self):
        # Reset common config
        config.BOT_ACTIVE = True
        config.SYMBOLS = ["BTC/USDT:USDT"]
        config.ACTIVE_EXCHANGES = ["okx"]
        
        # Mocks for news and tech
        self.patcher_news = patch('src.app.main.news_aggregator')
        self.mock_news = self.patcher_news.start()
        self.mock_news.get_recent_headlines.return_value = ["Bullish news!", "Bitcoin reaches new high"]
        self.mock_news.get_market_sentiment.return_value = {'value': 75, 'classification': 'Greed'}
        self.mock_news.has_significant_events.return_value = True
        
        # Mock AI
        self.patcher_ai = patch('src.app.main.ai_client')
        self.mock_ai = self.patcher_ai.start()
        
        # Mock Traders collection
        self.patcher_traders = patch('src.app.main.traders')
        self.mock_traders_dict = self.patcher_traders.start()
        
        self.mock_trader = MagicMock()
        self.mock_traders_dict.items.return_value = [("okx", self.mock_trader)]
        self.mock_traders_dict.__getitem__.return_value = self.mock_trader

    def tearDown(self):
        self.patcher_news.stop()
        self.patcher_ai.stop()
        self.patcher_traders.stop()

    def test_ai_decision_close(self):
        """Scenario: AI decides to CLOSE an existing LONG position."""
        # 1. Setup existing position
        test_pos = {'symbol': 'BTC/USDT:USDT', 'side': 'long', 'contracts': 1.0, 'info': {'instId': 'BTC-USDT-SWAP'}}
        self.mock_trader.get_positions.return_value = [test_pos]
        self.mock_trader.get_balance.return_value = 1000.0
        
        # 2. Setup AI decision
        self.mock_ai.analyze_news.return_value = {
            'target_symbol': 'BTC/USDT:USDT',
            'action': 'CLOSE',
            'sentiment_score': 9,
            'reasoning': 'Profit taking.'
        }
        
        # 3. Trigger cycle
        astra_cycle()
        
        # 4. Verify Trader.close_position was called
        self.mock_trader.close_position.assert_called_once_with(test_pos)
        print("Success: AI CLOSE decision correctly triggered Trader.close_position.")

    def test_ai_decision_flip_long_to_short(self):
        """Scenario: AI decides to SELL (SHORT) while we are currently LONG."""
        # 1. Setup existing LONG
        test_pos = {'symbol': 'BTC/USDT:USDT', 'side': 'long', 'contracts': 1.0, 'info': {'instId': 'BTC-USDT-SWAP'}}
        # Initial call returns the long, subsequent calls after close should return empty
        self.mock_trader.get_positions.side_effect = [[test_pos], [test_pos], []] # 1st for cycle, 2nd for check, 3rd for settlement check
        self.mock_trader.close_position.return_value = "SUCCESS: Position Closed"
        
        # 2. Setup AI decision
        self.mock_ai.analyze_news.return_value = {
            'target_symbol': 'BTC/USDT:USDT',
            'action': 'SELL',
            'sentiment_score': 9,
            'reasoning': 'Bearish reversal.',
            'leverage': 5,
            'budget_usdt': 100
        }
        
        # 3. Trigger cycle
        astra_cycle()
        
        # 4. Verify ATOMIC FLIP: close then open
        self.mock_trader.execute_flip.assert_called_once()
        print("Success: AI REVERSE decision correctly triggered Atomic Flip.")

    def test_ai_decision_no_position_to_close(self):
        """Scenario: AI says CLOSE but we have no such position."""
        self.mock_trader.get_positions.return_value = []
        
        self.mock_ai.analyze_news.return_value = {
            'target_symbol': 'ETH/USDT:USDT',
            'action': 'CLOSE',
            'sentiment_score': 8,
            'reasoning': 'Close it.'
        }
        
        astra_cycle()
        
        # Should NOT call close_position if list is empty
        self.mock_trader.close_position.assert_not_called()
        print("Success: AI CLOSE on empty position gracefully ignored.")

if __name__ == "__main__":
    unittest.main()
