
import unittest
from datetime import datetime, timedelta
from src.shared.utils.portfolio_tracker import PortfolioTracker

class TestPortfolioMath(unittest.TestCase):
    def setUp(self):
        # Create a tracker with a dummy file for testing
        self.tracker = PortfolioTracker(filename="data/test_history.json")
        self.tracker._cache = []
        
    def test_analytics_fallback_logic(self):
        """Test if Profit Factor is calculated correctly from balance snapshots when trades are missing."""
        # 1. Simulate a series of balance snapshots
        # Start at 100, Win to 150, Loss to 130
        history = [
            {"timestamp": (datetime.now() - timedelta(hours=2)).isoformat(), "balance": 100.0},
            {"timestamp": (datetime.now() - timedelta(hours=1, minutes=30)).isoformat(), "balance": 120.0}, # Added snapshot
            {"timestamp": (datetime.now() - timedelta(hours=1)).isoformat(), "balance": 150.0},
            {"timestamp": (datetime.now() - timedelta(minutes=30)).isoformat(), "balance": 140.0}, # Added snapshot
            {"timestamp": datetime.now().isoformat(), "balance": 130.0}
        ]
        
        # Inject history into tracker (bypassing file for speed)
        self.tracker._cache = history
        self.tracker._last_mtime = 9999999999 
        
        # Calculate analytics
        # total_win_val should be 50 (150-100)
        # total_loss_val should be 20 (150-130)
        # Expected Profit Factor: 50 / 20 = 2.5
        
        analytics = self.tracker.get_analytics(live_balance=130.0, trade_history=[])
        
        self.assertEqual(analytics['profit_factor'], 2.5)
        self.assertEqual(analytics['total_profit'], 30.0)
        self.assertEqual(analytics['win_rate'], 50.0) # 1 win, 1 loss

    def test_roi_calculation(self):
        """Verify ROI percentage math with at least 2 history points."""
        history = [
            {"timestamp": (datetime.now() - timedelta(minutes=10)).isoformat(), "balance": 1000.0},
            {"timestamp": datetime.now().isoformat(), "balance": 1000.0}
        ]
        self.tracker._cache = history
        self.tracker._last_mtime = 9999999999
        
        # Current balance 1100, 10 USDT in fees
        # Net Profit = 100 - 10 = 90
        # ROI = 90 / 1000 * 100 = 9.0%
        analytics = self.tracker.get_analytics(live_balance=1100.0, trade_history=[{'cost': 20000, 'symbol': 'BTC/USDT'}])
        
        # Fees: 20000 * 0.0005 = 10
        self.assertEqual(analytics['fees'], 10.0)
        self.assertEqual(analytics['roi_pct'], 9.0)

if __name__ == "__main__":
    unittest.main()
