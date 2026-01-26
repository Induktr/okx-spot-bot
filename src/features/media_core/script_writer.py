import json
import logging
import time
from src.app.config import config
from google import genai
from google.genai import types
from openai import OpenAI

class ScriptWriter:
    """
    Transforms raw trading data into viral TikTok/Shorts scripts and Telegram reports.
    Now supports TRIPLE-BRAIN ARCHITECTURE:
    1. Groq (Llama 3): Creative/Marketing (Primary - Free & Fast)
    2. DeepSeek: Creative/Marketing (Secondary)
    3. Gemini: Analytical Tasks (Fallback)
    """
    def __init__(self):
        self.api_key = config.GEMINI_API_KEY
        self.client = genai.Client(api_key=self.api_key)
        
        # Initialize Groq (Primary Creative Brain)
        self.marketing_client = None
        if config.GROQ_API_KEY:
            try:
                self.marketing_client = OpenAI(
                    api_key=config.GROQ_API_KEY,
                    base_url="https://api.groq.com/openai/v1"
                )
                self.marketing_model = config.GROQ_MODEL
                logging.info("🧠 CREATIVE BRAIN: Groq (Llama 3) connected.")
            except Exception as e:
                logging.warning(f"⚠️ Groq Init Failed: {e}")

        # Fallback to DeepSeek if Groq not available
        if not self.marketing_client and config.DEEPSEEK_API_KEY and "placeholder" not in config.DEEPSEEK_API_KEY:
             try:
                 self.marketing_client = OpenAI(
                     api_key=config.DEEPSEEK_API_KEY, 
                     base_url="https://api.deepseek.com"
                 )
                 self.marketing_model = "deepseek-chat"
                 logging.info("🧠 CREATIVE BRAIN: DeepSeek connected.")
             except Exception as e:
                 logging.warning(f"⚠️ DeepSeek Init Failed: {e}.")

        self.system_instruction = (
            "YOU ARE A SENIOR FINANCIAL DATA ANALYST & TRANSPARENCY REPORTER.\n"
            "Your mission is to report on the execution efficiency of the A.S.T.R.A. Algorithmic System.\n\n"
            "### REPORTING STRUCTURE (MANDATORY):\n"
            "1. DATA OBSERVATION (0-3s): Start with a specific market metric (e.g., 'Monitoring SOL/USDT liquidity delta...').\n"
            "2. EXECUTION ANALYSIS (3-12s): Report the system's performance metrics (ROI and Pair). Use professional terminology.\n"
            "3. SYSTEM TRANSPARENCY (12-20s): Explain that the A.S.T.R.A. model handles the risk management and execution layer.\n"
            "4. SOURCE OF DOCUMENTATION: Direct viewers to the project dashboard for full logic and history.\n\n"
            "### TERMS TO AVOID (CRITICAL FOR SOCIAL SAFETY):\n"
            "- AVOID: 'Passive Income', 'Get Rich', 'Broke free', 'Sales', 'Buy now', 'License'.\n"
            "- USE: 'Market Edge', 'Execution Delta', 'Transparency Dashboard', 'Algorithmic Efficiency'.\n\n"
            "### MANDATORY LINK (PROJECT DOCUMENTATION):\n"
            "Every script MUST end with: 'Protocol logs and data at: https://induktr-portfolio.vercel.app/'\n\n"
            "### STYLE DIRECTIVES:\n"
            "- TONE: Professional, analytical, calm, institutional aesthetic.\n"
            "- STRUCTURE: Data-driven, neutral language, objective reporting.\n"
            "- TARGET: Tech-savvy individuals interested in algorithmic transparency and market data."
        )

    def _call_marketing_ai(self, prompt, json_mode=False):
        """
        Calls Groq or DeepSeek API via OpenAI SDK.
        """
        try:
            response = self.marketing_client.chat.completions.create(
                model=self.marketing_model,
                messages=[
                    {"role": "system", "content": self.system_instruction},
                    {"role": "user", "content": prompt},
                ],
                response_format={'type': 'json_object'} if json_mode else None
            )
            return response.choices[0].message.content
        except Exception as e:
            logging.error(f"Marketing AI Error: {e}")
            raise e

    def _call_gemini_with_retry(self, prompt, config_params):
        """
        Executes an AI call with Exponential Backoff Strategy for 429 errors.
        Attempts: 3 | Delays: 5s -> 10s -> 20s.
        """
        max_retries = 3
        delay = 5
        
        for attempt in range(max_retries):
            try:
                # Attempt generation
                return self.client.models.generate_content(
                    model="gemini-2.0-flash-lite",
                    contents=prompt,
                    config=config_params
                )
            except Exception as e:
                # Check for Rate Limit (429) or Exhaustion
                error_str = str(e)
                if "429" in error_str or "ResourceExhausted" in error_str:
                    if attempt < max_retries - 1:
                        logging.warning(f"⏳ AI BRAIN SLEEPING: Rate Limit Hit. Keeping calm and waiting {delay}s... (Attempt {attempt+1}/{max_retries})")
                        time.sleep(delay)
                        delay *= 2 # Exponential backoff
                        continue
                    else:
                        logging.error(f"❌ AI BRAIN EXHAUSTED: Failed after {max_retries} attempts.")
                        raise e # Let the fallback handle it
                else:
                    raise e # Retrying won't fix syntax/auth errors, so raise immediately

    def select_trend_and_write_script(self, win_data, active_trends):
        """
        Analyzes 5 trending concepts and picks one to adapt for A.S.T.R.A.
        Returns JSON with 'script', 'selected_style', 'trending_song', and 'reasoning'.
        """
        trends_desc = "\n".join([
            f"- Trend ID: {t['id']} | Name: {t['name']} | Song: {t.get('trending_song', 'N/A')} | Visual: {t['visual_style']}" 
            for t in active_trends
        ])

        prompt = (
            f"CONTEXT: You are the Director of Viral Content for an AI Trading Bot named A.S.T.R.A.\n"
            f"WINNING TRADE DATA: Symbol {win_data['symbol']}, ROI {win_data['roi']}%, Profit ${win_data['pnl']}\n\n"
            f"CURRENT TIKTOK TRENDS:\n{trends_desc}\n\n"
            "TASK: Pick the best trend to showcase this specific trade results. Adapt the trend to feature our PnL result.\n"
            "AVAILABLE STYLES: [FLASH_CYBER, MINIMAL_TEXT, GLITCH_TRANSITION, CINEMATIC_ZOOM]\n\n"
            "OUTPUT FORMAT (JSON ONLY):\n"
            "{\n"
            "  'selected_trend_name': '...', \n"
            "  'visual_style': 'ONE_OF_AVAILABLE_STYLES', \n"
            "  'trending_song': 'Copy the exact song name from the selected trend above', \n"
            "  'script': 'Full voiceover text or text-overlay description...',\n"
            "  'reasoning': 'Why this trend fits this trade'\n"
            "}"
        )

        # PRIORITY: Try Marketing AI (Groq/DeepSeek)
        if self.marketing_client:
            try:
                raw_response = self._call_marketing_ai(prompt, json_mode=True)
                return json.loads(raw_response)
            except Exception as e:
                logging.warning(f"⚠️ Marketing AI Failed ({e}). Falling back to Gemini...")
        
        # FALLBACK: Gemini (Analytical Brain)
        try:
            # Use the new robust caller
            response = self._call_gemini_with_retry(
                prompt,
                config_params=types.GenerateContentConfig(
                    system_instruction=self.system_instruction,
                    response_mime_type='application/json'
                )
            )
            return json.loads(response.text)
        except Exception as e:
            logging.error(f"Trend Analysis Error: {e}")
            # Fallback
            return {
                "selected_trend_name": "Fallback Cyber",
                "visual_style": "FLASH_CYBER",
                "script": f"While you slept, A.S.T.R.A. made {win_data['roi']}% on {win_data['symbol']}.",
                "reasoning": "Error in AI processing, defaulting to Flash Style."
            }

    def generate_viral_script(self, win_data):
         # Legacy wrapper, redirects to simple generation if no trends provided
         return self.select_trend_and_write_script(win_data, [{"id":"legacy", "name":"Simple", "audio_vibe":"Tech", "visual_style":"DEFAULT"}])['script']

    def generate_rephrased_report(self, win_data):
        """
        Generates a concise, high-energy Telegram post for a trade.
        """
        prompt = (
            f"Write a catchy, aggressive Telegram post for a profitable trade:\n"
            f"- Asset: {win_data['symbol']}\n"
            f"- ROI: {win_data['roi']}%\n"
            f"- Profit: {win_data['pnl']} USDT\n"
            "Use emojis, short sentences, and a 'Cyberpunk Alpha' tone. "
            "Mention A.S.T.R.A. as the source of signal. Don't be boring."
        )

        try:
            if self.marketing_client:
                return self._call_marketing_ai(prompt)
            else:
                response = self._call_gemini_with_retry(
                    prompt,
                    config_params=types.GenerateContentConfig(
                        system_instruction=self.system_instruction
                    )
                )
                return response.text.strip()
        except Exception as e:
            logging.error(f"ScriptWriter Report Error: {e}")
            return f"🔥 A.S.T.R.A. WIN: {win_data['symbol']} | ROI: {win_data['roi']}% | Profit: {win_data['pnl']} USDT"

script_writer = ScriptWriter()
