from google import genai
from google.genai import types
import json
import logging
from src.app.config import config
from src.shared.utils.token_guard import token_guard

class AIAgent:
    """
    Brain module for A.S.T.R.A.
    Integrates with Google Gemini via the new google-genai SDK.
    """
    def __init__(self):
        self.keys = config.GEMINI_KEYS if config.GEMINI_KEYS else [config.GEMINI_API_KEY]
        self.current_key_index = 0
        self._init_client()
        self.model_id = config.GEMINI_MODEL
        self.system_instruction = (
            "Role: You are ASTRA, an advanced autonomous crypto portfolio manager with expertise in both Fundamental and Technical Analysis.\n"
            "Current Task: Analyze news and market data (Price + RSI + EMA) for a list of coins. Pick the BEST candidate.\n"
            "Mandates:\n"
            "1. Selection: Review 'MARKET SNAPSHOT'. Consider News + Technical Indicators (RSI, EMA). \n"
            "   - RSI Tip: <30 is Oversold (Potential Buy), >70 is Overbought (Potential Sell).\n"
            "   - EMA Tip: Price above EMA(20) suggests an Up-trend.\n"
            "2. Strategy: Look for CONVERGENCE. If News is BULLISH and RSI is low/neutral, it's a high-confidence signal.\n"
            "3. Profit/Risk: Aim for 30-35% profit and 20% SL. Adjust based on market context.\n"
            "4. Money Management: Base 'budget_usdt' on confidence (Sentiment 9-10 -> 25% balance, 6-8 -> 10%). Max 30% per coin.\n"
            "5. Flipping: You can return action 'SELL' to flip a LONG to SHORT (and vice-versa) if trend and news flip.\n"
            "Output Format: JSON only: {\"target_symbol\": \"BTC/USDT:USDT\", \"sentiment_score\": 1-10, \"action\": \"BUY/SELL/WAIT/CLOSE/ADJUST\", \"tp_pct\": 0.35, \"sl_pct\": 0.1, \"leverage\": 5, \"budget_usdt\": 15.0, \"reasoning\": \"Explain convergence of News + Technicals...\"}.\n"
            "If no action is needed for any coin, return \"target_symbol\": \"NONE\" and \"action\": \"WAIT\".\n"
        )

    def _init_client(self):
        # 1. User-Provided Key (Highest Priority)
        user_key = getattr(config, 'GEMINI_API_KEY', '')
        if user_key and len(user_key) > 10 and not user_key.startswith("AIzaSyCTX"): 
            self.client = genai.Client(api_key=user_key)
            logging.info("AI: Using USER PROVIDED Gemini Key (High Performance)")
            return

        # 2. Internal Pool (Backup/Demo)
        key = self.keys[self.current_key_index]
        self.client = genai.Client(api_key=key)
        logging.info(f"AI: Using Internal Key Pool #{self.current_key_index + 1} (Demo Limits)")

    def _rotate_key(self):
        self.current_key_index = (self.current_key_index + 1) % len(self.keys)
        self._init_client()
        logging.warning(f"AI: API Limit reached. Rotating to Key #{self.current_key_index + 1}")

    def analyze_news(self, headlines: str, balance: float, snapshot: str, market_mood: str = "Unknown") -> dict:
        """
        Routes the analysis request to the selected AI Provider.
        """
        provider = config.AI_PROVIDER
        logging.info(f"AI: Using Brain Provider [{provider.upper()}]")
        
        # Cloud Override
        if config.USE_CLOUD_AI:
            result = self._analyze_cloud(headlines, balance, snapshot, market_mood)
        elif provider == "openai" or provider == "deepseek":
            result = self._analyze_openai_compatible(headlines, balance, snapshot, market_mood)
        elif provider == "anthropic":
            result = self._analyze_anthropic(headlines, balance, snapshot, market_mood)
        else:
            result = self._analyze_gemini(headlines, balance, snapshot, market_mood)
            
        # SAFETY FIX: If AI returns a list (e.g. [ {..} ]), take the first item
        if isinstance(result, list):
            if len(result) > 0:
                logging.warning("AI returned a list. Using first item.")
                result = result[0]
            else:
                return {"sentiment_score": 5, "action": "WAIT", "reasoning": "AI returned empty list"}
                
        return result

    def _analyze_cloud(self, headlines, balance, snapshot, market_mood):
        # ... Cloud Logic (Same as before) ...
        import requests
        try:
            prompt = self._build_prompt(headlines, balance, snapshot, market_mood)
            response = requests.post(
                config.CLOUD_AI_NODES[0], # Using first node for now
                headers={"X-ASTRA-TOKEN": config.CLOUD_AI_TOKEN},
                json={
                    "prompt": prompt,
                    "system_instruction": self.system_instruction,
                    "model": self.model_id
                },
                timeout=65 # Increased timeout for cold starts
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logging.error(f"⚠️ Cloud Brain Error: {e}")
            logging.info("🔄 Switching to LOCAL Brain (Backup Mode)...")
            return self._analyze_gemini(headlines, balance, snapshot, market_mood)

    def _build_prompt(self, headlines, balance, snapshot, market_mood):
        return (
            f"--- ACCOUNT BALANCE ---\n{balance} USDT\n\n"
            f"--- GLOBAL MARKET MOOD ---\n{market_mood}\n\n"
            f"--- MARKET SNAPSHOT ---\n{snapshot}\n\n"
            f"--- LATEST NEWS ---\n{headlines}\n\n"
            "Review the snapshot and news. Which coin from the list is the best candidate to BUY, SELL, or requires management (CLOSE/ADJUST)? "
            "Return the 'target_symbol' and the determined action. If nothing is worth trading, return target_symbol: NONE. "
            "IMPORTANT: In your 'reasoning', you MUST cite the RSI value and Trend provided in the SNAPSHOT to justify your decision."
        )

    def _analyze_openai_compatible(self, headlines, balance, snapshot, market_mood):
        from openai import OpenAI
        
        # Select Key & Base URL
        if config.AI_PROVIDER == "deepseek":
            client = OpenAI(api_key=config.DEEPSEEK_API_KEY, base_url="https://api.deepseek.com/v1")
            model = config.DEEPSEEK_MODEL
        else:
            client = OpenAI(api_key=config.OPENAI_API_KEY)
            model = config.OPENAI_MODEL
            
        try:
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": self.system_instruction},
                    {"role": "user", "content": self._build_prompt(headlines, balance, snapshot, market_mood)}
                ],
                response_format={ "type": "json_object" }
            )
            return json.loads(response.choices[0].message.content)
        except Exception as e:
            logging.error(f"OpenAI/DeepSeek Error: {e}")
            return {"sentiment_score": 5, "action": "WAIT", "reasoning": str(e)}

    def _analyze_anthropic(self, headlines, balance, snapshot, market_mood):
        import anthropic
        client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
        
        try:
            message = client.messages.create(
                model=config.ANTHROPIC_MODEL,
                max_tokens=1024,
                system=self.system_instruction,
                messages=[
                    {"role": "user", "content": self._build_prompt(headlines, balance, snapshot, market_mood)}
                ]
            )
            return json.loads(message.content[0].text)
        except Exception as e:
            logging.error(f"Anthropic Error: {e}")
            return {"sentiment_score": 5, "action": "WAIT", "reasoning": str(e)}

    def _analyze_gemini(self, headlines: str, balance: float, snapshot: str, market_mood: str = "Unknown") -> dict:
        """
        Original Gemini Logic with Key Rotation
        """
        token_guard.wait_if_needed()
        
        prompt = self._build_prompt(headlines, balance, snapshot, market_mood)

        max_retries = 2
        for attempt in range(max_retries):
            try:
                # ... existing Gemini call logic ...
                response = self.client.models.generate_content(
                    model=self.model_id,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        system_instruction=self.system_instruction,
                        response_mime_type='application/json'
                    )
                )
                return json.loads(response.text)
                
            except Exception as e:
                # ... existing error handling ...
                error_str = str(e)
                if "429" in error_str or "RESOURCE_EXHAUSTED" in error_str:
                    logging.error(f"AI: Quota exceeded on attempt {attempt + 1}. Rotating key...")
                    self._rotate_key()
                    import time
                    time.sleep(2)
                    continue
                else:
                    return {"sentiment_score": 5, "action": "WAIT", "reasoning": str(e)}
        
        return {"sentiment_score": 5, "action": "WAIT", "reasoning": "AI rotation failed after retries."}

# Initialize AI client
ai_client = AIAgent()
