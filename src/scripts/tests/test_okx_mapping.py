
import unittest
from unittest.mock import MagicMock
from src.features.trade_executor.trader import Trader

class TestTraderPnLMapping(unittest.TestCase):
    def setUp(self):
        # Initialize trader with dummy keys
        self.trader = Trader(exchange_id='okx')
        # Mock the exchange
        self.trader.exchange = MagicMock()

    def test_okx_pnl_mapping(self):
        """Verify that OKX fillPnl is correctly mapped to pnl field for analytics."""
        # Mock response from fetch_my_trades
        mock_trades = [
            {
                'id': '12345',
                'symbol': 'BTC/USDT:USDT',
                'pnl': None, # PnL is missing in top level
                'info': {
                    'fillPnl': '15.50' # But exists in raw info
                }
            },
            {
                'id': '67890',
                'symbol': 'ETH/USDT:USDT',
                'pnl': 0.0,
                'info': {
                    'fillPnl': '-5.20'
                }
            }
        ]
        self.trader.exchange.fetch_my_trades.return_value = mock_trades
        
        trades = self.trader.get_history()
        
        # Check mapping
        self.assertEqual(trades[0]['pnl'], 15.50)
        self.assertEqual(trades[1]['pnl'], -5.20)
        self.assertEqual(trades[0]['id'], '12345')

if __name__ == "__main__":
    unittest.main()
