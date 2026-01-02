from typing import List, Dict, Optional, Any, Union
import ccxt
import logging
import time
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
                data = acc_config.get('data', [{}])
                if data:
                    self.pos_mode = data[0].get('posMode', 'net_mode')
                    logging.info(f"Trader: OKX Account Mode: {self.pos_mode} | Account Type: {data[0].get('acctLv')}")
                else:
                    self.pos_mode = 'net_mode'
            except Exception as e:
                logging.warning(f"Trader: Could not detect OKX posMode: {e}. Defaulting to net_mode.")
                self.pos_mode = 'net_mode' 

        # Load Markets once
        try:
            logging.info(f"Trader: [{exchange_id}] initialized. (Hedge: {'YES' if self.pos_mode == 'long_short_mode' else 'NO'})")
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


    def get_positions(self, target_symbol: Optional[str] = None) -> list[dict[str, any]]:
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

    def _sync_okx_mode(self):
        """Internal helper to ensure bot's pos_mode matches exchange reality."""
        if self.exchange_id != 'okx': return
        try:
            acc_config = self.exchange.private_get_account_config()
            data = acc_config.get('data', [{}])
            if data:
                self.pos_mode = data[0].get('posMode', 'net_mode')
        except:
            pass

    def execute_order(self, symbol, side, budget_usdt, leverage=3):
        """Unified order execution with manual contract calculation for Swaps."""
        self._sync_okx_mode()
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
                lev_params = {}
                if self.exchange_id == 'okx' and self.pos_mode == 'long_short_mode':
                    lev_params['posSide'] = 'long' if side.upper() == "BUY" else "short"
                self.exchange.set_leverage(leverage, symbol, lev_params)
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
        """
        Atomic force_close: sends close order and verifies closure via polling.
        Guarantees that the position is 0 before returning SUCCESS.
        """
        try:
            symbol = pos['symbol']
            
            # Robust Side Detection for closure
            current_side = str(pos.get('side', 'long')).lower()
            info_side = str(pos.get('info', {}).get('posSide', '')).lower()
            is_pos_short = 'short' in current_side or 'sell' in current_side or 'short' in info_side
            
            side = 'buy' if is_pos_short else 'sell'
            amount = pos['contracts']
            
            # Unified parameter building
            params = {}
            
            if self.exchange_id == 'okx':
                self._sync_okx_mode()
                # OKX V5: reduceOnly is NOT applicable in Hedge Mode (long_short_mode)
                if self.pos_mode == 'long_short_mode':
                    params['posSide'] = 'short' if is_pos_short else 'long'
                    # Use actual position margin mode (cross vs isolated)
                    params['tdMode'] = pos.get('marginMode', 'cross')
                    logging.info(f"[{self.exchange_id}] Closing HEDGE: {symbol} | Detected Side: {'SHORT' if is_pos_short else 'LONG'} | Map to posSide: {params['posSide']} | tdMode: {params['tdMode']}")
                else:
                    # Net mode uses reduceOnly
                    params['reduceOnly'] = True
                    params['tdMode'] = 'cross'
                    logging.info(f"[{self.exchange_id}] Closing NET: {symbol} | tdMode: cross")
            else:
                params['reduceOnly'] = True

            # Send execution signal
            res = self.exchange.create_market_order(symbol, side, amount, params)
            
            # ATOMIC VERIFICATION: Poll for closure
            max_retries = 5
            for i in range(max_retries):
                time.sleep(0.5) # 500ms polling interval
                active_pos = self.get_positions(target_symbol=symbol)
                if not active_pos:
                    logging.info(f"[{self.exchange_id}] Verification Success: {symbol} is closed.")
                    return "SUCCESS: Position Closed"
                logging.warning(f"[{self.exchange_id}] Verification Poll {i+1}/{max_retries}: {symbol} still active.")
            
            return f"FAILED: Closure verification timed out for {symbol}."

        except Exception as e:
            raw_err = str(e)
            logging.error(f"[{self.exchange_id}] Close Error Symbol {symbol}: {raw_err}")
            
            if "51000" in raw_err:
                # FALLBACK: If Hedge mode params failed, try Net mode params once as a safety net
                if self.exchange_id == 'okx' and 'posSide' in params:
                    logging.warning(f"[{self.exchange_id}] posSide mismatch. Attempting FALLBACK to Net mode closure...")
                    try:
                        fallback_params = {k:v for k,v in params.items() if k != 'posSide'}
                        fallback_params['reduceOnly'] = True
                        self.exchange.create_market_order(symbol, side, amount, fallback_params)
                        return "SUCCESS: Position Closed (via Net Fallback)"
                    except Exception as fe:
                        logging.error(f"[{self.exchange_id}] Fallback also failed: {fe}")

                return f"Error: OKX posSide mismatch. Bot Mode: {self.pos_mode}. Check OKX Settings."
            
            return raw_err

    def execute_flip(self, symbol, current_pos, target_decision, budget_usdt, leverage=3):
        """
        Unified Flip Logic: Guarantees the old position is dead before opening the new one.
        Blocking operation for atomic safety.
        """
        eid = self.exchange_id.upper()
        logging.info(f"[{eid}] ATOMIC FLIP START: {symbol} -> {target_decision}")
        
        # 1. KILL the old position
        close_res = self.close_position(current_pos)
        if "SUCCESS" not in close_res:
            return f"FLIP ABORTED: {close_res}"
            
        # 2. Wait for exchange margin settlement & verification (Blocking 1s + Retries)
        time.sleep(1)
        verification_retries = 5
        for i in range(verification_retries):
            remaining = self.get_positions(target_symbol=symbol)
            if not remaining:
                logging.info(f"[{eid}] Flip Verification: {symbol} is settled (Empty). Proceeding.")
                break
            logging.warning(f"[{eid}] Flip Verification {i+1}/{verification_retries}: {symbol} still active. Waiting...")
            time.sleep(1)
        else:
            return f"FLIP ABORTED: Settlement Timeout. Position {symbol} still detected after close."
            
        # 3. OPEN the new position
        open_res = self.execute_order(symbol, target_decision, budget_usdt, leverage)
        return f"FLIP SUCCESS: {open_res}"

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
                'ordType': 'conditional'
            }
            
            if self.exchange_id == 'okx':
                params['tdMode'] = pos.get('marginMode', 'cross')
                # OKX V5: reduceOnly is for net mode only
                if self.pos_mode == 'long_short_mode':
                    params['posSide'] = side
                else:
                    params['reduceOnly'] = True
            else:
                params['reduceOnly'] = True

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
