import asyncio
import logging
import datetime
from typing import List, Dict, Any
from src.features.sentiment_analyzer.ai_client import ai_client
from src.shared.utils.memory_bank import memory_bank
from src.app.config import config

class KaizenManager:
    """
    Module 5: KaizenManager (Process Growth Engine)
    Responsibility: Background analysis of past decisions to improve future performance.
    Runs for 30-45 minutes after each cycle using Groq for cost-efficiency.
    """
    def __init__(self):
        self.is_active = False
        self.active_task = None

    async def start_kaizen_session(self, last_symbol: str, headlines: List[str]):
        """Starts a background learning session."""
        if self.is_active:
            logging.info("🧠 KAIZEN: A session is already running. Skipping redundant start.")
            return

        self.is_active = True
        self.active_task = asyncio.create_task(self._run_kaizen_loop(last_symbol, headlines))

    async def _run_kaizen_loop(self, symbol: str, headlines: List[str]):
        logging.info(f"🧠 KAIZEN: Starting background analysis for {symbol} (Duration: 30m)...")
        
        start_time = datetime.datetime.now()
        duration_limit = datetime.timedelta(minutes=30)
        
        try:
            while datetime.datetime.now() - start_time < duration_limit:
                # 1. Fetch current 'Memory' of the decision
                last_decision = memory_bank.get_last_action(symbol)
                if not last_decision: break
                
                # 2. Perform 'Mini-Kaizen' via Groq (Cost Efficient)
                # We force Groq here to save Gemini tokens
                kaizen_prompt = (
                    f"Last Decision for {symbol}: {last_decision['action']} (Score: {last_decision['sentiment_score']})\n"
                    f"Reasoning: {last_decision['reasoning']}\n\n"
                    f"Current News: {headlines[:5]}\n\n"
                    "Task: Perform a 'Kaizen' (Continuous Improvement) analysis. "
                    "Was the decision to 'WAIT' or 'ACT' correct based on these news? "
                    "Provide a ONE-SENTENCE tactical insight for the next cycle. "
                    "Be critical. If I was too cowardly, say it. If too risky, warn me."
                )
                
                # Use Groq for background work
                insight = await self._get_groq_insight(kaizen_prompt)
                
                # 3. Store insight as context for next cycle
                if insight:
                    logging.info(f"🧠 KAIZEN INSIGHT: {insight}")
                    # We store it in a special 'kaizen' field in memory bank
                    # This could be added to MemoryBank implementation if needed
                
                # Sleep for 15 minutes before next background check
                await asyncio.sleep(900) 
                
        except Exception as e:
            logging.error(f"❌ KAIZEN ERROR: {e}")
        finally:
            self.is_active = False
            logging.info("🧠 KAIZEN: Session complete. Entering deep sleep to save resources.")

    async def _get_groq_insight(self, prompt: str) -> str:
        """Helper to get fast insight from Groq."""
        try:
            # We bypass the main analyze and call Groq directly
            # This requires Groq to be correctly set up in AIAgent
            # For now, we'll use a simplified version
            from openai import AsyncOpenAI
            client = AsyncOpenAI(api_key=config.GROQ_API_KEY, base_url="https://api.groq.com/openai/v1")
            
            response = await client.chat.completions.create(
                model=config.GROQ_MODEL,
                messages=[
                    {"role": "system", "content": "You are a Kaizen Trading Mentor. Be sharp, critical and concise."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=100
            )
            return response.choices[0].message.content
        except Exception as e:
            logging.error(f"Groq Kaizen Error: {e}")
            return None

# Global instance
kaizen_manager = KaizenManager()
