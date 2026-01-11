import unittest
from unittest.mock import MagicMock, patch
import datetime
import sys
import os

# Add project root to path for imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

class TestWeekendLock(unittest.TestCase):

    def test_is_weekend_logic(self):
        """Tests that is_weekend correctly identifies Saturdays and Sundays."""
        from src.app.main import is_weekend
        
        # Test Monday
        monday = datetime.datetime(2026, 1, 12, 12, 0)
        with patch('src.app.main.datetime') as mock_datetime:
            mock_datetime.datetime.now.return_value = monday
            self.assertFalse(is_weekend())
            
        # Test Friday
        friday = datetime.datetime(2026, 1, 16, 12, 0)
        with patch('src.app.main.datetime') as mock_datetime:
            mock_datetime.datetime.now.return_value = friday
            self.assertFalse(is_weekend())
            
        # Test Saturday
        saturday = datetime.datetime(2026, 1, 17, 12, 0)
        with patch('src.app.main.datetime') as mock_datetime:
            mock_datetime.datetime.now.return_value = saturday
            self.assertTrue(is_weekend())
            
        # Test Sunday
        sunday = datetime.datetime(2026, 1, 11, 12, 0)
        with patch('src.app.main.datetime') as mock_datetime:
            mock_datetime.datetime.now.return_value = sunday
            self.assertTrue(is_weekend())

    @patch('src.app.main.is_weekend', return_value=True)
    def test_astra_cycle_skips_on_weekend(self, mock_is_weekend):
        """Tests that astra_cycle returns SUCCESS and doesn't execute trade logic on weekends."""
        from src.app.main import astra_cycle
        
        with patch('src.app.main.news_aggregator') as mock_news:
            result = astra_cycle()
            self.assertEqual(result, "SUCCESS")
            # Should not reach the "Step 0" fetch news part
            self.assertFalse(mock_news.get_recent_headlines.called)

    def test_api_weekend_status(self):
        """Tests that the dashboard API correctly reports the weekend status."""
        from src.app.dashboard.app import app
        
        with app.test_client() as client:
            # 1. Simulate Saturday
            saturday = datetime.datetime(2026, 1, 17, 10, 0)
            with patch('src.app.dashboard.app.datetime') as mock_datetime:
                # We need to ensure datetime.datetime.now() returns our fake date
                # But app.py might use datetime.datetime.now() directly
                mock_datetime.datetime.now.return_value = saturday
                
                response = client.get('/api/bot_status')
                data = response.get_json()
                # If the patch for the API was applied correctly, this should work
                self.assertIn('is_weekend', data)
                self.assertTrue(data['is_weekend'])

if __name__ == '__main__':
    unittest.main()
