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
            self.trader = Trader(exchange_id='okx')
            # Mock the CCXT exchange instance
            self.trader.exchange = MagicMock()
            self.trader.exchange_id = 'okx'

    def test_okx_close_position_hedge_mode(self):
        """Verify that OKX close_position sends correct posSide and tdMode in Hedge Mode."""
        # Setup Hedge Mode state
        self.trader.pos_mode = 'long_short_mode'
        
        sample_position = {
            'symbol': 'SOL/USDT:USDT',
            'side': 'long',
            'contracts': 1.0,
            'entryPrice': 100.0
        }
        
        # Action
        self.trader.close_position(sample_position)
        
        # Verification
        # Should call create_market_order(symbol, side, amount, params)
        # For a LONG position, closing side should be 'sell'
        self.trader.exchange.create_market_order.assert_called_once()
        args, kwargs = self.trader.exchange.create_market_order.call_args
        
        symbol, side, amount, params = args
        
        self.assertEqual(symbol, 'SOL/USDT:USDT')
        self.assertEqual(side, 'sell')
        self.assertEqual(amount, 1.0)
        
        # Critical parameters for OKX Hedge Mode
        self.assertTrue(params['reduceOnly'])
        self.assertEqual(params['tdMode'], 'cross')
        self.assertEqual(params['posSide'], 'long')

    def test_okx_close_position_short(self):
        """Verify closing a SHORT position on OKX."""
        self.trader.pos_mode = 'long_short_mode'
        
        sample_position = {
            'symbol': 'BTC/USDT:USDT',
            'side': 'short',
            'contracts': 0.1,
            'entryPrice': 50000.0
        }
        
        self.trader.close_position(sample_position)
        
        args, kwargs = self.trader.exchange.create_market_order.call_args
        symbol, side, amount, params = args
        
        self.assertEqual(side, 'buy') # To close a short, we must buy
        self.assertEqual(params['posSide'], 'short')
        self.assertEqual(params['tdMode'], 'cross')

if __name__ == '__main__':
    unittest.main()
