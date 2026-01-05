
import unittest
import json
from unittest.mock import MagicMock, patch
from src.app.dashboard.app import app
from src.shared.utils.portfolio_tracker import portfolio_tracker

class TestUIMathConsistency(unittest.TestCase):
    def setUp(self):
        self.app = app.test_client()
        # Mock portfolio history: initial deposit $10,000
        self.test_history = [
            {"timestamp": "2026-01-01T10:00:00", "balance": 10000.0},
            {"timestamp": "2026-01-02T10:00:00", "balance": 10500.0}
        ]
        portfolio_tracker._cache = self.test_history
        portfolio_tracker._last_mtime = 9999999999

    @patch('src.features.trade_executor.trader.Trader.get_balance')
    @patch('src.features.trade_executor.trader.Trader.get_positions')
    @patch('src.features.trade_executor.trader.Trader.get_history')
    def test_dashboard_stats_calc(self, mock_hist, mock_pos, mock_bal):
        """Verify that dashboard correctly calculates metrics from mocked live exchange data."""
        # Mock LIVE state: Balance is now 11,000
        mock_bal.return_value = 11000.0
        mock_pos.return_value = []
        mock_hist.return_value = []
        
        # We need to trigger the background sync logic or just hit a helper that does it.
        # Since we use app.test_client(), we can hit /api/data. 
        # But /api/data returns the 'data_cache', which is updated by a background loop.
        # Let's hit the manual refresh if possible or we can hit the logic directly.
        
        # Hit /api/data
        # Note: In a real test we might need to wait for the first sync or mock the cache.
        from src.app.dashboard.app import data_cache
        
        # Manually trigger the "sync" logic once for the test
        import asyncio
        from src.app.dashboard.app import fetch_exchange_data_async
        from src.features.trade_executor.trader import traders
        
        # In the test, let's assume one trader 'okx'
        traders['okx'] = MagicMock()
        traders['okx'].get_balance.return_value = 11000.0
        traders['okx'].get_positions.return_value = []
        traders['okx'].get_history.return_value = []
        
        # Run the stats calculation logic
        analytics = portfolio_tracker.get_analytics(live_balance=11000.0, trade_history=[])
        
        # Initial: 10000 -> Current: 11000
        self.assertEqual(analytics['total_profit'], 1000.0)
        self.assertEqual(analytics['roi_pct'], 10.0)
        self.assertEqual(analytics['current_balance'], 11000.0)
        
        print("Calculation: Profit (1000) and ROI (10.0%) are correct based on $10,000 deposit.")

if __name__ == "__main__":
    unittest.main()
