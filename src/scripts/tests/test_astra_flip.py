import unittest
from unittest.mock import MagicMock, patch, call
import sys
import os
import time

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.features.trade_executor.trader import Trader
from src.app.main import astra_cycle

class TestAstraFlip(unittest.TestCase):
    def setUp(self):
        # Mocks
        self.mock_config = patch('src.app.main.config').start()
        # Use patch.dict for the traders global dict
        from src.features.trade_executor import trader as trader_module
        self.mock_traders_dict = {'okx': MagicMock()}
        patch.dict(trader_module.traders, self.mock_traders_dict, clear=True).start()
        
        self.mock_ai = patch('src.app.main.ai_client').start()
        self.mock_ta = patch('src.app.main.tech_analysis').start()
        self.mock_ta.calculate_rsi.return_value = 50.0
        self.mock_ta.calculate_ema.return_value = 49000.0
        
        self.mock_news = patch('src.app.main.news_aggregator').start()
        self.mock_scribe = patch('src.app.main.scribe').start()
        self.mock_portfolio = patch('src.app.main.portfolio_tracker').start()
        self.mock_tg = patch('src.app.main.telegram_bot').start()

        # Config setup
        self.mock_config.BOT_ACTIVE = True
        self.mock_config.SYMBOLS = ["BTC/USDT:USDT"]
        self.mock_config.EMERGENCY_WORDS = ["crash", "hacked"]
        self.mock_config.WHALE_MOVE_THRESHOLD = 1000
        
        # Trader Mock Setup
        self.trader = self.mock_traders_dict['okx']
        self.trader.exchange_id = 'okx'
        self.trader.exchange = MagicMock()
        self.trader.exchange.markets = {"BTC/USDT:USDT": True}
        self.trader.exchange.fetch_ticker.return_value = {'last': 50000.0, 'quoteVolume': 10000000}
        self.trader.exchange.market.return_value = {"contractSize": 1, "limits": {"amount": {"min": 0.001}}}
        
        self.trader.get_balance.return_value = 1000.0
        self.trader.get_ticker.return_value = 50000.0
        self.trader.get_free_balance.return_value = 1000.0
        self.trader.get_funding_rate.return_value = 0.0001
        self.trader.get_ohlcv.return_value = [[None, None, None, None, 50000.0]] * 50

    def tearDown(self):
        patch.stopall()

    def test_trader_init_pos_mode_live(self):
        """Verify Trader detects posMode even when not in demo mode."""
        with patch('src.features.trade_executor.trader.ccxt.okx') as mock_okx_class:
            mock_okx = mock_okx_class.return_value
            mock_okx.private_get_account_config.return_value = {
                'data': [{'posMode': 'long_short_mode'}]
            }
            
            # Initialize with is_demo = False
            with patch('src.features.trade_executor.trader.config') as mock_cfg:
                mock_cfg.SANDBOX_MODES = {'okx': False}
                trader = Trader(exchange_id='okx')
                
                self.assertEqual(trader.pos_mode, 'long_short_mode')
                # Verify it called private_get_account_config
                mock_okx.private_get_account_config.assert_called_once()

    def test_flip_failure_position_still_exists(self):
        """Scenario: AI wants to flip, but position fails to close (remains active)."""
        # 1. Market Snapshot data
        headline_list = ["Bitcoin is mooning", "Bull market confirmed"]
        self.mock_news.get_recent_headlines.return_value = headline_list
        self.mock_news.get_market_sentiment.return_value = {"value": 8, "classification": "Greed"}
        self.mock_news.has_significant_events.return_value = True
        
        self.trader.get_balance.return_value = 1000.0
        self.trader.get_ticker.return_value = 50000.0
        self.trader.get_funding_rate.return_value = 0.0001
        
        # Current position is SHORT
        short_pos = {'symbol': 'BTC/USDT:USDT', 'side': 'short', 'contracts': 0.1, 'notional': 5000}
        self.trader.get_positions.side_effect = [
            [short_pos], # During snapshot
            [short_pos], # First check in execute loop (exists)
            [short_pos]  # SECOND check in execute loop (STILL EXISTS after close attempt)
        ]
        
        # 2. AI Decision: Flip to LONG
        self.mock_ai.analyze_news.return_value = {
            'target_symbol': 'BTC/USDT:USDT',
            'action': 'BUY',
            'sentiment_score': 9,
            'reasoning': 'Flipping Short to Long',
            'leverage': 10,
            'budget_usdt': 100
        }
        
        # 3. Action
        with patch('src.app.main.time.sleep'): # Don't actually wait
            astra_cycle()
            
        # 4. Verifications
        # Should call close_position
        self.trader.close_position.assert_called_once_with(short_pos)
        
        # Should NOT call execute_order because flip verification failed
        self.trader.execute_order.assert_not_called()
        
        # Should log the failure to scribe
        scribe_calls = self.mock_scribe.log_cycle.call_args_list
        self.assertTrue(any("Flip Failed" in str(c) for c in scribe_calls))

    def test_flip_success_cycle(self):
        """Scenario: AI wants to flip, position closes, then opens new one."""
        self.mock_news.get_recent_headlines.return_value = ["Bullish news"]
        self.mock_news.get_market_sentiment.return_value = {"value": 8, "classification": "Greed"}
        self.mock_news.has_significant_events.return_value = True
        
        self.trader.get_balance.return_value = 1000.0
        self.trader.get_ticker.return_value = 50000.0
        
        short_pos = {'symbol': 'BTC/USDT:USDT', 'side': 'short', 'contracts': 0.1}
        self.trader.get_positions.side_effect = [
            [short_pos], # Snapshot
            [short_pos], # Flip check 1
            [],          # Flip check 2 (Success, gone)
            [{'symbol': 'BTC/USDT:USDT', 'side': 'long'}] # Post-execution sync check
        ]
        
        self.mock_ai.analyze_news.return_value = {
            'target_symbol': 'BTC/USDT:USDT',
            'action': 'BUY',
            'sentiment_score': 9,
            'budget_usdt': 100
        }
        
        with patch('src.app.main.time.sleep'):
            astra_cycle()
            
        self.trader.close_position.assert_called_once()
        self.trader.execute_order.assert_called_once_with('BTC/USDT:USDT', 'BUY', 100.0, leverage=3)
        self.trader.sync_sl_tp.assert_called_once()

    def test_insufficient_free_margin(self):
        """Verify execute_order rejects if free margin is too low."""
        # We need to test the Trader method directly for this
        with patch('src.features.trade_executor.trader.ccxt.okx') as mock_okx:
            trader = Trader(exchange_id='okx')
            trader.exchange = MagicMock()
            trader.exchange.markets = {"BTC/USDT:USDT": True}
            trader.exchange.market.return_value = {"contractSize": 1, "limits": {"amount": {"min": 0.001}}}
            trader.get_free_balance = MagicMock(return_value=10.0) # Only 10 USDT free
            trader.get_ticker = MagicMock(return_value=50000.0)
            
            result = trader.execute_order('BTC/USDT:USDT', 'BUY', 100.0)
            
            self.assertIn("Margin Error", result)
            self.assertIn("only have 10.00 USDT free", result)

if __name__ == '__main__':
    unittest.main()
