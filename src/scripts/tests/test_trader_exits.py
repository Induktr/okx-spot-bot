import unittest
from unittest.mock import MagicMock, patch
import sys
import os

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.features.trade_executor.trader import Trader

class TestTraderExits(unittest.TestCase):
    def setUp(self):
        # Mock config to avoid loading real environment variables
        with patch('src.app.config.config') as mock_config:
            mock_config.OKX_API_KEY = "test_key"
            mock_config.OKX_SECRET = "test_secret"
            mock_config.OKX_PASSWORD = "test_pass"
            mock_config.SANDBOX_MODES = {"okx": True}
            
            # Initialize trader with mocked exchange
            # We also mock OKX internal config calls during init
            with patch('src.features.trade_executor.trader.ccxt.okx') as mock_okx:
                mock_okx_instance = mock_okx.return_value
                mock_okx_instance.private_get_account_config.return_value = {
                    'data': [{'posMode': 'long_short_mode'}]
                }
                self.trader = Trader(exchange_id='okx')
                # Inject a fresh mock for each test
                self.trader.exchange = MagicMock()
                self.trader.exchange.private_get_account_config.return_value = {
                    'data': [{'posMode': 'long_short_mode'}]
                }
                self.trader.exchange_id = 'okx'

    def test_okx_close_long_hedge_mode(self):
        """Verify full closure of a LONG position in Hedge Mode."""
        sample_position = {
            'symbol': 'BTC/USDT:USDT',
            'side': 'long',
            'contracts': 0.1,
            'info': {'posSide': 'long'}
        }
        
        # Action
        self.trader.close_position(sample_position)
        
        # Verification
        args, kwargs = self.trader.exchange.create_market_order.call_args
        symbol, side, amount, params = args
        
        self.assertEqual(symbol, 'BTC/USDT:USDT')
        self.assertEqual(side, 'sell')
        self.assertEqual(amount, 0.1) # Full closure verification
        self.assertEqual(params['posSide'], 'long')
        self.assertTrue(params['reduceOnly'])

    def test_okx_close_short_hedge_mode(self):
        """Verify full closure of a SHORT position in Hedge Mode."""
        sample_position = {
            'symbol': 'ETH/USDT:USDT',
            'side': 'short',
            'contracts': 1.5,
            'info': {'posSide': 'short'}
        }
        
        # Action
        self.trader.close_position(sample_position)
        
        # Verification
        args, kwargs = self.trader.exchange.create_market_order.call_args
        symbol, side, amount, params = args
        
        self.assertEqual(side, 'buy') # Buying to close short
        self.assertEqual(amount, 1.5) # Full size
        self.assertEqual(params['posSide'], 'short')

    def test_close_normalized_side_priority(self):
        """Ensure the normalized 'side' property is used for posSide to ensure full closure."""
        sample_position = {
            'symbol': 'SOL/USDT:USDT',
            'side': 'long',
            'contracts': 10,
            'info': {'posSide': 'something_else'} # Should be ignored in favor of normalized side
        }
        
        self.trader.close_position(sample_position)
        
        _, kwargs = self.trader.exchange.create_market_order.call_args
        params = _[3]
        amount = _[2]
        self.assertEqual(params['posSide'], 'long') # Normalized side wins
        self.assertEqual(amount, 10) # Full closure verification

    def test_close_full_amount_resilience(self):
        """Ensure the amount passed to creation matches contracts exactly."""
        test_amounts = [0.001, 100, 1.2345]
        for amt in test_amounts:
            pos = {'symbol': 'TEST/USDT', 'side': 'long', 'contracts': amt}
            self.trader.close_position(pos)
            args, _ = self.trader.exchange.create_market_order.call_args
            self.assertEqual(args[2], amt) # Amount MUST match contracts for full exit

    def test_okx_pos_side_mismatch_error_message(self):
        """Verify custom error message for OKX error code 51000."""
        self.trader.exchange.create_market_order.side_effect = Exception("error_code: 51000, message: some error")
        
        res = self.trader.close_position({'symbol': 'BTC', 'side': 'long', 'contracts': 1})
        
        self.assertIn("OKX posSide mismatch", res)
        self.assertIn("Bot Mode: long_short_mode", res)
        self.assertIn("Check OKX Settings", res)

if __name__ == '__main__':
    unittest.main()
