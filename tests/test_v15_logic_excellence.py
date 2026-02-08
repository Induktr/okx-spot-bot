import unittest
import asyncio
from unittest.mock import MagicMock, patch, AsyncMock
import logging

# Module imports
from src.features.trade_executor.trader import Trader
from src.shared.providers.telegram_provider import TelegramProvider
from src.shared.utils.analysis import TechnicalAnalysis
from src.app.config import config

class TestV15LogicExcellence(unittest.IsolatedAsyncioTestCase):
    """
    Antifragility Test Suite for A.S.T.R.A. v1.5.1
    Testing Stage 20 (Brokerage) and Stage 21 (High Availability).
    """

    async def asyncSetUp(self):
        # Mocking config for consistent test behavior
        config.OKX_BROKER_ID = "TEST_TAG_123"
        config.TRAILING_STOP_ACTIVE = True
        config.TRAILING_STOP_CALLBACK_PCT = 0.02
        config.TRAILING_STOP_DISTANCE_PCT = 0.01
        
        # Initialize Trader with mocked exchange
        self.trader = Trader(exchange_id='okx')
        self.trader.exchange = AsyncMock()
        self.trader.exchange.price_to_precision = lambda s, p: str(round(p, 2))
        self.trader.exchange.amount_to_precision = lambda s, a: str(round(a, 4))
        self.trader.exchange.market = MagicMock(return_value={'contractSize': 1.0})
        self.trader.get_ticker = AsyncMock(return_value=50000.0)
        self.trader.set_leverage = AsyncMock()
        self.trader.pos_mode = 'long_short_mode'

    async def test_broker_id_persistence(self):
        """Verify that Broker ID (tag) is passed to execution orders."""
        symbol = "BTC/USDT:USDT"
        budget = 100
        
        # Test Market Order
        await self.trader.execute_order(symbol, "BUY", budget)
        
        # Check if create_market_buy_order was called with tag
        call_args = self.trader.exchange.create_market_buy_order.call_args
        params = call_args[1]['params']
        self.assertEqual(params.get('tag'), "TEST_TAG_123", "Broker Tag missing in Market Order")

    async def test_trailing_stop_breakeven_activation(self):
        """Verify that SL moves to profit/breakeven when price moves up."""
        mock_pos = {
            'symbol': 'ETH/USDT:USDT',
            'side': 'long',
            'entryPrice': 2000.0,
            'contracts': 10,
            'id': 'pos_123'
        }
        
        # Set price to +3% profit (triggers trailing at 2%)
        # Distance is 1% from peak, so target price should be last_price * 0.99
        last_price = 2060.0 # Entry 2000 + 3%
        self.trader.get_ticker = AsyncMock(return_value=last_price)
        
        # Mock cancel and create order
        self.trader.exchange.cancel_all_orders = AsyncMock()
        self.trader.exchange.create_order = AsyncMock()
        
        res = await self.trader.sync_sl_tp(mock_pos, sl_pct=0.1) # Initial SL at 1800
        
        self.assertEqual(res, "SYNCED_TRAILING")
        
        # Check if new SL price is correct (2060 * 0.99 = 2039.4)
        # It must be > entryPrice (2000)
        expected_sl = 2039.4
        
        # Verify create_order calls: 1 for TP, 1 for SL
        self.assertEqual(self.trader.exchange.create_order.call_count, 2)
        
        # Check the SL price in the last call
        sl_call = self.trader.exchange.create_order.call_args_list[1]
        sl_params = sl_call.kwargs['params']
        sl_trigger = float(sl_params['slTriggerPx'])
        
        self.assertGreaterEqual(sl_trigger, 2000.0, "Trailing Stop must be at least at Breakeven")
        self.assertAlmostEqual(sl_trigger, expected_sl, delta=1.0)

    async def test_telegram_retry_resilience(self):
        """Verify that Telegram provider handles network timeouts with retries."""
        tp = TelegramProvider()
        tp.bot = MagicMock()
        tp.chat_id = "12345"
        
        # Simulate 2 timeouts follow by success
        tp.bot.send_message.side_effect = [
            Exception("Timeout"),
            Exception("Connection Error"),
            MagicMock(message_id=999)
        ]
        
        with patch('asyncio.sleep', return_value=None): # Don't actually wait
            res = tp.send_message("Test message", retries=3)
            
        self.assertIsNotNone(res, "Telegram should eventually succeed after retries")
        self.assertEqual(tp.bot.send_message.call_count, 3, "Should have attempted 3 times")

    def test_math_hardening_extreme_inputs(self):
        """Stress test Technical Analysis with malicious or invalid data."""
        ta = TechnicalAnalysis()
        
        # 1. Empty list
        self.assertEqual(ta.calculate_rsi([]), 50.0)
        self.assertEqual(ta.calculate_ema([]), 0.0)
        
        # 2. List with one value
        self.assertEqual(ta.calculate_rsi([100]), 50.0)
        self.assertEqual(ta.calculate_ema([100]), 100.0)
        
        # 3. List with identical values (0 volatility)
        identical = [100.0] * 20
        self.assertEqual(ta.calculate_rsi(identical), 50.0)
        
        # 4. ATR with garbage candles
        garbage_candles = [[0, "n/a", None, 100, 100, 1]] # Should not crash
        try:
            atr = ta.calculate_atr(garbage_candles)
            self.assertIsInstance(atr, float)
        except Exception as e:
            self.fail(f"TechnicalAnalysis.calculate_atr crashed on garbage input: {e}")

if __name__ == "__main__":
    unittest.main()
