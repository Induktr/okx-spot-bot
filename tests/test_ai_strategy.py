
import unittest
from src.features.sentiment_analyzer.ai_client import AIAgent
from src.app.config import config

class TestAIStrategy(unittest.TestCase):
    def setUp(self):
        self.agent = AIAgent()

    def test_small_balance_budget_floor(self):
        """Verify that AI suggests at least 30 USDT for small balances."""
        # Simulated context for a $100 balance
        headlines = "BTC looking bullish on news."
        balance = 100.0
        snapshot = "- [OKX] BTC/USDT:USDT: Price 42000 | RSI: 35 | Trend: BULLISH | Status: No Position"
        market_mood = "Positive"
        
        # We check the prompt construction to see if instructions are integrated
        prompt = self.agent._build_prompt(headlines, balance, snapshot, market_mood)
        self.assertIn("ACCOUNT BALANCE", prompt)
        self.assertIn("100.0 USDT", prompt)
        
        # Note: Testing the actual AI response requires a real API call.
        # Here we verify the system instruction contains the logic.
        self.assertIn("Profitability Floor", self.agent.system_instruction)
        self.assertIn("minimum of 30 USDT", self.agent.system_instruction)

    def test_strategic_concentration_instruction(self):
        """Verify asset concentration rules for small accounts."""
        self.assertIn("Strategic Concentration", self.agent.system_instruction)
        self.assertIn("Sentiment >= 8", self.agent.system_instruction)

if __name__ == "__main__":
    unittest.main()
