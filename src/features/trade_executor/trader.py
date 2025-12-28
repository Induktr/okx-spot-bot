import ccxt
import logging
from src.app.config import config

class Trader:
    """
    Hands module for A.S.T.R.A.
    Universal Trader supporting OKX, Binance, Bybit.
    """
    def __init__(self, exchange_id='okx'):
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
                # New CCXT way for Binance Demo Trading (Futures)
                if hasattr(self.exchange, 'set_demo_trading'):
                    self.exchange.set_demo_trading(True, True) # (enabled, private_keys)
                    logging.info("Trader: Binance Demo Trading Enabled")
            elif hasattr(self.exchange, 'set_sandbox_mode'):
                self.exchange.set_sandbox_mode(True)
                logging.info(f"Trader: {exchange_id} Demo Mode Active")
            
            # Special header for OKX Demo
            if exchange_id == 'okx':
                self.exchange.headers = {'x-simulated-trading': '1'}

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

    def get_ticker(self, symbol):
        try:
            ticker = self.exchange.fetch_ticker(symbol)
            return ticker['last']
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


    def get_positions(self, target_symbol=None):
        try:
            positions = self.exchange.fetch_positions()
            if target_symbol:
                return [p for p in positions if p['symbol'] == target_symbol]
            return positions
        except Exception as e:
            logging.error(f"[{self.exchange_id}] Positions error: {e}")
            return []

    def execute_order(self, symbol, side, budget_usdt):
        """Unified order execution with manual contract calculation for Swaps."""
        side = side.upper()
        if side == "WAIT": return "WAIT"

        try:
            self.exchange.load_markets()
            market = self.exchange.market(symbol)
            current_price = self.get_ticker(symbol)
            if not current_price: return "Price Error"

            # Set Leverage
            try:
                self.exchange.set_leverage(self.leverage, symbol)
            except: pass

            # Calculate Contracts (sz)
            # Formula: (budget * leverage) / (contract_size * price)
            contract_size = float(market.get('contractSize', 1))
            total_nominal_value = budget_usdt * self.leverage
            raw_sz = total_nominal_value / (contract_size * current_price)
            
            # Floor to minimum lot size
            min_sz = float(market['limits']['amount']['min'] or 1)
            sz = max(min_sz, round(raw_sz / min_sz) * min_sz)

            logging.info(f"[{self.exchange_id}] Executing {side} on {symbol}. Budget ${budget_usdt} (x{self.leverage}) -> {sz} contracts.")
            
            if side == "BUY":
                return self.exchange.create_market_buy_order(symbol, sz)
            elif side == "SELL":
                return self.exchange.create_market_sell_order(symbol, sz)
                
        except Exception as e:
            logging.error(f"[{self.exchange_id}] Order Error: {e}")
            return str(e)


    def close_position(self, pos):
        try:
            symbol = pos['symbol']
            side = 'sell' if pos['side'] == 'long' else 'buy'
            amount = pos['contracts']
            logging.info(f"[{self.exchange_id}] Closing {symbol} {pos['side']}")
            return self.exchange.create_market_order(symbol, side, amount, {'reduceOnly': True})
        except Exception as e:
            logging.error(f"[{self.exchange_id}] Close Error: {e}")
            return str(e)

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
            side = pos['side']
            entry_price = float(pos['entryPrice'])
            contracts = pos['contracts']

            self.cancel_algo_orders(symbol)

            tp_price = entry_price * (1 + tp_pct) if side == 'long' else entry_price * (1 - tp_pct)
            sl_price = entry_price * (1 - sl_pct) if side == 'long' else entry_price * (1 + sl_pct)

            params = {
                'tdMode': 'cross',
                'ordType': 'conditional',
                'reduceOnly': True
            }

            logging.info(f"[{self.exchange_id}] Syncing TP/SL for {symbol}. SL: {sl_price:.2f}")

            # Take Profit
            self.exchange.create_order(
                symbol=symbol, type='market', side='sell' if side == 'long' else 'buy',
                amount=contracts, params={**params, 'tpTriggerPx': f"{tp_price:.2f}", 'tpOrdPx': '-1'}
            )
            # Stop Loss
            self.exchange.create_order(
                symbol=symbol, type='market', side='sell' if side == 'long' else 'buy',
                amount=contracts, params={**params, 'slTriggerPx': f"{sl_price:.2f}", 'slOrdPx': '-1'}
            )
            return "Synced"
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
