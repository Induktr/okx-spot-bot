import asyncio
import json
import logging
import websockets
from typing import Dict, Optional

class PriceObserver:
    """
    Core Engine Infrastructure (Idea 3).
    High-speed WebSocket price observer for OKX.
    Ensures real-time price updates for TSL and Risk Management without REST latency.
    """
    def __init__(self):
        self._price_cache: Dict[str, float] = {}
        self._running = False
        self._ws_url = "wss://wspap.okx.com:8443/ws/v5/public" # Demo/Public
        self._symbols = ["BTC-USDT-SWAP", "ETH-USDT-SWAP", "SOL-USDT-SWAP"]
        logging.info("🚀 WS OBSERVER: Starting engine...")

    async def start(self):
        self._running = True
        asyncio.create_task(self._main_loop())

    async def _main_loop(self):
        while self._running:
            try:
                async with websockets.connect(self._ws_url) as ws:
                    # Subscribe to tickers
                    subscribe_msg = {
                        "op": "subscribe",
                        "args": [{"channel": "tickers", "instId": s} for s in self._symbols]
                    }
                    await ws.send(json.dumps(subscribe_msg))
                    logging.info(f"🚀 WS OBSERVER: Subscribed to {self._symbols}")

                    while self._running:
                        msg = await ws.recv()
                        data = json.loads(msg)
                        
                        if "data" in data:
                            for tick in data["data"]:
                                symbol = tick["instId"].replace("-SWAP", "").replace("-", "/") + ":USDT"
                                self._price_cache[symbol] = float(tick["last"])
            except Exception as e:
                logging.error(f"❌ WS OBSERVER ERROR: {e}. Reconnecting in 5s...")
                await asyncio.sleep(5)

    def get_price(self, symbol: str) -> Optional[float]:
        # Normalize symbol for cache lookup
        # OKX format in Trader is symbols like 'BTC/USDT:USDT'
        return self._price_cache.get(symbol)

# Global Observer
price_observer = PriceObserver()
