
import unittest
import json
from unittest.mock import patch
from src.app.dashboard.app import app
from src.shared.utils.portfolio_tracker import portfolio_tracker

class TestFreshStartStats(unittest.TestCase):
    def setUp(self):
        self.app = app.test_client()
        # Mock get_history to return exactly what we want for each test
        self.patcher = patch.object(portfolio_tracker, 'get_history')
        self.mock_get_history = self.patcher.start()
        self.mock_get_history.return_value = []

    def tearDown(self):
        self.patcher.stop()

    def test_fresh_start_analytics(self):
        """Verify that analytics engine handles 0 history cases without crashing."""
        self.mock_get_history.return_value = []
        # When history is empty, it uses the live balance as initial and current
        analytics = portfolio_tracker.get_analytics(live_balance=500.0, trade_history=[])
        
        self.assertEqual(analytics['initial_balance'], 500.0)
        self.assertEqual(analytics['current_balance'], 500.0)
        self.assertEqual(analytics['total_profit'], 0.0)
        self.assertEqual(analytics['roi_pct'], 0.0)
        self.assertEqual(analytics['is_new'], True)
        print("Safety: Fresh start (0 history) handles balance and ROI correctly.")

    def test_single_point_analytics(self):
        """Verify analytics when we have exactly one snapshot."""
        self.mock_get_history.return_value = [{"timestamp": "2026-01-01T00:00:00", "balance": 1000.0}]
        
        # Live balance increased to 1100
        analytics = portfolio_tracker.get_analytics(live_balance=1100.0, trade_history=[])
        
        self.assertEqual(analytics['total_profit'], 100.0)
        self.assertEqual(analytics['roi_pct'], 10.0)
        self.assertEqual(analytics['max_drawdown_pct'], 0.0) # No drop from peak
        print("Safety: Single point history handles growth correctly.")

if __name__ == "__main__":
    unittest.main()
