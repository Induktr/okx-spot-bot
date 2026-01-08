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
        # Key Pool Setup
        self.keys = config.GEMINI_KEYS if config.GEMINI_KEYS else ([config.GEMINI_API_KEY] if config.GEMINI_API_KEY else [])
        
        if not self.keys:
            logging.critical("❌ NO GEMINI API KEYS FOUND! AI Analysis will fail. Please check your .env or admin_keys.json")
        
        self.current_key_index = 0
        
        # Model Pool Setup
        self.current_model_index = 0
        self.model_id = config.GEMINI_MODELS[self.current_model_index]
        
        self.client = None
        self.system_instruction = (
            "Role: You are ASTRA, an advanced autonomous crypto portfolio manager with expertise in both Fundamental and Technical Analysis.\n"
            "Current Task: Analyze news and market data (Price + RSI + EMA + Volume + Funding Rate) for a list of coins. Pick the BEST candidate.\n"
            "Mandates:\n"
            "1. Selection: Review 'MARKET SNAPSHOT'. Consider News + Technical Indicators (RSI, EMA, Trend, Volume, Funding). \n"
            "   - RSI Tip: <30 is Oversold (Potential Buy), >70 is Overbought (Potential Sell).\n"
            "   - EMA Tip: Price above EMA(20) suggests an Up-trend.\n"
            "   - Funding Tip: High positive funding (>0.05%) = crowded longs (reversal risk). Negative = shorts dominate.\n"
            "2. Strategy: Look for CONVERGENCE. If News is BULLISH + RSI low + Price > EMA = high-confidence BUY.\n"
            "3. Profit/Risk: Aim for 30-35% profit and 20% SL. Adjust based on market volatility.\n"
            "   - MANDATORY BREAKEVEN: If a position's current profit (ROE) exceeds 100%, you MUST suggest action: 'CLOSE' (to take 50% partial profit) or 'ADJUST' to move SL to entry price to ensure breakeven.\n"
            "4. Money Management: You MUST check the 'ACCOUNT BALANCE'. \n"
            "   - Sizing Principle: Calculate target budget as % of balance (Sentiment 9-10 -> 25%, 6-8 -> 10%).\n"
            "   - Profitability Floor: If the calculated budget is less than 30 USDT, you MUST upgrade it to a minimum of 30 USDT (provided balance > 30). This 'Floor' ensures that potential profits always outweigh exchange commissions. If balance < 30, use nearly full balance.\n"
            "   - Scalability: For large accounts where the percentage-based budget naturally exceeds 30 USDT, always follow the percentage-based rule.\n"
            "5. Flipping: You can return action 'SELL' to flip a LONG to SHORT (and vice-versa). You are responsible for deciding the leverage (1-20x) based on volatility.\n"
            "6. Leverage Constraint: Once you have entered a trade (Status show 'In LONG' or 'In SHORT' in SNAPSHOT), you MUST NOT suggest a change to 'leverage' for that specific position. Leverage should only be set during the initial 'BUY' or 'SELL' entry or when performing a 'FLIP'.\n"
            "7. Strategic Concentration: For small accounts where you are hitting the 'Profitability Floor', focus ONLY on the TOP 1-2 signals (Sentiment >= 8). For larger accounts with higher capacity, you may diversify across more symbols.\n"
            "Output Format: JSON only: {\"target_symbol\": \"BTC/USDT:USDT\", \"sentiment_score\": 1-10, \"action\": \"BUY/SELL/WAIT/CLOSE/ADJUST\", \"tp_pct\": 0.35, \"sl_pct\": 0.1, \"leverage\": 5, \"budget_usdt\": 15.0, \"reasoning\": \"CONCISE 2-sentence tactical summary citing RSI + Trend.\"}.\n"
            "Style: Be brief, clinical, and data-driven. No fluff.\n"
            "If no action is needed or balance is zero, return \"target_symbol\": \"NONE\" and \"action\": \"WAIT\".\n"
        )
        self._init_client()

    def _init_client(self):
        """Initialize Gemini client with current key from the pool."""
        api_key = self.keys[self.current_key_index]
        self.client = genai.Client(api_key=api_key)
        logging.info(f"AIAgent initialized: Key #{self.current_key_index + 1}/{len(self.keys)} | Model: {self.model_id}")

    def _reset_to_primary(self):
        """Resets indices to point to the first (best) model and first key."""
        if self.current_model_index != 0 or self.current_key_index != 0:
            self.current_model_index = 0
            self.current_key_index = 0
            self.model_id = config.GEMINI_MODELS[0]
            self._init_client()
            logging.info(f"🔄 Priority Reset: Starting cycle with primary model {self.model_id}")

    def _rotate_model(self):
        """Rotate to the next model in the pool to bypass rate limits."""
        old_model = self.model_id
        self.current_model_index = (self.current_model_index + 1) % len(config.GEMINI_MODELS)
        self.model_id = config.GEMINI_MODELS[self.current_model_index]
        logging.warning(f"🔄 Model rotated: {old_model} → {self.model_id}")
        
        # If we've cycled back to the first model, it means all models on this key are exhausted
        if self.current_model_index == 0:
            logging.warning("⚠️ All models exhausted on current key. Rotating to next key...")
            return self._rotate_key()
        return True

    def _rotate_key(self):
        """Rotate to the next API key in the pool and reset to first model."""
        old_key_idx = self.current_key_index
        self.current_key_index = (self.current_key_index + 1) % len(self.keys)
        
        # Reset model to first in pool
        self.current_model_index = 0
        self.model_id = config.GEMINI_MODELS[self.current_model_index]
        
        # Reinitialize client with new key
        self._init_client()
        logging.warning(f"🔑 API Key rotated: Key #{old_key_idx + 1} → Key #{self.current_key_index + 1}")
        
        # If we cycled back to the first key, ALL combinations are exhausted
        if self.current_key_index == 0:
            logging.error("❌ ALL KEYS AND MODELS EXHAUSTED. Need to wait or add more resources.")
            return False
        return True


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
            # Force reset to primary model at the start of a new analysis cycle
            self._reset_to_primary()
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
            "Review the snapshot and news. Pick the best candidate or manage current positions. "
            "Return JSON. IMPORTANT: 'reasoning' MUST be a CONCISE (max 30 words) tactical justification citing RSI and Trend."
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

        max_retries = len(config.GEMINI_MODELS)  # Try all models before giving up
        for attempt in range(max_retries):
            try:
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
                error_str = str(e)
                # Check for rate limit OR server overload errors
                needs_rotation = any(x in error_str for x in ["429", "RESOURCE_EXHAUSTED", "503", "UNAVAILABLE"])
                
                if needs_rotation and attempt < max_retries - 1:
                    logging.warning(f"🚨 Gemini error on model '{self.model_id}' (attempt {attempt + 1}/{max_retries}): {error_str[:100]}")
                    self._rotate_model()
                    import time
                    time.sleep(3)  # Brief cooldown before retry
                    continue
                else:
                    # Final attempt failed or non-retryable error
                    if "429" in error_str:
                        logging.critical("CRITICAL: Gemini API returned 429 (Rate Limit). A.S.T.R.A. will sleep for 60 minutes.")
                        import time
                        time.sleep(3600) # Sleep 60 minutes
                    
                    logging.error(f"❌ Gemini failed after trying all {max_retries} models: {error_str[:150]}")
                    return {"sentiment_score": 5, "action": "WAIT", "reasoning": f"AI unavailable: {error_str[:100]}"}
        
        return {"sentiment_score": 5, "action": "WAIT", "reasoning": "All Gemini models exhausted."}

# Initialize AI client
ai_client = AIAgent()
