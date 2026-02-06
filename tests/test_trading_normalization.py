import unittest
from unittest.mock import MagicMock, AsyncMock
import asyncio
from src.features.trade_executor.trader import Trader

class TestTradingNormalization(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        # Patch _get_keys to avoid trying to read real credentials
        Trader._get_keys = MagicMock(return_value={'apiKey': 'test', 'secret': 'test', 'password': 'test'})
        # Initialize Trader normally
        self.trader = Trader(exchange_id='okx')
        # Mock the internal exchange object
        self.mock_exchange = MagicMock()
        self.trader.exchange = self.mock_exchange

    async def test_symbol_normalization(self):
        """Test if standard symbols are converted to OKX SWAP format correctly."""
        self.mock_exchange.fetch_positions = AsyncMock(return_value=[
            {'symbol': 'BTC/USDT:USDT', 'contracts': 1.0, 'side': 'short'}
        ])

        # Try to get positions for raw symbol
        pos_raw = await self.trader.get_positions(target_symbol="BTC/USDT")
        pos_colon = await self.trader.get_positions(target_symbol="BTC/USDT:USDT")

        self.assertEqual(len(pos_raw), 1, "Should find position even with raw symbol BTC/USDT")
        self.assertEqual(pos_raw[0]['symbol'], 'BTC/USDT:USDT')
        self.assertEqual(len(pos_colon), 1, "Should find position with full symbol")

    async def test_execute_order_normalization(self):
        """Verify that execute_order also normalizes the symbol before calling exchange."""
        self.mock_exchange.market = MagicMock(return_value={'contractSize': 1.0})
        self.trader.get_ticker = AsyncMock(return_value=50000.0)
        self.trader.set_leverage = AsyncMock()
        self.mock_exchange.amount_to_precision = MagicMock(return_value="0.1")
        self.mock_exchange.create_market_sell_order = AsyncMock()

        await self.trader.execute_order("ETH/USDT", "SELL", 100)

        # Check if create_market_sell_order was called with normalized symbol
        args, _ = self.mock_exchange.create_market_sell_order.call_args
        self.assertEqual(args[0], "ETH/USDT:USDT", "Symbol should be normalized to :USDT for OKX")

if __name__ == "__main__":
    unittest.main()
