import unittest
from unittest.mock import patch, MagicMock
import time
import sys
import os

# Ensure src is in path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.app.config import Config

class TestSubscriptionSystem(unittest.TestCase):
    
    def setUp(self):
        """Set up a fresh Config instance for each test, mocking file operations."""
        # We patch 'open' during init to prevent reading the real settings.json
        with patch('builtins.open', unittest.mock.mock_open(read_data='{}')):
            self.config = Config()
            
        # Reset to default LITE state
        self.config.SUBSCRIPTION_STATUS = "LITE"
        self.config.SUBSCRIPTION_EXPIRY = 0.0

    @patch('src.app.config.Config.save_settings')
    def test_manual_activation(self, mock_save):
        """Test Simulating a Payment Activation."""
        print("\nTesting Subscription Activation...")
        
        # Simulate 30-day activation
        self.config.SUBSCRIPTION_STATUS = "PREMIUM"
        self.config.SUBSCRIPTION_EXPIRY = time.time() + (30 * 24 * 3600)
        
        # Assertions
        self.assertEqual(self.config.SUBSCRIPTION_STATUS, "PREMIUM")
        # Expiry should be approx 30 days from now
        self.assertTrue(self.config.SUBSCRIPTION_EXPIRY > time.time() + (29 * 24 * 3600))
        print("[PASS] Premium Status Set Correctly")

    @patch('src.app.config.time.time')
    @patch('src.app.config.Config.save_settings')
    def test_expiration_downgrade(self, mock_save, mock_time):
        """Test that an expired subscription automatically reverts to LITE."""
        print("\nTesting Expiration Downgrade...")
        
        # Mock current time
        NOW = 100000.0
        mock_time.return_value = NOW
        
        # Setup: Expired Premium (expired 1 second ago)
        self.config.SUBSCRIPTION_STATUS = "PREMIUM"
        self.config.SUBSCRIPTION_EXPIRY = NOW - 1.0 
        
        # Check Expiry
        self.config.check_subscription_expiry()
        
        # Assertions
        self.assertEqual(self.config.SUBSCRIPTION_STATUS, "LITE", "Status should follow downgrade to LITE")
        self.assertEqual(self.config.SUBSCRIPTION_EXPIRY, 0.0, "Expiry should reset to 0.0")
        mock_save.assert_called_once() # Should save the new LITE status
        print("[PASS] Expired Subscription Downgraded Successfully")

    @patch('src.app.config.time.time')
    @patch('src.app.config.Config.save_settings')
    def test_active_subscription_remained(self, mock_save, mock_time):
        """Test that a valid subscription remains PREMIUM."""
        print("\nTesting Valid Subscription Persistence...")
        
        # Mock current time
        NOW = 100000.0
        mock_time.return_value = NOW
        
        # Setup: Active Premium (expires in 10 minutes)
        self.config.SUBSCRIPTION_STATUS = "PREMIUM"
        self.config.SUBSCRIPTION_EXPIRY = NOW + 600.0 
        
        # Check Expiry
        self.config.check_subscription_expiry()
        
        # Assertions
        self.assertEqual(self.config.SUBSCRIPTION_STATUS, "PREMIUM", "Status should remain PREMIUM")
        mock_save.assert_not_called() # Should NOT save (no change)
        print("[PASS] Valid Subscription Remained Active")

if __name__ == '__main__':
    unittest.main()
