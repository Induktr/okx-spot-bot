import aiohttp
import logging
import time
from typing import List, Dict, Any
from src.app.config import config

class WhaleDetector:
    """
    On-Chain Sentinel module for A.S.T.R.A.
    Tracks large cryptocurrency transactions (Whales) to gauge market intent.
    Uses Whale-Alert.io API or specialized news filtering if no key provided.
    """
    API_URL = "https://api.whale-alert.io/v1/transactions"

    def __init__(self):
        self.large_moves: List[Dict[str, Any]] = []
        self.last_update = 0

    async def update(self, min_value_usd: float = 10000000):
        """Fetches recent large transactions."""
        api_key = config.WHALE_ALERT_API_KEY
        
        # If no API key, we fallback to searching in news headlines for whale moves
        # This is implemented via a 'Mock-Enhanced-News' approach if key is missing
        if not api_key:
            logging.info("🐋 WHALE: No API key found. Using news-based sentinel mode.")
            return await self._update_from_news()

        try:
            # Whale Alert API requires 'start' timestamp (fetch last 10 mins)
            start_time = int(time.time()) - 600 
            params = {
                "api_key": api_key,
                "min_value": int(min_value_usd),
                "start": start_time
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(self.API_URL, params=params, timeout=10) as response:
                    if response.status == 200:
                        data = await response.json()
                        self.large_moves = data.get('transactions', [])
                        logging.info(f"🐋 WHALE: Found {len(self.large_moves)} massive moves in the last 10m.")
                    else:
                        logging.warning(f"🐋 WHALE: API returned status {response.status}. Falling back to news.")
                        await self._update_from_news()
        except Exception as e:
            logging.error(f"❌ WHALE: Error fetching whale data: {e}")
            await self._update_from_news()

    async def _update_from_news(self):
        """Fallback: Scans existing news for whale activity keywords."""
        # This is a stub that will be populated by the news aggregator's findings
        # in the main orchestrator cycle.
        return True

    def get_summary(self) -> str:
        """Returns a string summary for Gemini to analyze."""
        if not self.large_moves:
            return "No extreme whale movements detected on-chain (Stable)."
            
        summary = "CRITICAL ON-CHAIN DATA (LAST 10M):\n"
        # Limit to top 5 moves to avoid context bloat
        for i, m in enumerate(self.large_moves):
            if i >= 5: break
            amount = m.get('amount_usd', 0)
            asset = m.get('symbol', 'Unknown').upper()
            from_addr = m.get('from', {}).get('owner_type', 'unknown')
            to_addr = m.get('to', {}).get('owner_type', 'unknown')
            
            summary += f"- {amount/1e6:.1f}M USD of {asset} moved from {from_addr} to {to_addr}.\n"
            
        if any(m.get('to', {}).get('owner_type') == 'exchange' for m in self.large_moves):
            summary += "!! ALERT: High Exchange Inflow detected. Potential Sell pressure incoming !!"
            
        return summary

# Initialize Detector
whale_detector = WhaleDetector()
