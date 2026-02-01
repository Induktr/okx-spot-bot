import unittest
import sys
import os
import json
from unittest.mock import patch, MagicMock

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.app.config import config
from src.app.dashboard.app import app
from src.app.main import astra_cycle

class TestSystemControl(unittest.TestCase):
    def setUp(self):
        self.app = app.test_client()
        self.app.testing = True
        # Ensure we start from a known state
        config.BOT_ACTIVE = True
        config.FORCE_CYCLE = False

    def test_01_toggle_to_paused(self):
        """Test transitioning from ONLINE to PAUSED."""
        response = self.app.post('/api/toggle_bot')
        data = json.loads(response.data)
        
        self.assertEqual(response.status_code, 200)
        self.assertFalse(data['active'])
        self.assertFalse(config.BOT_ACTIVE)
        self.assertEqual(data['message'], "Bot PAUSED")

    def test_02_toggle_to_resumed(self):
        """Test transitioning from PAUSED to ONLINE."""
        # Force state to PAUSED first
        config.BOT_ACTIVE = False
        
        response = self.app.post('/api/toggle_bot')
        data = json.loads(response.data)
        
        self.assertEqual(response.status_code, 200)
        self.assertTrue(data['active'])
        self.assertTrue(config.BOT_ACTIVE)
        self.assertTrue(config.FORCE_CYCLE) # Should trigger immediate wake-up signal
        self.assertEqual(data['message'], "Bot RESUMED")

    @patch('src.app.main.news_aggregator')
    def test_03_cycle_skipped_when_paused(self, mock_news):
        """Test that astra_cycle returns immediately if BOT_ACTIVE is False."""
        config.BOT_ACTIVE = False
        
        # If it doesn't return immediately, it would call news_aggregator
        astra_cycle()
        
        # Verify no network/analysis calls were made
        mock_news.get_recent_headlines.assert_not_called()
        
    def test_04_persistence(self):
        """Test that the state is actually saved during toggle."""
        # Start state
        initial_state = config.BOT_ACTIVE
        
        # Toggle
        self.app.post('/api/toggle_bot')
        new_state = config.BOT_ACTIVE
        
        self.assertNotEqual(initial_state, new_state)
        
    @patch('src.app.main.ai_client.analyze_news')
    @patch('src.app.main.news_aggregator.get_recent_headlines')
    def test_05_mid_cycle_interruption(self, mock_news, mock_ai):
        """Test that astra_cycle stops immediately if BOT_ACTIVE is flipped midway."""
        config.BOT_ACTIVE = True
        
        # We simulate that during news gathering (Step 1), the user hits PAUSE
        def side_effect(*args, **kwargs):
            config.BOT_ACTIVE = False
            return "Some News Headline"
        
        mock_news.side_effect = side_effect
        
        # Run the cycle
        astra_cycle()
        
        # Verify step 1 was called
        mock_news.assert_called()
        # Verify step 2 (AI) was NEVER called because of the checkpoint
        mock_ai.assert_not_called()

if __name__ == '__main__':
    unittest.main()
