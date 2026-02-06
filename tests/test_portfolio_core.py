import os
import json
import unittest
from datetime import datetime
from src.shared.utils.portfolio_tracker import PortfolioTracker

class TestPortfolioCore(unittest.TestCase):
    def setUp(self):
        # Use a temporary test file
        self.test_filename = "test_portfolio_history.json"
        if os.path.exists(self.test_filename):
            os.remove(self.test_filename)
        self.tracker = PortfolioTracker(filename=self.test_filename)

    def tearDown(self):
        if os.path.exists(self.test_filename):
            os.remove(self.test_filename)

    def test_initial_capital_detection(self):
        """Verify that Initial Capital is correctly pulled from the first history entry."""
        # Simulate history
        history = [
            {"timestamp": "2026-01-01T10:00:00", "balance": 50000.0},
            {"timestamp": "2026-01-01T11:00:00", "balance": 55000.0}
        ]
        with open(self.test_filename, "w") as f:
            json.dump(history, f)
        
        analytics = self.tracker.get_analytics(live_balance=60000.0)
        
        self.assertEqual(analytics["initial_balance"], 50000.0)
        self.assertEqual(analytics["current_balance"], 60000.0)
        self.assertEqual(analytics["net_profit"], 10000.0)
        self.assertEqual(analytics["roi_pct"], 20.0)

    def test_empty_history_fallback(self):
        """Verify behavior when no history exists."""
        analytics = self.tracker.get_analytics(live_balance=1000.0)
        self.assertEqual(analytics["initial_balance"], 1000.0)
        self.assertEqual(analytics["net_profit"], 1000.0) # If new, whole balance is profit vs 0 initial seed

    def test_snapshot_recording(self):
        """Test if snapshots are correctly saved and rounded."""
        self.tracker.record_snapshot(1234.567)
        history = self.tracker.get_history()
        self.assertEqual(len(history), 1)
        self.assertEqual(history[0]["balance"], 1234.57)

if __name__ == "__main__":
    unittest.main()
