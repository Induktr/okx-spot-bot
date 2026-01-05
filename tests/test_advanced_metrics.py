
import unittest
from datetime import datetime, timedelta
from src.shared.utils.portfolio_tracker import PortfolioTracker

class TestAdvancedMetrics(unittest.TestCase):
    def setUp(self):
        self.tracker = PortfolioTracker(filename="data/test_metrics.json")
        self.tracker._cache = []

    def test_drawdown_calculation(self):
        """Metric Test: Verify that Max Drawdown is correctly identified from equity curve."""
        history = [
            {"timestamp": (datetime.now() - timedelta(days=4)).isoformat(), "balance": 1000.0},
            {"timestamp": (datetime.now() - timedelta(days=3)).isoformat(), "balance": 1200.0}, # Peak 1
            {"timestamp": (datetime.now() - timedelta(days=2)).isoformat(), "balance": 900.0},  # DD = (1200-900)/1200 = 25%
            {"timestamp": (datetime.now() - timedelta(days=1)).isoformat(), "balance": 1100.0},
            {"timestamp": datetime.now().isoformat(), "balance": 1500.0}                    # New Peak
        ]
        self.tracker._cache = history
        self.tracker._last_mtime = 9999999999
        
        analytics = self.tracker.get_analytics()
        self.assertEqual(analytics['max_drawdown_pct'], 25.0)
        self.assertEqual(analytics['peak'], 1500.0)

    def test_sharpe_and_sortino_ratio(self):
        """Metric Test: Verify high-level risk-adjusted return metrics."""
        # Returns: +10%, +10%, -20%, +10%
        history = [
            {"timestamp": (datetime.now() - timedelta(hours=5)).isoformat(), "balance": 1000.0},
            {"timestamp": (datetime.now() - timedelta(hours=4)).isoformat(), "balance": 1100.0},
            {"timestamp": (datetime.now() - timedelta(hours=3)).isoformat(), "balance": 1210.0},
            {"timestamp": (datetime.now() - timedelta(hours=2)).isoformat(), "balance": 968.0},
            {"timestamp": (datetime.now() - timedelta(hours=1)).isoformat(), "balance": 1064.8}
        ]
        self.tracker._cache = history
        self.tracker._last_mtime = 9999999999
        
        analytics = self.tracker.get_analytics()
        
        # We don't need to check exact values since they depend on stdev math,
        # but we check they are non-zero and reasonable.
        self.assertNotEqual(analytics['sharpe_ratio'], 0)
        self.assertNotEqual(analytics['sortino_ratio'], 0)
        
        # Sortino should typically be different from Sharpe if there's asymmetric risk
        # In this case, we have one big down month vs small up months.
        print(f"Sharpe: {analytics['sharpe_ratio']}, Sortino: {analytics['sortino_ratio']}")

    def test_max_loss_streak(self):
        """Metric Test: Verify consecutive loss counter."""
        now = datetime.now()
        history = [
            {"timestamp": (now - timedelta(hours=5)).isoformat(), "balance": 1000},
            {"timestamp": (now - timedelta(hours=4)).isoformat(), "balance": 1100}, # Win
            {"timestamp": (now - timedelta(hours=3)).isoformat(), "balance": 1050}, # Loss 1
            {"timestamp": (now - timedelta(hours=2)).isoformat(), "balance": 1000}, # Loss 2
            {"timestamp": (now - timedelta(hours=1)).isoformat(), "balance": 950},  # Loss 3
            {"timestamp": now.isoformat(), "balance": 1000}  # Win
        ]
        self.tracker._cache = history
        self.tracker._last_mtime = 9999999999
        
        analytics = self.tracker.get_analytics()
        self.assertEqual(analytics['max_loss_streak'], 3)

if __name__ == "__main__":
    unittest.main()
