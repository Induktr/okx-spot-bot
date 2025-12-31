from typing import List, Dict, Optional, Any, Union
import ccxt
import logging
from src.app.config import config

class Trader:
    """
    Hands module for A.S.T.R.A.
    Universal Trader supporting OKX, Binance, Bybit.
    """
    def __init__(self, exchange_id: str = 'okx'):
        self.exchange_id = exchange_id
        exchange_class = getattr(ccxt, exchange_id)
        
        # Select correct keys based on ID
        keys = self._get_keys(exchange_id)
        
        self.exchange = exchange_class({
            'apiKey': keys['apiKey'],
            'secret': keys['secret'],
            'password': keys.get('password'),
            'enableRateLimit': True,
            'options': {'defaultType': 'swap'}
        })

        self.pos_mode = 'net_mode'
        self.leverage = 3

        # Check individual sandbox mode for this exchange
        is_demo = config.SANDBOX_MODES.get(exchange_id, False)

        if is_demo:
            if exchange_id == 'binance':
                # Force Binance Demo Trading (Futures)
                self.exchange.set_demo_trading(True)
                self.exchange.urls['api']['fapi'] = 'https://demo-fapi.binance.com'
                self.exchange.options['defaultType'] = 'future'
                logging.info("Trader: Binance Demo Trading Forced (fapi)")
            elif hasattr(self.exchange, 'set_sandbox_mode'):
                self.exchange.set_sandbox_mode(True)
                logging.info(f"Trader: {exchange_id} Demo Mode Active")
            
        if exchange_id == 'okx':
            self.exchange.options['defaultType'] = 'swap'
            if is_demo:
                self.exchange.headers['x-simulated-trading'] = '1'
            
            # Detect Position Mode (Net vs Long/Short) - Required for both Live and Demo
            try:
                acc_config = self.exchange.private_get_account_config()
                self.pos_mode = acc_config.get('data', [{}])[0].get('posMode', 'net_mode')
                logging.info(f"Trader: OKX Account Mode detected: {self.pos_mode}")
            except Exception as e:
                logging.warning(f"Trader: Could not detect OKX posMode: {e}. Defaulting to safest.")
                # If we have existing positions, we can try to guess or use a safer default
                self.pos_mode = 'long_short_mode' 

        # Load Markets once
        try:
            self.exchange.load_markets()
        except Exception as e:
            logging.error(f"Trader: Failed to load markets for {exchange_id}: {e}")

    def _get_keys(self, eid):
        if eid == 'binance':
            return {'apiKey': config.BINANCE_API_KEY, 'secret': config.BINANCE_SECRET}
        if eid == 'bybit':
            return {'apiKey': config.BYBIT_API_KEY, 'secret': config.BYBIT_SECRET}
        # Default OKX
        return {
            'apiKey': config.OKX_API_KEY, 
            'secret': config.OKX_SECRET, 
            'password': config.OKX_PASSWORD
        }

    def get_balance(self):
        """Fetches total equity in stablecoins (USDT/USDC/BUSD)."""
        try:
            balance = self.exchange.fetch_balance()
            total_equity = 0.0
            
            # Sum up major stablecoins
            for coin in ['USDT', 'USDC', 'BUSD']:
                asset = balance.get(coin, {})
                # For Futures/Swap, we usually want 'total' (equity)
                # Fallback to 'free' if total is missing, then 0.0
                val = asset.get('total', asset.get('free', 0.0))
                total_equity += float(val or 0)
            
            if total_equity == 0:
                logging.warning(f"[{self.exchange_id}] Balance is 0.0. Check your API keys and permissions.")
                
            return total_equity
        except Exception as e:
            logging.error(f"[{self.exchange_id}] Balance error: {e}")
            return 0.0

    def get_free_balance(self):
        """Fetches available (free) margin in stablecoins (USDT/USDC/BUSD)."""
        try:
            balance = self.exchange.fetch_balance()
            free_margin = 0.0
            for coin in ['USDT', 'USDC', 'BUSD']:
                asset = balance.get(coin, {})
                # For OKX/Binance, 'free' is what we can use for new orders
                val = asset.get('free', 0.0)
                free_margin += float(val or 0)
            return free_margin
        except Exception as e:
            logging.error(f"[{self.exchange_id}] Free balance error: {e}")
            return 0.0

    def get_ticker(self, symbol: str) -> Optional[float]:
        try:
            ticker = self.exchange.fetch_ticker(symbol)
            return float(ticker['last'])
        except Exception as e:
            logging.error(f"[{self.exchange_id}] Ticker error: {e}")
            return None

    def get_ohlcv(self, symbol, timeframe='1h', limit=50):
        try:
            return self.exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)
        except Exception as e:
            logging.error(f"[{self.exchange_id}] OHLCV error: {e}")
            return []

    def get_history(self, limit=20):
        try:
            trades = self.exchange.fetch_my_trades(limit=limit)
            return trades if trades is not None else []
        except Exception as e:
            logging.error(f"[{self.exchange_id}] History error: {e}")
            return []


    def get_positions(self, target_symbol: Optional[str] = None) -> List[Dict[str, Any]]:
        try:
            # fetch_positions can return closed positions (0 contracts) on some exchanges
            positions = self.exchange.fetch_positions()
            active_positions = [p for p in positions if float(p.get('contracts', 0)) > 0]
            
            if target_symbol:
                return [p for p in active_positions if p['symbol'] == target_symbol]
            return active_positions
        except Exception as e:
            logging.error(f"[{self.exchange_id}] Positions error: {e}")
            return []

    def get_funding_rate(self, symbol):
        """Fetches the current funding rate for a swap/future."""
        try:
            # Note: Not all exchanges support this standard method, but major ones do.
            funding = self.exchange.fetch_funding_rate(symbol)
            return float(funding.get('fundingRate', 0.0))
        except Exception as e:
            return 0.0

    # --- Feature 3: Adaptive Risk Engine ---
    def calculate_adaptive_leverage(self, symbol, base_leverage):
        """
        Dynamically adjusts leverage based on market volatility and bot performance.
        Reduces leverage if a Black Swan event or high volatility is detected.
        """
        try:
            ohlcv = self.get_ohlcv(symbol, timeframe='1h', limit=2)
            if len(ohlcv) < 2: return base_leverage
            
            # Simple 1h volatility check
            close_prev = ohlcv[0][4]
            close_curr = ohlcv[1][4]
            move_pct = abs(close_curr - close_prev) / close_prev
            
            adjusted = base_leverage
            if move_pct > config.VOLATILITY_THRESHOLD:
                # High volatility: Safety first, cut leverage in half
                adjusted = max(config.MIN_LEVERAGE, int(base_leverage * 0.5))
                logging.warning(f"[{self.exchange_id}] High Volatility Detected ({move_pct:.2%}). Adaptive Risk scaling leverage {base_leverage}x -> {adjusted}x")
            
            return min(adjusted, config.MAX_LEVERAGE)
        except:
            return base_leverage

    # --- Feature 6: Black Swan Insurance ---
    def emergency_liquidate_all(self):
        """Force closes all positions immediately across this exchange."""
        try:
            positions = self.get_positions()
            results = []
            for p in positions:
                logging.warning(f"🚨 EMERGENCY LIQUIDATION: Closing {p['symbol']}")
                res = self.close_position(p)
                results.append(res)
            return results
        except Exception as e:
            logging.error(f"Critical: Emergency Liquidation Failed: {e}")
            return []
            # logging.debug(f"[{self.exchange_id}] Funding Rate not available: {e}") 
            return 0.0

    def execute_order(self, symbol, side, budget_usdt, leverage=3):
        """Unified order execution with manual contract calculation for Swaps."""
        side = side.upper()
        if side == "WAIT": return "WAIT"

        try:
            self.exchange.load_markets()
            
            # Robust Symbol Check: If AI returns just 'BTC' or 'BTCUSDT'
            if symbol not in self.exchange.markets:
                found = False
                # Try common formats and case-insensitive search
                search_term = symbol.split('/')[0].upper()
                alternatives = [f"{search_term}/USDT:USDT", f"{search_term}/USDT", search_term]
                
                # Broad search in markets
                for m_id, m_info in self.exchange.markets.items():
                    if search_term in m_id.upper() and (':USDT' in m_id or '-SWAP' in m_id):
                        logging.info(f"[{self.exchange_id}] Deep normalizing symbol: {symbol} -> {m_id}")
                        symbol = m_id
                        found = True
                        break
                
                if not found:
                    for alt in alternatives:
                        if alt in self.exchange.markets:
                            logging.info(f"[{self.exchange_id}] Normalizing symbol: {symbol} -> {alt}")
                            symbol = alt
                            found = True
                            break
                            
                if not found:
                    return f"Symbol Error: {symbol} not found on {self.exchange_id}. (Note: Rebranded assets like FET/RNDR might be ASI/RENDER)"

            market = self.exchange.market(symbol)
            current_price = self.get_ticker(symbol)
            if not current_price: return "Price Error"

            # Set Leverage (Adaptive)
            leverage = self.calculate_adaptive_leverage(symbol, leverage)
            try:
                self.exchange.set_leverage(leverage, symbol)
            except: pass

            # PRE-FLIGHT CHECK: Free Margin Check
            free_balance = self.get_free_balance()
            if free_balance < budget_usdt:
                return f"Margin Error: Required {budget_usdt} USDT but only have {free_balance:.2f} USDT free available. (Total Equity: {self.get_balance():.2f})"

            # Calculate Contracts (sz)
            # Formula: (budget * leverage) / (contract_size * price)
            contract_size = float(market.get('contractSize', 1))
            total_nominal_value = budget_usdt * leverage
            raw_sz = total_nominal_value / (contract_size * current_price)
            
            # Floor to minimum lot size and apply exchange precision
            min_sz = float(market['limits']['amount']['min'] or 1)
            sz = max(min_sz, round(raw_sz / min_sz) * min_sz)
            
            # Use CCXT's amount_to_precision to satisfy exchange requirements
            sz_str = self.exchange.amount_to_precision(symbol, sz)
            sz = float(sz_str)

            logging.info(f"[{self.exchange_id}] Executing {side} on {symbol}. Budget ${budget_usdt} (x{leverage}) -> {sz} ({sz_str}) contracts.")
            
            # OKX Specific: Explicitly set tdMode and posSide if in Hedge mode
            order_params = {}
            if self.exchange_id == 'okx':
                order_params = {
                    'tdMode': 'cross'
                }
                # Handle Hedge Mode (long_short_mode)
                if self.pos_mode == 'long_short_mode':
                    # When opening a new position, we must specify which side we are opening
                    order_params['posSide'] = 'long' if side.upper() == "BUY" else "short"

            if side == "BUY":
                res = self.exchange.create_market_buy_order(symbol, sz, params=order_params)
            elif side == "SELL":
                res = self.exchange.create_market_sell_order(symbol, sz, params=order_params)
                
            return self._parse_execution_result(res)
                
        except Exception as e:
            return self._parse_execution_result(str(e))

    def _parse_execution_result(self, res):
        """Converts raw exchange responses into crystalline human-readable summaries."""
        res_str = str(res)
        
        # OKX Error Code Mapping
        if "51008" in res_str: return "FAILED: Insufficient USDT Margin (Account Empty)"
        if "51000" in res_str: return "FAILED: posSide Parameter Error (Hedge Mode Conflict)"
        if "51119" in res_str: return "FAILED: Leverage too high for position size"
        if "51001" in res_str: return "FAILED: Instrument not tradable (Check Symbol)"
        
        # Success check
        if isinstance(res, dict) and (res.get('id') or res.get('clOrdId') or res.get('status') == 'open'):
            return f"SUCCESS: Order #{res.get('id', 'N/A')} filled on {self.exchange_id.upper()}"
            
        return f"SYSTEM LOG: {res_str[:150]}..." if len(res_str) > 150 else f"SYSTEM LOG: {res_str}"


    def close_position(self, pos):
        try:
            symbol = pos['symbol']
            side = 'sell' if pos['side'] == 'long' else 'buy'
            amount = pos['contracts']
            
            # OKX requires posSide and tdMode even for closing in specific account modes
            params = {
                'reduceOnly': True
            }
            
            if self.exchange_id == 'okx':
                params['tdMode'] = 'cross'
                if self.pos_mode == 'long_short_mode':
                    # CRITICAL: For OKX Hedge Mode, posSide MUST be provided and must match 
                    # the side of the position being closed (long or short).
                    # We normalize this to ensure it's always lowercase 'long' or 'short'.
                    raw_side = pos.get('side', 'long')
                    params['posSide'] = 'long' if 'long' in raw_side.lower() else 'short'
                    
            logging.info(f"[{self.exchange_id}] Closing {symbol} {pos['side']} | Params: {params}")
            return self.exchange.create_market_order(symbol, side, amount, params)
        except Exception as e:
            err = str(e)
            if "51000" in err:
                return "Error: OKX posSide mismatch. Ensure Account is in Hedge Mode."
            logging.error(f"[{self.exchange_id}] Close Error: {err}")
            return err

    def cancel_algo_orders(self, symbol):
        """Cancels pending algo orders specifically for OKX."""
        if self.exchange_id != 'okx': return
        try:
            market = self.exchange.market(symbol)
            inst_id = market['id']
            pending = self.exchange.private_get_trade_orders_algo_pending({
                'instId': inst_id, 'ordType': 'conditional'
            })
            orders = pending.get('data', [])
            cancel_list = [{'algoId': o['algoId'], 'instId': o['instId']} for o in orders]
            if cancel_list:
                return self.exchange.private_post_trade_cancel_algos(cancel_list)
        except Exception as e:
            logging.warning(f"[{self.exchange_id}] Cancel Algos error: {e}")

    def sync_sl_tp(self, pos, tp_pct=0.3, sl_pct=0.2):
        """Sets protective TP/SL orders."""
        if self.exchange_id != 'okx':
            logging.info(f"[{self.exchange_id}] TP/SL skip (not implemented for this exchange yet)")
            return "Skipped"

        try:
            symbol = pos['symbol']
            side = pos['side'] # 'long' or 'short'
            entry_price = float(pos['entryPrice'])
            contracts = pos['contracts']

            self.cancel_algo_orders(symbol)

            tp_price = entry_price * (1 + tp_pct) if side == 'long' else entry_price * (1 - tp_pct)
            sl_price = entry_price * (1 - sl_pct) if side == 'long' else entry_price * (1 + sl_pct)
            
            # Format prices according to exchange precision
            tp_str = self.exchange.price_to_precision(symbol, tp_price)
            sl_str = self.exchange.price_to_precision(symbol, sl_price)

            params = {
                'tdMode': 'cross',
                'ordType': 'conditional',
                'reduceOnly': True
            }
            
            # Critical FIX for Hedge Mode
            if self.pos_mode == 'long_short_mode':
                params['posSide'] = side # Must match the position we are protecting

            logging.info(f"[{self.exchange_id}] Syncing TP/SL for {symbol} ({side}). TP: {tp_str}, SL: {sl_str}")

            # Take Profit (Market-Conditional)
            # OKX via CCXT uses tpTriggerPx and tpOrdPx
            self.exchange.create_order(
                symbol=symbol, type='market', side='sell' if side == 'long' else 'buy',
                amount=contracts, params={
                    **params, 
                    'tpTriggerPx': tp_str, 
                    'tpOrdPx': '-1' # -1 means market order on trigger
                }
            )
            # Stop Loss (Market-Conditional)
            self.exchange.create_order(
                symbol=symbol, type='market', side='sell' if side == 'long' else 'buy',
                amount=contracts, params={
                    **params, 
                    'slTriggerPx': sl_str, 
                    'slOrdPx': '-1'
                }
            )
            return f"Synced (SL:{sl_str})"
        except Exception as e:
            logging.error(f"[{self.exchange_id}] TP/SL Error: {e}")
            return str(e)
# Initialize traders collection
traders = {}

def refresh_traders():
    global traders, trader
    logging.info(f"Trader System: Refreshing exchanges... Active: {config.ACTIVE_EXCHANGES}")
    traders.clear()
    for eid in config.ACTIVE_EXCHANGES:
        try:
            traders[eid] = Trader(eid)
        except Exception as e:
            logging.error(f"Failed to initialize {eid}: {e}")
    
    # Legacy support
    if traders:
        trader = traders[config.ACTIVE_EXCHANGES[0]]

# Initial call
refresh_traders()
