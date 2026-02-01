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

        self.personas = [
            "AGGRESSIVE ALPHA: Direct, loud, focus on winning and dominance. Uses short, punchy sentences.",
            "COLD LOGICAL QUANT: Intellectual, data-obsessed, neutral. Focuses on statistical significance and execution logs.",
            "CYBERPUNK REBEL: High-tech, slightly anti-authoritarian. Focuses on 'extracting' liquidity and beating the traditional system.",
            "ZEN MASTER: Calm, focused on the 'flow' of the market and automated precision.",
            "STREET SMART TRADER: Practical, high-energy, uses slightly informal but professional trading slang."
        ]

        self.system_instruction = (
            "YOU ARE A VIRAL CONTENT ARCHITECT FOR A.S.T.R.A. (ALGORITHMIC SYSTEM FOR TRADING & RISK ANALYSIS).\n"
            "Your mission is to report market data and system execution with RADICAL VARIETY to avoid shadowbans and repetitive content flags.\n\n"
            "### CORE RULE: ZERO REPETITION\n"
            "- Every script must have a unique hook. NEVER start with 'Did you know', 'In this video', or 'Watch how'.\n"
            "- Vary the sentence structure and vocabulary in every single response.\n"
            "- Forbid the use of overused AI filler words: 'Incredible', 'Revolutionary', 'Game-changer', 'The future is here'.\n\n"
            "### REPORTING STRUCTURE (FLEXIBLE BUT MANDATORY):\n"
            "1. THE HOOK (0-3s): Start with a sharp, unexpected observation about the specific asset. No cliches.\n"
            "2. THE EXECUTION (3-12s): Integrate the ROI ({roi}%) and Pair ({symbol}) naturally into a narrative, not just a list.\n"
            "3. THE LOGIC (12-20s): Briefly touch on how the algorithm managed the volatility (e.g., 'system volatility dampening', 'delta neutral adjustments').\n"
            "4. THE PROOF: Direct viewers to the transparency dashboard.\n\n"
            "### MANDATORY ENDING:\n"
            "Every script MUST end with: 'Protocol logs and data at: https://induktr-portfolio.vercel.app/'\n\n"
            "### STYLE DIRECTIVES:\n"
            "- TONE: Will be dictated by the assigned PERSONA.\n"
            "- LANGUAGE: English, direct, no marketing fluff, analytical foundation."
        )

    def _call_marketing_ai(self, prompt, json_mode=False):
        """
        Calls Groq or DeepSeek API via OpenAI SDK.
        """
        # Inject persona and chaos seed for maximum variety
        import random
        persona = random.choice(self.personas)
        chaos_seed = f"RandomSeed_{random.randint(1000, 9999)}_{time.time()}"
        
        full_prompt = (
            f"ASSIGNED PERSONA: {persona}\n"
            f"CHAOS FACTOR (Entropy Seed): {chaos_seed}\n\n"
            f"USER REQUEST: {prompt}\n\n"
            f"REMINDER: Do NOT repeat yourself. Write a COMPLETELY NEW narrative that fits the persona."
        )

        try:
            response = self.marketing_client.chat.completions.create(
                model=self.marketing_model,
                messages=[
                    {"role": "system", "content": self.system_instruction},
                    {"role": "user", "content": full_prompt},
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
            f"WINNING TRADE DATA: Symbol {win_data['symbol']}, ROI {win_data['roi']}%, Profit ${win_data['pnl']}\n\n"
            f"CURRENT TIKTOK TRENDS:\n{trends_desc}\n\n"
            "TASK: Create a viral script and metadata for this trade. \n"
            "1. Select a TREND that fits the trade best.\n"
            "2. Write a viral TITLE that is unique and clickable (Avoid: 'Insane profit', 'How I made').\n"
            "3. Write a SCRIPT: Use the assigned persona. Be creative. Use varied sentence lengths.\n"
            "4. DESCRIPTION: Write a unique 2-3 sentence video description (for YouTube/TikTok caption) using hashtags.\n\n"
            "AVAILABLE STYLES: [FLASH_CYBER, MINIMAL_TEXT, GLITCH_TRANSITION, CINEMATIC_ZOOM, INFOGRAPHIC]\n"
            "AVAILABLE FORMATS: [DEFAULT, SPLIT_SCREEN, POV_PHONE]\n\n"
            "OUTPUT FORMAT (JSON ONLY):\n"
            "{\n"
            "  'selected_trend_name': '...', \n"
            "  'visual_style': 'ONE_OF_AVAILABLE_STYLES', \n"
            "  'format_type': 'ONE_OF_AVAILABLE_FORMATS', \n"
            "  'viral_title': '...', \n"
            "  'video_description': '...', \n"
            "  'hashtags': '...', \n"
            "  'trending_song': '...', \n"
            "  'card_heading': 'catchy 2-3 word header', \n"
            "  'card_status': '...', \n"
            "  'script': 'Full voiceover text...',\n"
            "  'reasoning': '...'\n"
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
