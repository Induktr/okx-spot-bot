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
            "Current Task: Analyze news AND current open positions to manage risk for a SPECIFIC COIN.\n"
            "Mandates:\n"
            "1. Focus: Look for news mentioning the coin in 'CURRENT POSITION STATUS'. If no specific news, use global market mood and BTC trend as a proxy.\n"
            "2. Profit Target: Aim for 30% to 35% profit. You can suggest a custom 'tp_pct' if the trend is very strong.\n"
            "3. Stop Loss Protection: Default is 20% loss. You can suggest a custom 'sl_pct' based on market volatility.\n"
            "4. Leverage: You can suggest leverage from 1 to 10 (Max 10x).\n"
            "Output Format: JSON only: {\"sentiment_score\": 1-10, \"action\": \"BUY/SELL/WAIT/CLOSE/ADJUST\", \"tp_pct\": 0.35, \"sl_pct\": 0.1, \"leverage\": 5, \"reasoning\": \"...\"}.\n"

        )

    def analyze_news(self, headlines: str, position_data: str = "No open positions.", market_mood: str = "Unknown") -> dict:
        """
        Sends headlines, position data, and market mood to Gemini.
        """
        token_guard.wait_if_needed()
        
        logging.info(f"AI: Starting analysis with Market Mood: {market_mood}")
        
        prompt = (
            f"--- GLOBAL MARKET MOOD ---\n{market_mood}\n\n"
            f"--- MARKET NEWS ---\n{headlines}\n\n"
            f"--- CURRENT POSITION STATUS ---\n{position_data}\n\n"
            "Evaluate global sentiment and specific news alongside my current position. "
            "Decide on the best action: BUY, SELL, WAIT, or CLOSE (if strategy targets met or danger detected)."
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

