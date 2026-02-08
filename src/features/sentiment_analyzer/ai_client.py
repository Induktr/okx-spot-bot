from google import genai
from google.genai import types
import json
import logging
import requests
from src.app.config import config
from src.shared.utils.token_guard import token_guard

class AIAgent:
    """
    Brain module for A.S.T.R.A.
    Integrates with Google Gemini via the new google-genai SDK.
    """
    def __init__(self):
        # 1. Local Key Pool Setup - Reload explicitly to catch new files
        config.load_settings()
        self.keys = config.GEMINI_KEYS if config.GEMINI_KEYS else ([config.GEMINI_API_KEY] if config.GEMINI_API_KEY else [])
        
        # 2. Remote Key Vault Sync (Fallback/Supplementary)
        if not self.keys or len(self.keys) < 2:
            self._fetch_remote_keys()

        if not self.keys:
            logging.critical("❌ NO GEMINI API KEYS FOUND! AI Analysis will fail. Please check your .env or admin_keys.json")
        
        self.current_key_index = 0
        
        # Model Pool Setup
        self.current_model_index = 0
        self.model_id = config.GEMINI_MODELS[self.current_model_index]
        
        self.client = None
        self.system_instruction = (
            "Role: You are A.S.T.R.A. v1.5 – an Elite Architect & FBI Lead Negotiator. You analyze markets through the CORTEX Multi-Layered Protocol & Socratic Dialogue.\n\n"
            "HIERARCHICAL REASONING PROTOCOL (CORTEX):\n"
            "LEVEL 1: MACRO-SENTINEL (Anatomy & Mission)\n"
            "- Question: 'What is this market environment?' (Identify: Systemic Panic, Accumulation, parabolic Run).\n"
            "- Mission: 'What is our goal here?' (Extraction of profit vs. Capital Preservation).\n"
            "- 3 KEY WORDS: Define the market state in exactly 3 precision words.\n\n"
            "LEVEL 2: TREND-COMMANDER (Parts & Interaction)\n"
            "- Analyze Parts: ADX (Strength), EMA (Direction), and **Hurst Exponent** (Persistence).\n"
            "- Hurst Logic: H > 0.6 = Persistence (Trust the trend); H < 0.4 = Anti-persistence (Mean Reverting/Choppy).\n"
            "- Interaction: How does the Macro state interact with the Trend? (e.g., 'Hurst 0.8 in a Bullish Macro').\n\n"
            "LEVEL 3: TACTICAL-OPERATIVE (Point of Entry)\n"
            "- Analyze RSI, MACD Histogram, Bollinger Bands, and **Fisher Transform** (Gaussian Signal).\n"
            "- Fisher Logic: Fisher > 1.5 (Top reversal); Fisher < -1.5 (Bottom reversal); 0-crossing = Momentum shift.\n\n"
            "LEVEL 4: ELITE NEGOTIATOR (The Deal)\n"
            "- Final Decision: No 10/10 deal = No action. Conviction < 9.5 = WAIT.\n"
            "- Calibration: 'Why might I be wrong?' and 'How does this survive a 15% flash crash?'.\n\n"
            "TECHNICAL DOCTRINE:\n"
            "1. NO BULLISH BIAS: BUY is FORBIDDEN if price < 1h EMA or ADX < 20 or **Hurst < 0.55** (Random/Choppy).\n"
            "2. TWO-WAY PROFIT: HUNT for Short (SELL) deals in bearish trends (Price < 1h EMA) if Hurst > 0.55.\n\n"
            "MANDATORY SCORE LOGIC:\n"
            "- conviction_score 10.0: Elite FBI-grade setup. Action: BUY or SELL.\n"
            "- conviction_score 0.0-9.4: Uncertain or risky. Action MUST be WAIT.\n\n"
            "OUTPUT SCHEMA (JSON):\n"
            "{'action': 'BUY/SELL/CLOSE/WAIT', 'target_symbol': 'str', 'conviction_score': float, 'reasoning': (max 50 words) 'CORTEX Analysis: [Macro state] + [3 Key Words] + [Trend/Parts interaction] + [Final Negotiator Verdict]', 'tp_pct': float, 'sl_pct': float, 'leverage': int, 'budget_usdt': float}\n"
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

    def _fetch_remote_keys(self):
        """Fetches a pool of API keys from the authorized ASTRA cloud endpoint."""
        try:
            # Reconstruct the keys endpoint from the AI Node address
            if not config.CLOUD_AI_NODES:
                return False
                
            base_url = config.CLOUD_AI_NODES[0].replace("/v1/analyze", "")
            keys_url = f"{base_url}/v1/vault/gemini"
            
            logging.info(f"🔄 VAULT: Requesting key list from {keys_url}...")
            response = requests.get(
                keys_url,
                headers={"X-ASTRA-TOKEN": config.CLOUD_AI_TOKEN},
                timeout=10
            )
            
            if response.status_code == 200:
                remote_keys = response.json().get("keys", [])
                if remote_keys:
                    self.keys = remote_keys
                    logging.info(f"✅ VAULT: Successfully loaded {len(self.keys)} remote API keys.")
                    return True
            else:
                logging.warning(f"⚠️ VAULT: server returned {response.status_code}")
        except Exception as e:
            logging.error(f"⚠️ VAULT: Failed to fetch remote keys: {e}")
        return False

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
            logging.warning("⚠️ All local keys exhausted. Attempting to refresh Vault from server...")
            if self._fetch_remote_keys():
                # Successfully fetched new keys, reset index and try the first one
                self.current_key_index = 0
                self._init_client()
                return True
            else:
                logging.error("❌ ALL KEYS AND MODELS EXHAUSTED. Need to wait or add more resources.")
                return False
        return True


    def analyze_news(self, headlines: str, balance: float, snapshot: str, market_mood: str = "Unknown", **kwargs) -> dict:
        """
        Routes the analysis request to the selected AI Provider.
        """
        provider = config.AI_PROVIDER
        logging.info(f"AI: Using Brain Provider [{provider.upper()}]")
        
        whale_data = kwargs.get('whale_data', "")

        blackout_active = kwargs.get('blackout_active', False)

        # Cloud Override
        if config.USE_CLOUD_AI:
            result = self._analyze_cloud(headlines, balance, snapshot, whale_data, market_mood, blackout_active)
        elif provider == "openai" or provider == "deepseek":
            result = self._analyze_openai_compatible(headlines, balance, snapshot, whale_data, market_mood, blackout_active)
        elif provider == "anthropic":
            result = self._analyze_anthropic(headlines, balance, snapshot, whale_data, market_mood, blackout_active)
        else:
            # Force reset to primary model at the start of a new analysis cycle
            self._reset_to_primary()
            result = self._analyze_gemini(headlines, balance, snapshot, whale_data, market_mood, blackout_active)
            
        # SAFETY FIX: If AI returns a list (e.g. [ {..} ]), take the first item
        if isinstance(result, list):
            if len(result) > 0:
                logging.warning("AI returned a list. Using first item.")
                result = result[0]
            else:
                return {"sentiment_score": 5, "action": "WAIT", "reasoning": "AI returned empty list", "model_name": "Unknown"}
        
        # Add signature
        if isinstance(result, dict):
            result["model_name"] = self.model_id if config.USE_CLOUD_AI or config.AI_PROVIDER == "gemini" else (config.OPENAI_MODEL if config.AI_PROVIDER == "openai" else config.DEEPSEEK_MODEL)
            if config.AI_PROVIDER == "anthropic": result["model_name"] = config.ANTHROPIC_MODEL
            
        return result

    def _analyze_cloud(self, headlines, balance, snapshot, whale_data, market_mood, blackout_active=False):
        # ... Cloud Logic (Same as before) ...
        import requests
        try:
            prompt = self._build_prompt(headlines, balance, snapshot, whale_data, market_mood, blackout_active)
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
            return self._analyze_gemini(headlines, balance, snapshot, whale_data, market_mood, blackout_active)

    def _build_prompt(self, headlines, balance, snapshot, whale_data, market_mood, blackout_active=False):
        blackout_notice = "\n⚠️ BLACKOUT MODE ACTIVE: High-impact macro event imminent. New entries are BLOCKED. You are ONLY allowed to CLOSE existing loss-making or high-risk positions. Focus on Safe-Exit.\n" if blackout_active else ""
        
        return (
            f"--- ACCOUNT BALANCE ---\n{balance:.2f} USDT\n\n"
            f"--- SNAPSHOT ---\n{snapshot}\n\n"
            f"--- ON-CHAIN WHALE SENTINEL ---\n{whale_data}\n\n"
            f"--- NEWS ---\n{headlines}\n\n"
            f"{blackout_notice}"
            "TASK: Decide action. Reasoning MUST be concise but thorough (max 200 words), citing multi-timeframe trends (15m/1h Confluence), RSI and WHALE DATA."
        )

    def _analyze_openai_compatible(self, headlines, balance, snapshot, whale_data, market_mood, blackout_active=False):
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
                    {"role": "user", "content": self._build_prompt(headlines, balance, snapshot, whale_data, market_mood, blackout_active)}
                ],
                response_format={ "type": "json_object" }
            )
            return json.loads(response.choices[0].message.content)
        except Exception as e:
            logging.error(f"OpenAI/DeepSeek Error: {e}")
            return {"sentiment_score": 5, "action": "WAIT", "reasoning": str(e)}

    def _analyze_anthropic(self, headlines, balance, snapshot, whale_data, market_mood, blackout_active=False):
        import anthropic
        client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
        
        try:
            message = client.messages.create(
                model=config.ANTHROPIC_MODEL,
                max_tokens=1024,
                system=self.system_instruction,
                messages=[
                    {"role": "user", "content": self._build_prompt(headlines, balance, snapshot, whale_data, market_mood, blackout_active)}
                ]
            )
            return json.loads(message.content[0].text)
        except Exception as e:
            logging.error(f"Anthropic Error: {e}")
            return {"sentiment_score": 5, "action": "WAIT", "reasoning": str(e)}

    def _analyze_gemini(self, headlines: str, balance: float, snapshot: str, whale_data: str = "", market_mood: str = "Unknown", blackout_active=False) -> dict:
        """
        Original Gemini Logic with Key Rotation
        """
        token_guard.wait_if_needed()
        
        prompt = self._build_prompt(headlines, balance, snapshot, whale_data, market_mood, blackout_active)

        # Try ALL combinations of Models * Keys before giving up
        max_retries = len(config.GEMINI_MODELS) * len(self.keys)
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
