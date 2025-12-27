from google import genai
from google.genai import types
import json
import logging
from core.config import config
from core.token_guard import token_guard

class AIAgent:
    """
    Brain module for A.S.T.R.A.
    Integrates with Google Gemini via the new google-genai SDK.
    """
    def __init__(self):
        self.client = genai.Client(api_key=config.GEMINI_API_KEY)
        self.model_id = config.GEMINI_MODEL
        self.system_instruction = (
            "Role: You are ASTRA, an advanced autonomous crypto portfolio manager.\n"
            "Current Task: Analyze news and market data for a list of coins. Pick the BEST candidate to act upon (or manage existing positions).\n"
            "Mandates:\n"
            "1. Selection: Review the 'MARKET SNAPSHOT'. Pick ONE coin that has the strongest setup or requires urgent risk adjustment (CLOSE/ADJUST).\n"
            "2. Profit/Risk: Aim for 30-35% profit and 20% stop loss. Adjust based on trend strength.\n"
            "3. Money Management: Base 'budget_usdt' on confidence (Sentiment 9-10 -> 25% balance, 6-8 -> 10%). Max 30% per coin.\n"
            "4. Leverage: Suggested 1-10x.\n"
            "5. Flipping Positions: If current position is LONG but news suggest a strong reversal, you can return action 'SELL' to flip to SHORT (and vice-versa). The system will handle the transition.\n"
            "Output Format: JSON only: {\"target_symbol\": \"BTC/USDT:USDT\", \"sentiment_score\": 1-10, \"action\": \"BUY/SELL/WAIT/CLOSE/ADJUST\", \"tp_pct\": 0.35, \"sl_pct\": 0.1, \"leverage\": 5, \"budget_usdt\": 15.0, \"reasoning\": \"...\"}.\n"

            "If no action is needed for any coin, return \"target_symbol\": \"NONE\" and \"action\": \"WAIT\".\n"



        )

    def analyze_news(self, headlines: str, balance: float, snapshot: str, market_mood: str = "Unknown") -> dict:
        """
        Sends headlines, balance, market snapshot, and mood to Gemini.
        """
        token_guard.wait_if_needed()
        
        logging.info(f"AI: Selecting best candidate from snapshot. Balance: {balance} USDT")
        
        prompt = (
            f"--- ACCOUNT BALANCE ---\n{balance} USDT\n\n"
            f"--- GLOBAL MARKET MOOD ---\n{market_mood}\n\n"
            f"--- MARKET SNAPSHOT (Prices & Positions) ---\n{snapshot}\n\n"
            f"--- LATEST NEWS ---\n{headlines}\n\n"
            "Review the snapshot and news. Which coin from the list is the best candidate to BUY, SELL, or requires management (CLOSE/ADJUST)? "
            "Return the 'target_symbol' and the determined action. If nothing is worth trading, return target_symbol: NONE."
        )



        
        try:
            response = self.client.models.generate_content(
                model=self.model_id,
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=self.system_instruction,
                    response_mime_type='application/json'
                )
            )
            
            result = json.loads(response.text)
            
            # Extract usage metadata
            usage = response.usage_metadata
            usage_info = {
                "prompt_tokens": usage.prompt_token_count,
                "candidates_tokens": usage.candidates_token_count,
                "total_tokens": usage.total_token_count
            }
            
            # If the AI returns a list, take the first element
            if isinstance(result, list) and len(result) > 0:
                result = result[0]
            
            if not isinstance(result, dict):
                raise ValueError("AI response is not a valid JSON object")
            
            # Attach usage info to the result
            result['usage'] = usage_info
            
            score = result.get('sentiment_score', 0)
            decision = result.get('action', 'WAIT')
            reason = result.get('reasoning', 'No reason provided.')
            
            logging.info(f"AI Result: [Score: {score}/10] [Action: {decision}]")
            logging.info(f"AI Usage: {usage_info}")
            logging.info(f"AI Reasoning: {reason}")
            
            return result


        except Exception as e:
            error_msg = f"AI Analysis failed: {str(e)}"
            logging.error(error_msg)
            return {
                "sentiment_score": 5,
                "action": "WAIT",
                "reasoning": error_msg
            }



# Initialize AI client
ai_client = AIAgent()

