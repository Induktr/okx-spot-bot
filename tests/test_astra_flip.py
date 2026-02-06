import unittest
from unittest.mock import MagicMock, AsyncMock
import asyncio
from src.features.trade_executor.trader import Trader

class TestAstraFlip(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        # Patch _get_keys to avoid trying to read real credentials
        Trader._get_keys = MagicMock(return_value={'apiKey': 'test', 'secret': 'test', 'password': 'test'})
        self.trader = Trader(exchange_id='okx')
        self.mock_exchange = MagicMock()
        self.trader.exchange = self.mock_exchange

    async def test_atomic_flip_logic_short_to_long(self):
        """Verify that Trader can flip from SHORT to LONG (Atomic Flip)."""
        # 1. Setup existing SHORT position
        existing_pos = {'symbol': 'BTC/USDT:USDT', 'contracts': 1.0, 'side': 'short'}
        
        # 2. Mock execution methods
        self.trader.close_position = AsyncMock(return_value="CLOSED")
        self.trader.execute_order = AsyncMock(return_value="SUCCESS: Order filled")
        
        # 3. Trigger Flip
        # Calling flip: symbol, current_pos, target_decision (BUY), budget, leverage
        res = await self.trader.execute_flip("BTC/USDT", existing_pos, "BUY", 1000, 10)
        
        # 4. Assertions
        self.trader.close_position.assert_called_once_with(existing_pos)
        self.trader.execute_order.assert_called_once_with("BTC/USDT", "BUY", 1000, 10)
        self.assertEqual(res, "SUCCESS: Order filled")

    async def test_atomic_flip_logic_long_to_short(self):
        """Verify that Trader can flip from LONG to SHORT."""
        existing_pos = {'symbol': 'ETH/USDT:USDT', 'contracts': 2.5, 'side': 'long'}
        
        self.trader.close_position = AsyncMock(return_value="CLOSED")
        self.trader.execute_order = AsyncMock(return_value="SUCCESS: Order filled")
        
        res = await self.trader.execute_flip("ETH/USDT", existing_pos, "SELL", 500, 5)
        
        self.trader.close_position.assert_called_once_with(existing_pos)
        self.trader.execute_order.assert_called_once_with("ETH/USDT", "SELL", 500, 5)
        self.assertEqual(res, "SUCCESS: Order filled")

    async def test_flip_abort_if_close_fails(self):
        """Verify that Flip is aborted if the initial position cannot be closed."""
        existing_pos = {'symbol': 'BTC/USDT:USDT', 'contracts': 1.0, 'side': 'short'}
        
        # Mock close failure
        self.trader.close_position = AsyncMock(return_value="FAILED: Connection Error")
        self.trader.execute_order = AsyncMock() # Should NOT be called
        
        res = await self.trader.execute_flip("BTC/USDT", existing_pos, "BUY", 1000, 10)
        
        self.assertIn("FLIP ABORTED", res)
        self.trader.execute_order.assert_not_called()

if __name__ == "__main__":
    unittest.main()
