
import unittest
import time
from src.features.sentiment_analyzer.ai_client import AIAgent

class TestAISystemStress(unittest.TestCase):
    def setUp(self):
        self.agent = AIAgent()

    def test_massive_news_payload(self):
        """Stress test the AI Client with a very large amount of news data (Limit Testing)."""
        # Generate 50,000 characters of news (simulating a very busy day)
        fake_news = "BREAKING: Market volatility increases. " * 1000 
        balance = 500.0
        snapshot = "- [OKX] BTC/USDT:Price 42000 | RSI 30\n" * 50 # 50 coins in snapshot
        market_mood = "Extreme Fear"

        print(f"Testing AI Prompt generation with {len(fake_news)} chars of news...")
        start = time.perf_counter()
        prompt = self.agent._build_prompt(fake_news, balance, snapshot, market_mood)
        duration = (time.perf_counter() - start) * 1000
        
        print(f"Prompt Building Latency: {duration:.2f}ms")
        
        # Verify prompt isn't broken
        self.assertIn("ACCOUNT BALANCE", prompt)
        self.assertIn("Extreme Fear", prompt)
        self.assertGreater(len(prompt), 50000)
        
        # Checking if it exceeds typical LLM token limits (roughly 4 chars per token)
        # 50k chars is roughly 12.5k tokens. Gemini handle 1M+, so this should be fine.
        print(f"Total Prompt Size: {len(prompt)} characters.")

    def test_model_rotation_on_failure(self):
        """Verify that the agent rotates models if one fails (Simulation)."""
        # We manually trigger rotation
        initial_model = self.agent.model_id
        self.agent._rotate_model()
        new_model = self.agent.model_id
        
        self.assertNotEqual(initial_model, new_model)
        print(f"Model Rotation Success: {initial_model} -> {new_model}")

if __name__ == "__main__":
    unittest.main()
