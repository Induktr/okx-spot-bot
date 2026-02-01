
import unittest
from unittest.mock import MagicMock, patch
from src.features.trade_executor.trader import Trader

class TestLeverageAndExecution(unittest.TestCase):
    def setUp(self):
        # Mock ccxt.okx to avoid network and properly initialize
        with patch('ccxt.okx') as mock_ccxt:
            mock_inst = mock_ccxt.return_value
            mock_inst.private_get_account_config.return_value = {"data": [{"posMode": "net_mode"}]}
            self.trader = Trader(exchange_id='okx')
            self.trader.exchange = MagicMock()

    def test_leverage_and_order_flow(self):
        """Verify that leverage is set BEFORE the order and with correct params."""
        symbol = "BTC/USDT:USDT"
        self.trader.exchange.markets = {symbol: {'symbol': symbol}}
        self.trader.exchange.market.return_value = {
            'symbol': symbol, 'contractSize': 1, 
            'limits': {'amount': {'min': 0.01}}, 'precision': {'amount': 2}
        }
        self.trader.get_ticker = MagicMock(return_value=40000)
        self.trader.get_free_balance = MagicMock(return_value=1000)
        self.trader.exchange.amount_to_precision = MagicMock(side_effect=lambda s, v: str(v))
        
        # We need to spy on set_leverage and create_market_buy_order
        with patch.object(self.trader, 'set_leverage') as mock_set_lev, \
             patch.object(self.trader.exchange, 'create_market_buy_order') as mock_buy:
            
            self.trader.execute_order(symbol, "BUY", 100, leverage=10)
            
            # 1. Check if set_leverage was called first
            mock_set_lev.assert_called_once_with(symbol, 10, side='long')
            
            # 2. Check if the order was created with 'cross' mode for OKX
            args, kwargs = mock_buy.call_args
            self.assertEqual(args[0], symbol)
            self.assertEqual(kwargs['params']['tdMode'], 'cross')
            print("Execution: Leverage set correctly before order.")

    def test_hedge_mode_pos_side(self):
        """Verify that posSide is included in order parameters when in Hedge Mode."""
        symbol = "ETH/USDT:USDT"
        # Mock account config to return Hedge Mode during sync
        self.trader.exchange.private_get_account_config.return_value = {"data": [{"posMode": "long_short_mode"}]}
        
        self.trader.exchange.markets = {symbol: {'symbol': symbol}}
        self.trader.exchange.market.return_value = {
            'symbol': symbol, 'contractSize': 1, 
            'limits': {'amount': {'min': 0.1}}, 'precision': {'amount': 1}
        }
        self.trader.get_ticker = MagicMock(return_value=2000)
        self.trader.get_free_balance = MagicMock(return_value=1000)
        self.trader.exchange.amount_to_precision = MagicMock(side_effect=lambda s, v: str(v))
        
        with patch.object(self.trader.exchange, 'create_market_sell_order') as mock_sell:
            self.trader.execute_order(symbol, "SELL", 200, leverage=5)
            
            # Check posSide param
            _, kwargs = mock_sell.call_args
            self.assertEqual(kwargs['params']['posSide'], 'short')
            self.assertEqual(kwargs['params']['tdMode'], 'cross')
            print("Execution: posSide correctly sent for Hedge Mode.")

    def test_adaptive_leverage_integration(self):
        """Verify that execution uses Adjusted Leverage if volatility is high."""
        symbol = "BTC/USDT:USDT"
        
        # 10% move triggers 50% leverage reduction
        mock_ohlcv = [[0,0,0,0,100.0,0], [0,0,0,0,110.0,0]]
        self.trader.get_ohlcv = MagicMock(return_value=mock_ohlcv)
        
        self.trader.exchange.markets = {symbol: {'symbol': symbol}}
        self.trader.exchange.market.return_value = {
            'symbol': symbol, 'contractSize': 1, 
            'limits': {'amount': {'min': 0.1}}, 'precision': {'amount': 1}
        }
        self.trader.get_ticker = MagicMock(return_value=40000)
        self.trader.get_free_balance = MagicMock(return_value=1000)
        self.trader.exchange.amount_to_precision = MagicMock(side_effect=lambda s, v: str(v))
        
        with patch('src.app.config.config.VOLATILITY_THRESHOLD', 0.05), \
             patch.object(self.trader, 'set_leverage') as mock_set_lev:
            
            print(f"DEBUG: Move is 10%, Threshold is 0.05. Calling execute_order with 10x...")
            self.trader.execute_order(symbol, "BUY", 100, leverage=10)
            
            # Verify it was scaled down
            actual_args = mock_set_lev.call_args[0]
            print(f"DEBUG: Final Leverage used: {actual_args[1]}x")
            
            mock_set_lev.assert_called_once_with(symbol, 5, side='long')
            print("Execution: Adaptive Risk correctly scaled down leverage.")

if __name__ == "__main__":
    unittest.main()
