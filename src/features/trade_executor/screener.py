import logging
import asyncio
from typing import List, Dict, Any
from src.app.config import config
from src.shared.utils.analysis import tech_analysis

class MarketScreener:
    """
    Module 1: MarketScreener (Async Version)
    Responsibility: Discovering hot assets and pre-screening them in parallel.
    Uses asyncio for high-performance discovery.
    """
    def __init__(self, traders_map: Dict[str, Any]):
        self.traders = traders_map
        # For discovery, we use the first available trader
        self.primary_trader = list(traders_map.values())[0] if traders_map else None

    async def discover_candidates(self) -> List[str]:
        """Collect potential symbols from top volume, user list, and open positions."""
        if not self.primary_trader:
            return config.SYMBOLS

        try:
            # Parallel fetching of top symbols and positions
            # (Note: Assuming primary_trader methods will be made async in Stage 2.1)
            # For now, we wrap them in threads if they are still sync, 
            # but prepare for true async.
            
            top_market_symbols = await self.primary_trader.get_top_symbols(100)
            
            open_positions = []
            for t in self.traders.values():
                try:
                    pos = await t.get_positions()
                    open_positions.extend([p['symbol'] for p in pos])
                except: continue
                
            candidates = list(set(top_market_symbols + config.SYMBOLS + open_positions))
            logging.info(f"🔍 SCREENER: Identified {len(candidates)} total candidates.")
            return candidates
        except Exception as e:
            logging.error(f"❌ SCREENER DISCOVERY ERROR: {e}")
            return config.SYMBOLS

    async def _pre_screen_asset(self, symbol: str, open_positions: List[str]) -> Dict[str, Any]:
        """Fast technical scoring for a single asset (non-blocking)."""
        try:
            candles = await self.primary_trader.get_ohlcv(symbol, '1h', 30)
            if not candles: return None
            
            closes = [c[4] for c in candles]
            volumes = [c[5] for c in candles]
            
            rvol = tech_analysis.calculate_rvol(volumes)
            rsi = tech_analysis.calculate_rsi(closes)
            
            score = 0
            if symbol in open_positions: score += 5000 
            if symbol in config.SYMBOLS: score += 1000 
            
            if rvol > 1.5: score += 100 * rvol
            if rsi < 30 or rsi > 70: score += 50
            
            if score > 50:
                return {"symbol": symbol, "score": score}
            return None
        except: return None

    async def get_final_selection(self, limit: int = 10) -> List[str]:
        """Runs the screening process fully asynchronously."""
        candidates = await self.discover_candidates()
        
        # Collect open positions for scoring
        open_positions = []
        for t in self.traders.values():
            try:
                pos = await t.get_positions()
                open_positions.extend([p['symbol'] for p in pos])
            except: pass
            
        # True Async Parallel Execution
        tasks = [self._pre_screen_asset(s, open_positions) for s in candidates]
        raw_results = await asyncio.gather(*tasks)
        
        screened_results = [r for r in raw_results if r]
        screened_results.sort(key=lambda x: x['score'], reverse=True)
        final_symbols = [r['symbol'] for r in screened_results[:limit]]
        
        # Update UI Discoveries
        new_discoveries = [r['symbol'] for r in screened_results 
                          if r['symbol'] not in open_positions and r['symbol'] not in config.SYMBOLS]
        config.HOT_SYMBOLS = new_discoveries[:5]
        
        logging.info(f"✅ SCREENER: Parallel screening complete. Selection: {final_symbols}")
        return final_symbols
