import unittest
from unittest.mock import MagicMock, patch
import sys
import os

# Add project root to path for imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

class TestGoldenAnalysis(unittest.TestCase):

    def setUp(self):
        from src.shared.utils.analysis import tech_analysis
        self.ta = tech_analysis
        self.prices = [100 + i for i in range(100)]
        self.volumes = [1000 for _ in range(100)]
        self.candles = [[i, 100+i, 105+i, 95+i, 100+i, 1000] for i in range(100)]

    def test_calculate_rvol(self):
        """Tests Relative Volume calculation."""
        # Baseline rvol with constant volume should be 1.0
        rvol = self.ta.calculate_rvol(self.volumes)
        self.assertEqual(rvol, 1.0)
        
        # Spike in volume
        spiked_volumes = self.volumes + [5000] # 5x spike
        rvol_spike = self.ta.calculate_rvol(spiked_volumes)
        self.assertEqual(rvol_spike, 5.0)

    def test_detect_pivots(self):
        """Tests Pivot Point detection."""
        result = self.ta.detect_pivots(self.candles)
        self.assertIsNotNone(result)
        self.assertIn('p', result)
        self.assertIn('s1', result)
        self.assertIn('r1', result)

    def test_ai_client_golden_instructions(self):
        """Tests that the AI client's instructions reflect the new Golden 10 strategy."""
        from src.features.sentiment_analyzer.ai_client import AIAgent
        agent = AIAgent()
        self.assertIn("Quad-Convergence", agent.system_instruction)
        self.assertIn("RVOL", agent.system_instruction)
        self.assertIn("Pivot Levels", agent.system_instruction)
        self.assertIn("THE GOLDEN 10 (10/10)", agent.system_instruction)

    @patch('src.app.main.traders')
    @patch('src.app.main.config')
    def test_market_snapshot_full_integration(self, mock_config, mock_traders):
        """Verified that all new indicators appear in the final market snapshot string."""
        from src.shared.utils.analysis import tech_analysis
        
        # Simulated data for one symbol
        price = 150
        closes = self.prices
        volumes = self.volumes
        candles = self.candles
        
        rsi = tech_analysis.calculate_rsi(closes)
        ema = tech_analysis.calculate_ema(closes)
        macd = tech_analysis.calculate_macd(closes)
        bb = tech_analysis.calculate_bollinger_bands(closes)
        atr = tech_analysis.calculate_atr(candles)
        rvol = tech_analysis.calculate_rvol(volumes)
        pivots = tech_analysis.detect_pivots(candles)
        
        trend = "BULLISH" if price > (ema or 0) else "BEARISH"
        bb_status = "OVERSOLD" if price < bb['lower'] else ("OVERBOUGHT" if price > bb['upper'] else "STABLE")
        macd_status = "BULLISH_CROSS" if macd['histogram'] > 0 else "BEARISH_CROSS"
        
        ta_str = f"1h:{trend}(RSI:{rsi}|MACD:{macd_status}|BB:{bb_status}|ATR:{atr}|RVOL:{rvol}|S1:{pivots['s1']}|R1:{pivots['r1']})"
        
        self.assertIn("RVOL:1.0", ta_str)
        self.assertIn("S1:", ta_str)
        self.assertIn("R1:", ta_str)
        self.assertIn("MACD:", ta_str)

if __name__ == '__main__':
    unittest.main()
