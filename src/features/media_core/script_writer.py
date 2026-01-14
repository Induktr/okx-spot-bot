import json
import logging
from src.app.config import config
from google import genai
from google.genai import types

class ScriptWriter:
    """
    Transforms raw trading data into viral TikTok/Shorts scripts using Gemini 2.0 Flash Lite.
    """
    def __init__(self):
        self.api_key = config.GEMINI_API_KEY
        self.client = genai.Client(api_key=self.api_key)
        self.system_instruction = (
            "You are a viral social media growth expert specializing in Crypto and Trading. "
            "You write scripts for TikTok, Reels, and YouTube Shorts. "
            "The tone must be Cyberpunk, high-energy, and 'Alpha-Trader' style. "
            "Use aggressive hooks, cliffhangers, and psychological triggers."
        )

    def generate_viral_script(self, win_data):
        """
        Generates a 30-second script for a given trade.
        """
        prompt = (
            f"Generate a viral 30-second video script based on this WINNING TRADE:\n"
            f"- Symbol: {win_data['symbol']}\n"
            f"- Profit: {win_data['pnl']} USDT\n"
            f"- ROI: {win_data['roi']}%\n"
            f"- Strategy: A.S.T.R.A. AI Intelligence\n\n"
            "Hook Requirement: Start with something like 'While you were sleeping, A.S.T.R.A. extracted {roi}% profit on {symbol}'.\n"
            "Include an emotional arc: From market stagnation to AI-driven explosion.\n"
            "Call to Action: Visit 'induktr.com' to get the bot.\n\n"
            "FORMAT: Output only the script text. Use bracketed instructions for visuals like [Scene: Dark neon room]. "
            "Maximum 100 words."
        )

        try:
            response = self.client.models.generate_content(
                model="gemini-2.0-flash-lite",
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=self.system_instruction
                )
            )
            script_text = response.text.strip()
            logging.info(f"✍️ SCRIPT WRITER: Viral script generated for {win_data['symbol']}")
            return script_text
        except Exception as e:
            logging.error(f"ScriptWriter Error: {e}")
            return f"While you were sleeping, A.S.T.R.A. extracted {win_data['roi']}% profit on {win_data['symbol']}. Visit induktr.com for details."

script_writer = ScriptWriter()
