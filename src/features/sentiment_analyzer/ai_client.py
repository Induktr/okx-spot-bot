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
            "Role: You are ASTRA, a precision-focused Quant Trading Engine. You balance aggressive opportunity capture with calculated risk management.\n"
            "Current Task: Analyze News + MTF Technicals + Institutional Flow to generate high-probability trade signals.\n\n"
            "MANDATORY DECISION LOGIC:\n"
            "1. RISK FIRST: Look at 'HELD POSITION' data. If ROE is < -5% AND Trends shift BEARISH, output 'CLOSE'.\n"
            "2. PROFIT PROTECTION: If ROE is > 15% and RSI > 75 (Overbought), consider 'ADJUST' (tighten SL) or 'CLOSE' to lock gains.\n"
            "3. ENTRY CRITERIA: Seek 'confluence'. Aligned Trends (1h/4h) + Momentum (MACD/RSI) + News Tailwinds.\n"
            "   - If Technicals are Bullish but News is Bearish -> Score: 4-6 (WAIT).\n"
            "   - If Technicals are Bearish and News is Bearish -> Score: 1-3 (WAIT/SELL).\n"
            "   - If Technicals are Bullish and News is Bullish -> Score: 8-10 (BUY).\n"
            "   - If No clear signal -> Score: 5 (WAIT).\n"
            "4. SCORING GUIDANCE: Use the full 0-10 range. \n"
            "   - 1-3: Strong Sell / Bearish Pressure\n"
            "   - 4-6: Neutral / Consolidation / Uncertainty\n"
            "   - 7-9: Strong Buy / Bullish Conviction\n"
            "   - 10: Perfect Setup (All Indicators Aligned)\n"
            "5. OUTPUT SCHEMA: You MUST return a JSON object with EXACTLY these fields:\n"
            "   - 'action': [BUY, SELL, CLOSE, ADJUST, WAIT]\n"
            "   - 'target_symbol': (string, e.g. 'SOL/USDT')\n"
            "   - 'sentiment_score': (0-10 integer)\n"
            "   - 'reasoning': (string, max 30 words, concise and analytical)\n"
            "   - 'tp_pct': (float, recommended target profit e.g. 0.055 for 5.5%)\n"
            "   - 'sl_pct': (float, recommended stop loss e.g. 0.02 for 2.0%)\n"
            "   - 'leverage': (integer, 1-10, based on risk factor)\n"
            "   - 'budget_usdt': (float, proposed allocation, e.g. 500.0)\n"
            "   - 'risk_factor': ['LOW', 'MODERATE', 'HIGH']\n\n"
            "Budgeting Strategy: For BUY/SELL, calculate 'budget_usdt' based on the provided total balance. \n"
            "   - Use a 'Kelly Criterion' inspired approach: allocate 10% (Conservative) to 25% (Aggressive) of total balance.\n"
            "   - Higher 'sentiment_score' and 'LOW' risk factor justify larger allocations.\n"
            "Style: Analytical, professional, decisive. Output valid JSON.\n"
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
                    logging.error(f"❌ Gemini failed after trying all {max_retries} models: {error_str[:150]}")
                    return {"target_symbol": "NONE", "sentiment_score": 5, "action": "WAIT", "reasoning": f"AI unavailable: {error_str[:100]}"}
        
        return {"target_symbol": "NONE", "sentiment_score": 5, "action": "WAIT", "reasoning": "AI unavailable: All Gemini models exhausted."}

# Initialize AI client
ai_client = AIAgent()
