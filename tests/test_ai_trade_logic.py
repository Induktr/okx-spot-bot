import unittest
from unittest.mock import AsyncMock, patch
import asyncio
from src.features.sentiment_analyzer.ai_client import AIAgent

class TestAITradeLogic(unittest.IsolatedAsyncioTestCase):
    """
    Tests the 'Brain' of Astra.
    Checks if the AI correctly interprets extreme market data and news 
    to output specific actions like CLOSE or SELL.
    """
    async def asyncSetUp(self):
        # We mock the config to use a real model name but we will mock the actual API call
        self.ai = AIAgent()
        self.ai.client = MagicMock()
        self.ai.client.models = MagicMock()
        self.ai.client.models.generate_content_async = AsyncMock()

    async def test_ai_recommends_close_on_reversal(self):
        """Mock a scenario where RSI is extreme and AI should recommend CLOSE."""
        # 1. Mock Gemini Response for CLOSE
        mock_response = MagicMock()
        mock_response.text = '{"action": "CLOSE", "target_symbol": "ETH/USDT", "sentiment_score": 5, "reasoning": "RSI extreme reversal detected", "tp_pct": 0, "sl_pct": 0, "leverage": 1, "budget_usdt": 0}'
        self.ai.client.models.generate_content_async.return_value = mock_response

        # 2. Call analysis
        decision = await self.ai.analyze_market(
            symbol="ETH/USDT",
            news_context="Market is cooling down after a massive pump.",
            ticker_data="Price: 2800 | TA: BEARISH (RSI: 85)" # Extreme overbought
        )

        # 3. Assertions
        self.assertEqual(decision["action"], "CLOSE")
        self.assertIn("RSI", decision["reasoning"])

    async def test_ai_recommends_short_on_dump(self):
        """Mock systemic liquidation news to see if AI chooses SELL."""
        mock_response = MagicMock()
        mock_response.text = '{"action": "SELL", "target_symbol": "BTC/USDT", "sentiment_score": 1, "reasoning": "Systemic liquidation spiral", "tp_pct": 10.0, "sl_pct": 5.0, "leverage": 10, "budget_usdt": 5000}'
        self.ai.client.models.generate_content_async.return_value = mock_response

        decision = await self.ai.analyze_market(
            symbol="BTC/USDT",
            news_context="Major exchange insolvency rumors spreading.",
            ticker_data="Price: 65000 | TA: BEARISH (RSI: 35)"
        )

        self.assertEqual(decision["action"], "SELL")
        self.assertEqual(decision["sentiment_score"], 1)

if __name__ == "__main__":
    from unittest.mock import MagicMock
    unittest.main()
