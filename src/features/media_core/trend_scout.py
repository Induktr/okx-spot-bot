import logging
import asyncio
import os
import random
import json
from datetime import datetime
from src.app.config import config
from openai import OpenAI

class TrendScout:
    """
    Advanced TrendScout (The Aggregator Voyager).
    Task: Synthesize viral data from multiple virtual aggregators 
    to provide high-converting, unique video formats for the CRYPTO/TRADING niche.
    Uses GROQ (Llama 3) for super-fast trend synthesis.
    """
    def __init__(self):
        # Initialize Groq for Marketing Tasks
        self.marketing_client = None
        if config.GROQ_API_KEY:
            try:
                self.marketing_client = OpenAI(
                    api_key=config.GROQ_API_KEY,
                    base_url="https://api.groq.com/openai/v1"
                )
                self.marketing_model = config.GROQ_MODEL
                logging.info("🧠 SCOUT BRAIN: Groq (Llama 3) connected.")
            except Exception as e:
                logging.warning(f"⚠️ Scout Groq Init Failed: {e}")
        
        # Virtual Aggregator Sources (Knowledge Bases)
        self.aggregators = {
            "TokBoard": "Focused on trending sounds and beat-drop patterns.",
            "TikTok Creative Center": "Focuses on high-retention visual hooks and editing styles.",
            "SocialInsider": "Deep analysis of niche-specific (Finance/Tech) engagement metrics.",
            "Influee": "UGC-style (User Generated Content) formats for authenticity."
        }
        
    async def find_top_trends(self, limit=5):
        """
        Synthesizes trends from virtual aggregators using Groq AI.
        """
        logging.info("🕵️ SCOUT: Aggregating trends from multiple sources...")
        
        if not self.marketing_client:
            logging.error("❌ SCOUT: No Groq client initialized! Cannot find trends.")
            return self._get_fallbacks()

        aggregator_context = json.dumps(self.aggregators)
        
        prompt = (
            f"DATE: {datetime.now().strftime('%B %Y')}\n"
            f"NICHE: Algorithmic Trading / Crypto Transparency / FinTech\n"
            f"SOURCES: {aggregator_context}\n\n"
            "TASK: Act as a high-end Trend Aggregator for TikTok/Instagram Reels. "
            "Analyze the current viral landscape and output 3-5 UNIQUE video formats. "
            "Every format must feel distinct in Narrative, Visual, and Audio structure.\n\n"
            "OUTPUT FORMAT (JSON ARRAY ONLY):\n"
            "[\n"
            "  {\n"
            "    'id': '...', \n"
            "    'name': 'Format Name (e.g., The Matrix Reveal)', \n"
            "    'description': 'Detailed visual/editing instructions',\n"
            "    'format_type': 'ONE_OF [SPLIT_SCREEN, POV_PHONE, HYPE_GLITCH, DEFAULT]',\n"
            "    'visual_style': 'ONE_OF [FLASH_CYBER, MINIMAL_TEXT, GLITCH_TRANSITION, CINEMATIC_ZOOM, REAL_WORLD_OVERLAY]',\n"
            "    'trending_song': 'Current viral song candidate (e.g. MONTAGEM PR FUNK)',\n"
            "    'aggregator_source': 'Which virtual source inspired this'\n"
            "  }\n"
            "]"
        )

        try:
            logging.info(f"🕵️ SCOUT: Calling Groq ({self.marketing_model})...")
            response = self.marketing_client.chat.completions.create(
                model=self.marketing_model,
                messages=[
                    {"role": "system", "content": "You are a professional social media trend aggregator."},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"}
            )
            
            raw_content = response.choices[0].message.content
            # Note: Groq with json_mode might return a wrapping object, or just the list.
            # Let's handle both.
            data = json.loads(raw_content)
            
            # If the response is a dict with a 'trends' key or similar, extract the list.
            if isinstance(data, dict):
                for key in data:
                    if isinstance(data[key], list):
                        trends = data[key]
                        break
                else:
                    trends = [data] # Fallback if it's just one object
            else:
                trends = data

            logging.info(f"🕵️ SCOUT: Successfully synthesized {len(trends)} unique trends via Groq.")
            return trends[:limit]
            
        except Exception as e:
            logging.error(f"❌ SCOUT ERROR: Groq aggregation failed: {e}")
            return self._get_fallbacks()

    def _get_fallbacks(self):
        return [
            {
                "id": "fallback_minimal",
                "name": "The Transparency Log",
                "description": "Clean dark mode UI with moving data logs in background.",
                "format_type": "DEFAULT",
                "visual_style": "MINIMAL_TEXT",
                "trending_song": "Interstellar Theme Remix",
                "aggregator_source": "Internal Fallback"
            },
            {
                "id": "fallback_split",
                "name": "Market Duel",
                "description": "Top screen showing luxury, bottom screen showing real-time execution.",
                "format_type": "SPLIT_SCREEN",
                "visual_style": "FLASH_CYBER",
                "trending_song": "MONTAGEM PR FUNK - S3BZS",
                "aggregator_source": "Internal Fallback"
            }
        ]

trend_scout = TrendScout()
