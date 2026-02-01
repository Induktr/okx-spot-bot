
import unittest
from unittest.mock import MagicMock, patch
from src.features.trade_executor.trader import Trader
from src.app.config import config

class TestNuclearClose(unittest.TestCase):
    def setUp(self):
        # Patch ccxt.okx
        self.patcher_okx = patch('ccxt.okx')
        self.mock_okx_class = self.patcher_okx.start()
        self.mock_okx_inst = self.mock_okx_class.return_value
        
        # Configure OKX mock
        self.mock_okx_inst.private_get_account_config.return_value = {'data': [{'posMode': 'long_short_mode'}]}
        self.mock_okx_inst.headers = {}
        
        # Initialize Trader
        self.trader = Trader('okx')

    def tearDown(self):
        self.patcher_okx.stop()

    def test_okx_nuclear_close_logic(self):
        """Verify OKX uses the dedicated close_position endpoint with correct params."""
        test_pos = {
            'symbol': 'BTC/USDT:USDT',
            'side': 'long',
            'marginMode': 'cross',
            'info': {
                'instId': 'BTC-USDT-SWAP',
                'posSide': 'long'
            }
        }
        
        # Setup API response for success
        self.mock_okx_inst.private_post_trade_close_position.return_value = {'code': '0', 'msg': 'Success'}
        
        # We also need to mock _verify_closure to avoid real exchange calls
        with patch.object(self.trader, '_verify_closure', return_value="SUCCESS: Verified"):
            res = self.trader.close_position(test_pos)
            
            # Check call to the specific OKX endpoint
            self.mock_okx_inst.private_post_trade_close_position.assert_called_once()
            args = self.mock_okx_inst.private_post_trade_close_position.call_args[0][0]
            
            self.assertEqual(args['instId'], 'BTC-USDT-SWAP')
            self.assertEqual(args['mgnMode'], 'cross')
            self.assertEqual(args['posSide'], 'long')
            self.assertEqual(res, "SUCCESS: Verified")
            print("Nuclear Close: OKX specific endpoint called with correct payload.")

    @patch('ccxt.binance')
    def test_binance_standard_close_logic(self, mock_binance_class):
        """Verify Binance uses standard reduceOnly market order for closing."""
        mock_binance_inst = mock_binance_class.return_value
        mock_binance_inst.amount_to_precision.return_value = "1.0"
        
        # Initialize Binance trader
        with patch('src.features.trade_executor.trader.config') as mock_config:
            # Need to mock get_keys or just skip it
            b_trader = Trader('binance')
            
            test_pos = {
                'symbol': 'ETH/USDT:USDT',
                'side': 'long',
                'contracts': 1.0,
                'info': {'posSide': 'long'}
            }
            
            with patch.object(b_trader, '_verify_closure', return_value="SUCCESS: Verified"):
                res = b_trader.close_position(test_pos)
                
                # Verify standard CCXT call
                # Long position -> Sell order
                mock_binance_inst.create_market_order.assert_called_once_with(
                    'ETH/USDT:USDT', 'sell', 1.0, {'reduceOnly': True}
                )
                self.assertEqual(res, "SUCCESS: Verified")
                print("Standard Close: Binance reduceOnly order verified.")

if __name__ == "__main__":
    unittest.main()
