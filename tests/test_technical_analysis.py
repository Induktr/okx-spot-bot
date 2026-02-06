import unittest
from src.shared.utils.analysis import tech_analysis

class TestTechnicalAnalysis(unittest.TestCase):
    def test_rsi_calculation(self):
        """Verify RSI output for a clear uptrend."""
        # Standard RSI should be high for increasing prices
        prices = [100, 101, 102, 103, 104, 105, 106, 107, 108, 109, 110, 111, 112, 113, 114, 115]
        rsi = tech_analysis.calculate_rsi(prices, period=14)
        self.assertIsNotNone(rsi)
        self.assertGreater(rsi, 70, "RSI should be overbought (>70) for a steady uptrend")

    def test_ema_calculation(self):
        """Verify EMA reflects recent price changes more than SMA."""
        prices = [10, 10, 10, 10, 10, 20] # Sharp jump at the end
        ema = tech_analysis.calculate_ema(prices, period=5)
        self.assertIsNotNone(ema)
        self.assertGreater(ema, 10, "EMA should react to the jump to 20")

    def test_atr_calculation(self):
        """Verify ATR responds to volatility."""
        # candles: [time, open, high, low, close, vol]
        candles = [[0, 100, 110, 90, 105, 1000] for _ in range(20)]
        atr = tech_analysis.calculate_atr(candles, period=14)
        self.assertIsNotNone(atr)
        self.assertGreater(atr, 0)

if __name__ == "__main__":
    unittest.main()
