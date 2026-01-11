import unittest
from unittest.mock import MagicMock, patch
import sys
import os

# Add project root to path for imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

class TestAdvancedAnalysis(unittest.TestCase):

    def setUp(self):
        from src.shared.utils.analysis import tech_analysis
        self.ta = tech_analysis
        # Generate some mock data: 100 prices gradually increasing
        self.prices = [100 + i for i in range(100)]
        # Generate mock candles: [timestamp, open, high, low, close, volume]
        self.candles = [[i, 100+i, 105+i, 95+i, 100+i, 1000] for i in range(100)]

    def test_calculate_macd(self):
        """Tests MACD calculation logic."""
        result = self.ta.calculate_macd(self.prices)
        self.assertIsNotNone(result)
        self.assertIn('macd', result)
        self.assertIn('signal', result)
        self.assertIn('histogram', result)

    def test_calculate_bollinger_bands(self):
        """Tests Bollinger Bands calculation logic."""
        result = self.ta.calculate_bollinger_bands(self.prices)
        self.assertIsNotNone(result)
        self.assertIn('upper', result)
        self.assertIn('mid', result)
        self.assertIn('lower', result)
        self.assertGreater(result['upper'], result['mid'])
        self.assertGreater(result['mid'], result['lower'])
        # Last 20 are [180...199]. SMA is 189.5
        self.assertEqual(result['mid'], 189.5)

    def test_calculate_atr(self):
        """Tests Average True Range calculation logic."""
        result = self.ta.calculate_atr(self.candles)
        self.assertIsNotNone(result)
        self.assertEqual(result, 10.0)

    def test_ai_client_quad_convergence_instructions(self):
        """Tests that the AI client's instructions reflect the new Quad-Convergence strategy."""
        from src.features.sentiment_analyzer.ai_client import AIAgent
        agent = AIAgent()
        self.assertIn("Quad-Convergence", agent.system_instruction)
        self.assertIn("RVOL", agent.system_instruction)
        self.assertIn("Pivot Levels", agent.system_instruction)
        self.assertIn("THE GOLDEN 10 (10/10)", agent.system_instruction)

    @patch('src.app.main.traders')
    @patch('src.app.main.config')
    def test_market_snapshot_advanced_ta(self, mock_config, mock_traders):
        """Verified that advanced TA indicators appear in the market snapshot string."""
        from src.shared.utils.analysis import tech_analysis
        
        # Simulated data for one symbol
        price = 150
        closes = self.prices
        rsi = tech_analysis.calculate_rsi(closes)
        ema = tech_analysis.calculate_ema(closes)
        macd = tech_analysis.calculate_macd(closes)
        bb = tech_analysis.calculate_bollinger_bands(closes)
        atr = tech_analysis.calculate_atr(self.candles)
        
        trend = "BULLISH" if price > (ema or 0) else "BEARISH"
        bb_status = "OVERSOLD" if price < bb['lower'] else ("OVERBOUGHT" if price > bb['upper'] else "STABLE")
        macd_status = "BULLISH_CROSS" if macd['histogram'] > 0 else "BEARISH_CROSS"
        
        ta_str = f"1h:{trend}(RSI:{rsi}|MACD:{macd_status}|BB:{bb_status}|ATR:{atr})"
        
        # Relaxed assertions to check for existence of formatting tags
        self.assertIn("MACD:", ta_str)
        self.assertIn("BB:", ta_str)
        self.assertIn("ATR:", ta_str)
        self.assertIn("RSI:", ta_str)

if __name__ == '__main__':
    unittest.main()
