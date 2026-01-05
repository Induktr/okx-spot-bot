
import unittest
from unittest.mock import MagicMock
from src.features.trade_executor.trader import Trader
from src.app.config import config

class TestAdaptiveRisk(unittest.TestCase):
    def setUp(self):
        self.trader = Trader(exchange_id='okx')
        self.trader.exchange = MagicMock()
        config.VOLATILITY_THRESHOLD = 0.05 # 5%
        config.MAX_LEVERAGE = 20
        config.MIN_LEVERAGE = 1

    def test_leverage_reduction_on_volatility(self):
        """Test that leverage is cut in half if volatility exceeds threshold."""
        # Mock OHLCV: 10% price move (from 100 to 110)
        self.trader.exchange.fetch_ohlcv.return_value = [
            [0, 0, 0, 0, 100.0, 0], # Close 100
            [0, 0, 0, 0, 110.0, 0]  # Close 110
        ]
        
        base_leverage = 10
        # Expected: 10% > 5% threshold -> leverage becomes 10 * 0.5 = 5
        adjusted = self.trader.calculate_adaptive_leverage("BTC/USDT:USDT", base_leverage)
        self.assertEqual(adjusted, 5)

    def test_leverage_baseline_stable_market(self):
        """Test that leverage remains same if market is stable."""
        # 1% move
        self.trader.exchange.fetch_ohlcv.return_value = [
            [0, 0, 0, 0, 100.0, 0],
            [0, 0, 0, 0, 101.0, 0]
        ]
        
        base_leverage = 10
        adjusted = self.trader.calculate_adaptive_leverage("BTC/USDT:USDT", base_leverage)
        self.assertEqual(adjusted, 10)

    def test_symbol_deep_normalization(self):
        """Test the logic that finds 'BTC/USDT:USDT' when AI returns just 'BTC'."""
        self.trader.exchange.markets = {
            "BTC/USDT:USDT": {"id": "BTC-USDT-SWAP", "symbol": "BTC/USDT:USDT"},
            "ETH/USDT:USDT": {"id": "ETH-USDT-SWAP", "symbol": "ETH/USDT:USDT"}
        }
        
        # We need to mock fetch_ticker used inside execute_order
        self.trader.get_ticker = MagicMock(return_value=40000)
        self.trader.get_free_balance = MagicMock(return_value=1000)
        self.trader.exchange.market = MagicMock(return_value={
            'contractSize': 1, 
            'limits': {'amount': {'min': 0.01}},
            'precision': {'amount': 2}
        })
        
        # Call execute_order with deep normalization target
        # Logic should find BTC/USDT:USDT
        with patch.object(self.trader.exchange, 'create_market_buy_order') as mock_order:
            self.trader.execute_order("BTC", "BUY", 100, leverage=3)
            # Verify the first argument to create_market_buy_order was the normalized symbol
            args, kwargs = mock_order.call_args
            self.assertEqual(args[0], "BTC/USDT:USDT")

if __name__ == "__main__":
    from unittest.mock import patch
    unittest.main()
