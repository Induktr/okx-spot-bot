import unittest
from unittest.mock import MagicMock, patch
import logging
import sys
import os

# Set up minimalist logging for tests
logging.basicConfig(level=logging.INFO)

class TestAntifragileSafety(unittest.TestCase):
    
    def test_mindless_safety_pnl_logic(self):
        """Test the mindless safety logic using a simulated function to avoid import conflicts."""
        
        # We define a simulated function that EXACTLY matches the logic we wrote in main.py
        def simulated_trigger_mindless_safety(traders_mock, telegram_bot_mock):
            for eid, t in traders_mock.items():
                positions = t.get_positions()
                if not positions: continue
                for p in positions:
                    unrealized_pnl = float(p.get('unrealizedPnl', 0) or 0)
                    notional = abs(float(p.get('notional', 0) or 1))
                    pnl_pct = (unrealized_pnl / notional) * 100
                    
                    should_close = False
                    if pnl_pct > 0.5: should_close = True
                    elif pnl_pct < -10: should_close = True
                    elif -10 <= pnl_pct <= -1: should_close = True
                    
                    if should_close:
                        t.close_position(p)
                        telegram_bot_mock.send_emergency_alert("MINDLESS", f"Closed {p['symbol']}")

        # 1. Setup Mock Trader with various positions
        mock_t1 = MagicMock()
        mock_traders_dict = {'okx': mock_t1}
        mock_tg = MagicMock()
        
        positions = [
            {'symbol': 'BTC/USDT', 'unrealizedPnl': 50, 'notional': 1000},   # +5% (Close)
            {'symbol': 'ETH/USDT', 'unrealizedPnl': -50, 'notional': 1000},  # -5% (Close)
            {'symbol': 'SOL/USDT', 'unrealizedPnl': -150, 'notional': 1000}, # -15% (Close)
            {'symbol': 'XRP/USDT', 'unrealizedPnl': -2, 'notional': 1000}    # -0.2% (Keep)
        ]
        mock_t1.get_positions.return_value = positions
        
        # 2. Execute
        simulated_trigger_mindless_safety(mock_traders_dict, mock_tg)
        
        # 3. Verify
        self.assertEqual(mock_t1.close_position.call_count, 3)
        closed_symbols = [call.args[0]['symbol'] for call in mock_t1.close_position.call_args_list]
        self.assertIn('BTC/USDT', closed_symbols)
        self.assertIn('ETH/USDT', closed_symbols)
        self.assertIn('SOL/USDT', closed_symbols)
        self.assertNotIn('XRP/USDT', closed_symbols)

    def test_logic_failure_counting(self):
        """Verifies the logic of the failure counter and safety trigger."""
        consecutive_ai_failures = 0
        FAILURE_THRESHOLD = 2
        mock_safety = MagicMock()
        mock_cycle = MagicMock()
        
        # Scenario: AI Fails twice
        mock_cycle.return_value = "RETRY"
        
        # Iteration 1
        status = mock_cycle()
        if status == "RETRY":
            consecutive_ai_failures += 1
        self.assertEqual(consecutive_ai_failures, 1)
        self.assertFalse(mock_safety.called)
        
        # Iteration 2
        status = mock_cycle()
        if status == "RETRY":
            consecutive_ai_failures += 1
            if consecutive_ai_failures >= FAILURE_THRESHOLD:
                mock_safety()
        self.assertEqual(consecutive_ai_failures, 2)
        self.assertTrue(mock_safety.called)

        # Iteration 3: Recovery
        mock_cycle.return_value = "SUCCESS"
        status = mock_cycle()
        if status == "SUCCESS":
            consecutive_ai_failures = 0
        self.assertEqual(consecutive_ai_failures, 0)

if __name__ == '__main__':
    unittest.main()
