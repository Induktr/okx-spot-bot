
import unittest
from unittest.mock import MagicMock, patch
import ccxt
from src.features.trade_executor.trader import Trader, refresh_traders, traders
from src.app.config import config

class TestExchangeSwitch(unittest.TestCase):
    def setUp(self):
        # Reset config to a known state
        config.ACTIVE_EXCHANGES = ['okx']
        config.OKX_API_KEY = "test_okx_key"
        config.OKX_SECRET = "test_okx_secret"
        config.BINANCE_API_KEY = "test_binance_key"
        config.BINANCE_SECRET = "test_binance_secret"
        
        # Patch the exchange classes in ccxt
        self.patcher_okx = patch('ccxt.okx')
        self.patcher_binance = patch('ccxt.binance')
        self.patcher_bybit = patch('ccxt.bybit')
        
        self.mock_okx_class = self.patcher_okx.start()
        self.mock_binance_class = self.patcher_binance.start()
        self.mock_bybit_class = self.patcher_bybit.start()
        
        # Setup mock instances
        self.mock_okx_inst = self.mock_okx_class.return_value
        self.mock_binance_inst = self.mock_binance_class.return_value
        self.mock_bybit_inst = self.mock_bybit_class.return_value
        
        # Initialize urls structure for Binance test
        self.mock_binance_inst.urls = {'api': {'fapi': 'empty'}}
        
        # OKX needs specific mock for __init__ (private_get_account_config)
        self.mock_okx_inst.private_get_account_config.return_value = {"data": [{"posMode": "net_mode"}]}

    def tearDown(self):
        self.patcher_okx.stop()
        self.patcher_binance.stop()
        self.patcher_bybit.stop()

    def test_switch_okx_to_binance(self):
        """Verify switching from OKX to Binance updates traders collection correctly."""
        # Initial state should be OKX
        refresh_traders()
        self.assertIn('okx', traders)
        self.assertNotIn('binance', traders)
        self.assertEqual(len(traders), 1)
        print("Initial state: OKX only.")

        # Simulate user switching to Binance
        config.ACTIVE_EXCHANGES = ['binance']
        refresh_traders()
        
        self.assertNotIn('okx', traders)
        self.assertIn('binance', traders)
        self.assertEqual(len(traders), 1)
        self.mock_binance_class.assert_called()
        print("Switch successful: Binance active, OKX cleared.")

    def test_switch_with_invalid_keys_error_handling(self):
        """Verify that if one exchange fails to init, it doesn't crash the entire list."""
        self.mock_binance_class.side_effect = Exception("Invalid API Keys for Binance")
        
        config.ACTIVE_EXCHANGES = ['okx', 'binance']
        refresh_traders()
        
        # OKX should be active, Binance should be missing but system shouldn't crash
        self.assertIn('okx', traders)
        self.assertNotIn('binance', traders)
        print("Robustness: Binance init failure didn't crash OKX initialization.")

    def test_binance_demo_mode_switch(self):
        """Verify that switching to Binance Demo Trading applies correct URL overrides."""
        config.ACTIVE_EXCHANGES = ['binance']
        config.SANDBOX_MODES['binance'] = True
        
        refresh_traders()
        
        # Check if set_demo_trading was called on the mock instance
        # Note: Depending on implementation, it might be called on 'binance' instance
        self.mock_binance_inst.set_demo_trading.assert_called_once_with(True)
        self.assertEqual(self.mock_binance_inst.urls['api']['fapi'], 'https://demo-fapi.binance.com')
        print("Binance Demo: URL and Demo flags verified.")

if __name__ == "__main__":
    unittest.main()
