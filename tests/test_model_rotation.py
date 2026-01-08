import unittest
from unittest.mock import MagicMock, patch
import json
from src.features.sentiment_analyzer.ai_client import AIAgent
from src.app.config import config

class TestModelRotationLogic(unittest.TestCase):
    def setUp(self):
        # Configure test models
        config.GEMINI_MODELS = ["primary-model", "backup-model"]
        config.GEMINI_API_KEY = "test-key"
        config.USE_CLOUD_AI = False # Test local logic
        
        # Patch the genai.Client
        self.patcher_client = patch('google.genai.Client')
        self.mock_client_class = self.patcher_client.start()
        self.mock_client = self.mock_client_class.return_value
        
        # Initialize agent
        self.agent = AIAgent()

    def tearDown(self):
        self.patcher_client.stop()

    def test_initial_state(self):
        """Verify agent starts with the first model in the pool."""
        self.assertEqual(self.agent.model_id, "primary-model")
        print("SUCCESS: Initial state: Agent correctly started with primary-model.")

    def test_rotation_on_error(self):
        """Verify agent rotates to the next model when hit with a rate limit (429)."""
        # Setup mock to fail with 429 once, then succeed
        mock_response = MagicMock()
        mock_response.text = json.dumps({"target_symbol": "BTC/USDT", "action": "WAIT", "reasoning": "Success after rotation"})
        
        # Simulation: First call fails on primary, second call (automatic retry) should happen on backup
        self.mock_client.models.generate_content.side_effect = [
            Exception("429 Rate Limit Exceeded"),
            mock_response
        ]
        
        result = self.agent.analyze_news("Test news", 100.0, "Test snapshot")
        
        self.assertEqual(self.agent.model_id, "backup-model")
        self.assertEqual(result["reasoning"], "Success after rotation")
        print("SUCCESS: Rotation: Agent successfully switched to backup-model after 429 error.")

    def test_priority_reset(self):
        """Verify agent resets to primary model at the start of a NEW cycle."""
        # 1. Manually force rotation to backup
        self.agent._rotate_model()
        self.assertEqual(self.agent.model_id, "backup-model")
        
        # 2. Mock a successful response
        mock_response = MagicMock()
        mock_response.text = json.dumps({"target_symbol": "BTC/USDT", "action": "WAIT", "reasoning": "Reset success"})
        self.mock_client.models.generate_content.return_value = mock_response
        
        # 3. Call analyze_news (simulating a new cycle)
        # This should trigger _reset_to_primary() inside analyze_news()
        self.agent.analyze_news("Test news", 100.0, "Test snapshot")
        
        self.assertEqual(self.agent.model_id, "primary-model")
        print("SUCCESS: Priority Reset: Agent correctly returned to primary-model for the new analysis cycle.")

if __name__ == "__main__":
    unittest.main()
