
import unittest
import json
from src.app.dashboard.app import app
from src.app.config import config

class TestDashboardAPI(unittest.TestCase):
    def setUp(self):
        self.app = app.test_client()
        # Ensure we have at least one symbol for testing
        if "TEST/USDT:USDT" not in config.SYMBOLS:
            config.SYMBOLS.append("TEST/USDT:USDT")

    def test_delete_symbol_api(self):
        """Verify the backend endpoint for deleting a trading symbol."""
        target = "TEST/USDT:USDT"
        
        # 1. Check if symbol exists before
        self.assertIn(target, config.SYMBOLS)
        
        # 2. Call delete API
        response = self.app.post('/api/symbols/delete', 
                                 data=json.dumps({'symbol': target}),
                                 content_type='application/json')
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['status'], 'success')
        
        # 3. Verify it's gone from config
        self.assertNotIn(target, config.SYMBOLS)

if __name__ == "__main__":
    unittest.main()
