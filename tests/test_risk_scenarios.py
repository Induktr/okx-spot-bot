import unittest
from unittest.mock import MagicMock
from src.features.trade_executor.risk_manager import RiskManager

class TestRiskScenarios(unittest.TestCase):
    def setUp(self):
        self.mock_tracker = MagicMock()
        self.risk = RiskManager(self.mock_tracker)

    def test_conviction_logic_short(self):
        """Verify that sentiment 1/10 (Max Bearish) gives high conviction."""
        analysis = {
            "action": "SELL",
            "sentiment_score": 1, # Very Bearish
            "target_symbol": "ETH/USDT"
        }
        # In OPTIMAL mode, min_confidence is 8.0
        # Conviction = |1 - 5| * 2 = 8.0
        self.risk.set_mode("OPTIMAL")
        self.assertTrue(self.risk.validate_execution(analysis), "Sentiment 1 should pass OPTIMAL risk")

    def test_conviction_logic_weak(self):
        """Verify that sentiment 4/10 (Weak Bearish) is blocked in optimal mode."""
        analysis = {
            "action": "SELL",
            "sentiment_score": 4, # Weak Bearish
            "target_symbol": "ETH/USDT"
        }
        # Conviction = |4 - 5| * 2 = 2.0
        self.assertFalse(self.risk.validate_execution(analysis), "Sentiment 4 should be blocked as too low conviction")

    def test_aggressive_mode(self):
        """Verify that Aggressive mode allows lower conviction."""
        self.risk.set_mode("AGGRESSIVE") # min_conf = 6.5
        analysis = {
            "action": "BUY",
            "sentiment_score": 8.5 # Conviction = |8.5 - 5| * 2 = 7.0
        }
        self.assertTrue(self.risk.validate_execution(analysis), "Aggressive mode should allow 7.0 conviction")

if __name__ == "__main__":
    unittest.main()
