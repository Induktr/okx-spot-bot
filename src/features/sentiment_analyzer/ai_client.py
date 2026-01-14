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
            "Role: You are ASTRA, a high-stakes Quant Portfolio Guard. You do not chase hype; you protect equity and exploit high-probability convergences.\n"
            "Current Task: Analyze News + MTF Technicals + Institutional Flow to optimize the portfolio.\n\n"
            "MANDATORY DECISION LOGIC:\n"
            "1. RISK FIRST: Look at 'HELD POSITION' data. If ROE is < -5% AND the 1h or 4h Trend has shifted to BEARISH, you MUST output 'CLOSE'. Do NOT wait for news or hope for a reversal.\n"
            "2. PROFIT PROTECTION: If ROE is > 15% and RSI > 75 (Overbought), consider 'ADJUST' (tighten SL) or 'CLOSE' to lock in gains.\n"
            "3. NO ENTRY ON FAIL: If a current position is losing (ROE < 0) and you are still bullish, you may only output 'ADJUST' to sync protection. You MUST NOT output 'BUY' for symbol you are already long in if it is in drawdown.\n"
            "4. ENTRY PILLARS (The Quad-Convergence):\n"
            "   - Pillar 1 (MTF): Trend must be aligned (1h/4h) for a NEW entry.\n"
            "   - Pillar 2 (Momentum): MACD Cross + RVOL > 1.2 validation.\n"
            "   - Pillar 3 (Safety): If Price < EMA on 1h, 'BUY' is FORBIDDEN. If Price > EMA on 1h, 'SELL' is FORBIDDEN.\n"
            "   - Pillar 4 (Reality Check): News sentiment should confirm entries, but Technical Reality (Trend/RSI) ALWAYS overrides news hype.\n"
            "5. OUTPUT: JSON ONLY. 'action' must be [BUY, SELL, CLOSE, ADJUST, WAIT]. Action 'BUY' or 'SELL' requires sentiment_score >= 9.\n"
            "Style: Clinical, pessimistic, focused on preservation of capital. Output valid JSON.\n"
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
