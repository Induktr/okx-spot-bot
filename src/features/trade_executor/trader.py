import ccxt.async_support as ccxt
import logging
import asyncio
from typing import List, Dict, Optional, Any, Union
from src.app.config import config
from src.shared.providers.db_provider import db_engine

class Trader:
    """
    Hands module for A.S.T.R.A. (Async Version)
    Universal Trader supporting OKX, Binance, Bybit via ccxt.async_support.
    """
    def __init__(self, exchange_id: str = 'okx'):
        self.exchange_id = exchange_id
        exchange_class = getattr(ccxt, exchange_id)
        
        keys = self._get_keys(exchange_id)
        
        self.exchange = exchange_class({
            'apiKey': keys['apiKey'],
            'secret': keys['secret'],
            'password': keys.get('password'),
            'enableRateLimit': True,
            'options': {'defaultType': 'swap'}
        })

        self.pos_mode = 'net_mode'
        self.is_demo = config.SANDBOX_MODES.get(exchange_id, False)

    async def initialize(self):
        """Async initialization: loading markets and detecting modes."""
        if self.is_demo:
            if self.exchange_id == 'binance':
                self.exchange.set_demo_trading(True)
                self.exchange.urls['api']['fapi'] = 'https://demo-fapi.binance.com'
                logging.info("Trader: Binance Demo Trading Active")
            elif hasattr(self.exchange, 'set_sandbox_mode'):
                self.exchange.set_sandbox_mode(True)
            
        if self.exchange_id == 'okx':
            if self.is_demo:
                self.exchange.headers['x-simulated-trading'] = '1'
            
            try:
                acc_config = await self.exchange.private_get_account_config()
                data = acc_config.get('data', [{}])
                if data:
                    self.pos_mode = data[0].get('posMode', 'net_mode')
            except: self.pos_mode = 'net_mode'

        await self.exchange.load_markets()
        logging.info(f"✅ ASYNC TRADER: [{self.exchange_id}] Ready. (Hedge: {self.pos_mode})")

    async def close(self):
        """Close exchange connection."""
        await self.exchange.close()

    def _get_keys(self, eid):
        if eid == 'binance':
            return {'apiKey': config.BINANCE_API_KEY, 'secret': config.BINANCE_SECRET}
        if eid == 'bybit':
            return {'apiKey': config.BYBIT_API_KEY, 'secret': config.BYBIT_SECRET}
        return {
            'apiKey': config.OKX_API_KEY, 
            'secret': config.OKX_SECRET, 
            'password': config.OKX_PASSWORD
        }

    async def get_balance(self):
        try:
            balance = await self.exchange.fetch_balance()
            total_equity = 0.0
            for coin in ['USDT', 'USDC', 'BUSD']:
                asset = balance.get(coin, {})
                val = asset.get('total', asset.get('free', 0.0))
                total_equity += float(val or 0)
            return total_equity
        except Exception as e:
            logging.error(f"[{self.exchange_id}] Balance error: {e}")
            return 0.0

    async def get_free_balance(self):
        try:
            balance = await self.exchange.fetch_balance()
            free_margin = 0.0
            for coin in ['USDT', 'USDC', 'BUSD']:
                asset = balance.get(coin, {})
                val = asset.get('free', 0.0)
                free_margin += float(val or 0)
            return free_margin
        except Exception as e:
            logging.error(f"[{self.exchange_id}] Free balance error: {e}")
            return 0.0

    async def get_ticker(self, symbol: str) -> Optional[float]:
        try:
            # 1. TRY WEBSOCKET FIRST (Idea 3 - Low Latency)
            from src.shared.providers.price_observer import price_observer
            ws_price = price_observer.get_price(symbol)
            if ws_price:
                return ws_price

            # 2. FALLBACK TO REST
            ticker = await self.exchange.fetch_ticker(symbol)
            if 'last' in ticker and ticker['last'] is not None:
                return float(ticker['last'])
            else:
                logging.warning(f"[{self.exchange_id}] Ticker for {symbol} returned no 'last' price.")
                return None
        except Exception as e:
            logging.error(f"[{self.exchange_id}] Ticker error for {symbol}: {e}")
            return None

    async def get_history(self, limit=100):
        try:
            return await self.exchange.fetch_my_trades(None, None, limit)
        except: return []

    async def get_ohlcv(self, symbol, timeframe='1h', limit=50):
        try:
            return await self.exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)
        except: return []

    async def get_top_symbols(self, limit=50) -> List[str]:
        try:
            tickers = await self.exchange.fetch_tickers()
            valid_tickers = []
            for symbol, ticker in tickers.items():
                if ':USDT' in symbol and ticker.get('quoteVolume'):
                    valid_tickers.append({'symbol': symbol, 'volume': float(ticker['quoteVolume'])})
            sorted_tickers = sorted(valid_tickers, key=lambda x: x['volume'], reverse=True)
            return [x['symbol'] for x in sorted_tickers[:limit]]
        except Exception as e:
            logging.error(f"[{self.exchange_id}] Failed to fetch top symbols: {e}")
            return []

    async def get_positions(self, target_symbol: Optional[str] = None) -> list[dict[str, Any]]:
        try:
            # Normalize target_symbol for OKX Swap consistency
            if target_symbol and self.exchange_id == 'okx' and ":USDT" not in target_symbol:
                target_symbol = f"{target_symbol}:USDT" if ":" not in target_symbol else f"{target_symbol.split(':')[0]}:USDT"

            positions = await self.exchange.fetch_positions()
            active_positions = [p for p in positions if float(p.get('contracts', 0)) > 0]
            if target_symbol:
                return [p for p in active_positions if p['symbol'] == target_symbol]
            return active_positions
        except Exception as e:
            logging.error(f"Trader Error: Failed to fetch positions: {e}")
            return []

    async def get_funding_rate(self, symbol):
        try:
            funding = await self.exchange.fetch_funding_rate(symbol)
            return float(funding.get('fundingRate', 0.0))
        except: return 0.0

    async def emergency_liquidate_all(self):
        try:
            positions = await self.get_positions()
            tasks = [self.close_position(p) for p in positions]
            return await asyncio.gather(*tasks)
        except Exception as e:
            logging.error(f"Critical: Emergency Liquidation Failed: {e}")
            return []

    async def execute_order(self, symbol, side, budget_usdt, leverage=3):
        side = side.upper()
        if side == "WAIT": return "WAIT"
        
        # Symbol Normalization for OKX Swap
        if self.exchange_id == 'okx' and ":USDT" not in symbol:
            symbol = f"{symbol}:USDT" if ":" not in symbol else f"{symbol.split(':')[0]}:USDT"

        try:
            market = self.exchange.market(symbol)
            current_price = await self.get_ticker(symbol)
            if not current_price: return "Price Error"

            await self.set_leverage(symbol, leverage, side='long' if side == "BUY" else "short")

            # Defensive float conversion for contract size
            raw_contract_size = market.get('contractSize')
            contract_size = float(raw_contract_size) if raw_contract_size is not None else 1.0
            
            sz = (budget_usdt * leverage) / (contract_size * current_price)
            sz_str = self.exchange.amount_to_precision(symbol, sz)
            
            if sz_str is None:
                return f"FAILED: Precision error for {symbol} (sz: {sz})"
            
            order_params = {'tdMode': 'cross'}
            
            # --- MONETIZATION: Broker Tag injection ---
            if self.exchange_id == 'okx' and config.OKX_BROKER_ID:
                order_params['tag'] = config.OKX_BROKER_ID
            
            if self.exchange_id == 'okx' and self.pos_mode == 'long_short_mode':
                order_params['posSide'] = 'long' if side == "BUY" else "short"

            if side == "BUY":
                res = await self.exchange.create_market_buy_order(symbol, float(sz_str), params=order_params)
            else:
                res = await self.exchange.create_market_sell_order(symbol, float(sz_str), params=order_params)
            
            # Sync Target State to DB
            db_engine.update_active_trade(symbol, side, sz, current_price, leverage)
            
            return f"SUCCESS: Order filled on {self.exchange_id.upper()}"
        except Exception as e:
            logging.error(f"Trader Error [{self.exchange_id}] on {symbol}: {e}")
            return f"FAILED: {str(e)[:100]}"

    async def set_leverage(self, symbol, leverage, side=None):
        try:
            params = {}
            if self.exchange_id == 'okx' and self.pos_mode == 'long_short_mode' and side:
                params['posSide'] = side.lower()
            await self.exchange.set_leverage(leverage, symbol, params)
            return f"LVG:{leverage}x"
        except: return "LVG:ERR"

    async def close_position(self, pos):
        symbol = pos['symbol']
        try:
            if self.exchange_id == 'okx':
                inst_id = pos.get('info', {}).get('instId') or self.exchange.market(symbol)['id']
                payload = {'instId': inst_id, 'mgnMode': pos.get('marginMode', 'cross')}
                
                # Monetization tag for Close orders too
                if config.OKX_BROKER_ID:
                    payload['tag'] = config.OKX_BROKER_ID
                    
                if pos.get('info', {}).get('posSide') in ['long', 'short']:
                    payload['posSide'] = pos['info']['posSide']
                res = await self.exchange.private_post_trade_close_position(payload)
                if str(res.get('code')) == '0': 
                    db_engine.close_active_trade(symbol)
                    return await self._verify_closure(symbol)
            
            side = 'sell' if pos.get('side') == 'long' else 'buy'
            await self.exchange.create_market_order(symbol, side, float(pos['contracts']), {'reduceOnly': True})
            return await self._verify_closure(symbol)
        except Exception as e:
            return f"FAILED: {str(e)[:50]}"

    async def _verify_closure(self, symbol):
        for _ in range(5):
            await asyncio.sleep(0.5)
            if not await self.get_positions(target_symbol=symbol): return "CLOSED"
        return "SENT (Pending)"

    async def execute_flip(self, symbol, current_pos, target_decision, budget_usdt, leverage=3):
        res = await self.close_position(current_pos)
        if "CLOSED" not in res: return f"FLIP ABORTED: {res}"
        await asyncio.sleep(1)
        return await self.execute_order(symbol, target_decision, budget_usdt, leverage)

    async def sync_sl_tp(self, pos, tp_pct=0.3, sl_pct=0.1):
        if self.exchange_id != 'okx': return "Skipped"
        try:
            symbol, side = pos['symbol'], pos['side']
            # Normalize pct
            if tp_pct > 0.5: tp_pct = tp_pct / 100.0
            if sl_pct > 0.5: sl_pct = sl_pct / 100.0

            raw_entry = pos.get('entryPrice') or pos.get('info', {}).get('avgPx')
            raw_contracts = pos.get('contracts', 0) or pos.get('info', {}).get('pos', 0)
            
            if not raw_entry or float(raw_contracts) == 0:
                return "ERR: Position data incomplete"

            entry_price, contracts = float(raw_entry), abs(float(raw_contracts))
            
            # Fetch Current Ticker for Trailing Check
            last_price = await self.get_ticker(symbol)
            if last_price is None: return "ERR: Ticker unavailable"
            
            # Calculate Current PnL %
            current_pnl_pct = (last_price - entry_price) / entry_price if side == 'long' else (entry_price - last_price) / entry_price
            
            # --- Trailing Stop-Loss Logic (v1.5.1) ---
            final_sl_price = entry_price * (1 - sl_pct) if side == 'long' else entry_price * (1 + sl_pct)
            
            if config.TRAILING_STOP_ACTIVE and current_pnl_pct >= config.TRAILING_STOP_CALLBACK_PCT:
                # Dynamic SL at distance from peak
                ts_sl = last_price * (1 - config.TRAILING_STOP_DISTANCE_PCT) if side == 'long' else last_price * (1 + config.TRAILING_STOP_DISTANCE_PCT)
                
                # Ensure we never move SL back into loss if we are already in profit
                if side == 'long':
                    final_sl_price = max(ts_sl, final_sl_price, entry_price)
                else:
                    final_sl_price = min(ts_sl, final_sl_price, entry_price)
                
                logging.info(f"🛡️ Trailing SL Active for {symbol}: Moving SL to {final_sl_price:.2f} (Breakeven+) ")

            tp_price = entry_price * (1 + tp_pct) if side == 'long' else entry_price * (1 - tp_pct)
            
            # Cancel existing conditional orders for this symbol to avoid duplicates
            try:
                await self.exchange.cancel_all_orders(symbol, params={'unfilledOnly': True, 'stop': True})
            except: pass

            p: Dict[str, Any] = {'tdMode': 'cross', 'ordType': 'conditional'}
            if config.OKX_BROKER_ID: p['tag'] = config.OKX_BROKER_ID
            if self.pos_mode == 'long_short_mode': p['posSide'] = side
            else: p['reduceOnly'] = True

            # TP Execution
            tp_px_str = self.exchange.price_to_precision(symbol, tp_price)
            await self.exchange.create_order(symbol, 'market', 'sell' if side == 'long' else 'buy', contracts, params={**p, 'tpTriggerPx': tp_px_str, 'tpOrdPx': '-1'})
            
            # SL Execution (Dynamic)
            sl_px_str = self.exchange.price_to_precision(symbol, final_sl_price)
            await self.exchange.create_order(symbol, 'market', 'sell' if side == 'long' else 'buy', contracts, params={**p, 'slTriggerPx': sl_px_str, 'slOrdPx': '-1'})
            
            return "SYNCED_TRAILING" if current_pnl_pct >= config.TRAILING_STOP_CALLBACK_PCT else "SYNCED"
        except Exception as e:
            logging.error(f"Sync SL/TP Error: {e}")
            return "ERR"

# Global Async Trader Manager
traders: Dict[str, Trader] = {}

class TraderProxy:
    """A proxy that always points to the first active trader in the pool."""
    def __getattr__(self, name):
        if not traders:
            raise RuntimeError("No active traders found. Call refresh_traders() first.")
        # Return first available trader
        return getattr(list(traders.values())[0], name)

trader = TraderProxy()

async def refresh_traders():
    global traders
    logging.info(f"🔄 ASYNC TRADER: Refreshing {config.ACTIVE_EXCHANGES}")
    # Close old ones
    for t in traders.values(): await t.close()
    traders.clear()
    # Init new ones in parallel
    new_traders = [Trader(eid) for eid in config.ACTIVE_EXCHANGES]
    await asyncio.gather(*[t.initialize() for t in new_traders])
    for t in new_traders: traders[t.exchange_id] = t

# Initial sync refresh (legacy support)
# In true async app, this should be called by the event loop.
