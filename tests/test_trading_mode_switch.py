
import unittest
from unittest.mock import MagicMock, patch
from src.features.trade_executor.trader import Trader, refresh_traders, traders
from src.app.config import config

class TestTradingModeSwitch(unittest.TestCase):
    def setUp(self):
        # Setup baseline config
        config.ACTIVE_EXCHANGES = ['okx']
        config.OKX_API_KEY = "REAL_KEY"
        config.OKX_SECRET = "REAL_SECRET"
        config.OKX_PASSWORD = "REAL_PASSWORD"
        config.SANDBOX_MODES = {'okx': True} # Start in Demo
        
        # Patch ccxt
        self.patcher_okx = patch('ccxt.okx')
        self.mock_okx_class = self.patcher_okx.start()
        
        self.created_instances = []
        
        # Helper to create fresh mock instances
        def create_mock_okx(*args, **kwargs):
            mock_inst = MagicMock()
            mock_inst.headers = {}
            mock_inst.private_get_account_config.return_value = {"data": [{"posMode": "net_mode"}]}
            self.created_instances.append(mock_inst)
            return mock_inst
            
        self.mock_okx_class.side_effect = create_mock_okx

    def tearDown(self):
        self.patcher_okx.stop()

    def test_switch_demo_to_real(self):
        """Verify that switching from Demo to Real applies keys and disables sandbox headers."""
        # 1. Initial State: Demo
        refresh_traders()
        initial_mock = self.created_instances[-1]
        self.assertTrue(config.SANDBOX_MODES['okx'])
        # In demo, OKX has a special header
        self.assertEqual(initial_mock.headers.get('x-simulated-trading'), '1')
        print("Initial: Demo Mode active (Header x-simulated-trading=1 detected).")

        # 2. Switch to REAL
        config.SANDBOX_MODES['okx'] = False
        refresh_traders()
        
        # Verify the new instance has REAL keys and NO demo headers
        new_mock_inst = self.created_instances[-1]
        last_call_args = self.mock_okx_class.call_args[0][0]
        self.assertEqual(last_call_args['apiKey'], "REAL_KEY")
        
        self.assertNotIn('x-simulated-trading', new_mock_inst.headers)
        print("Success: Switched to REAL mode. Headers cleared, Real keys applied.")

    def test_switch_real_to_demo(self):
        """Verify that switching from Real to Demo re-activates sandbox protection."""
        # 1. Start in REAL
        config.SANDBOX_MODES['okx'] = False
        refresh_traders()
        
        # 2. Switch to DEMO
        config.SANDBOX_MODES['okx'] = True
        refresh_traders()
        
        # Get the latest instance
        new_mock_inst = self.created_instances[-1]
        self.assertEqual(new_mock_inst.headers.get('x-simulated-trading'), '1')
        print("Success: Switched to DEMO mode. Sandbox safety header re-applied.")

if __name__ == "__main__":
    unittest.main()
