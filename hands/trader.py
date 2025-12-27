import ccxt
import logging
from core.config import config

class Trader:
    """
    Hands module for A.S.T.R.A.
    Interacts with OKX via CCXT in Demo mode.
    """
    def __init__(self):
        self.exchange = ccxt.okx({
            'apiKey': config.OKX_API_KEY,
            'secret': config.OKX_SECRET,
            'password': config.OKX_PASSWORD,
            'enableRateLimit': True,
        })
        self.pos_mode = 'net_mode' 
        self.acct_lv = '1' 
        self.leverage = 3 # Default leverage for safety
        
        # Always fetch real account config on startup
        try:
            account_config = self.exchange.private_get_account_config()
            config_data = account_config.get('data', [{}])[0]
            self.acct_lv = config_data.get('acctLv', '1')
            self.pos_mode = config_data.get('posMode', 'net_mode')
            logging.info(f"Trader: OKX Account Mode: {self.acct_lv}, Position Mode: {self.pos_mode}")
        except Exception as e:
            logging.warning(f"Trader: Could not fetch account configuration: {e}")

        if config.USE_SANDBOX:
            self.exchange.set_sandbox_mode(True)
            self.exchange.headers = {
                'x-simulated-trading': '1'
            }
            logging.info("Trader: OKX Sandbox mode enabled with headers.")

    def get_balance(self):
        """Fetches account balance for USDT."""
        try:
            balance = self.exchange.fetch_balance()
            return balance.get('USDT', {}).get('free', 0.0)
        except Exception as e:
            logging.error(f"Balance fetch error: {e}")
            return 0.0

    def get_ticker(self, symbol):
        """Fetches current market price for the symbol."""
        try:
            ticker = self.exchange.fetch_ticker(symbol)
            return ticker['last']
        except Exception as e:
            logging.error(f"Ticker fetch error: {e}")
            return None

    def get_positions(self, target_symbol=None):
        """Fetches all open positions on the account."""
        try:
            positions = self.exchange.fetch_positions()
            if target_symbol:
                return [p for p in positions if p['symbol'] == target_symbol]
            return positions
        except Exception as e:
            logging.error(f"Positions fetch error: {e}")
            return []

    def close_position(self, pos):
        """
        Closes a specific position.
        pos: The position object from fetch_positions()
        """
        try:
            symbol = pos['symbol']
            side = 'sell' if pos['side'] == 'long' else 'buy'
            amount = pos['contracts']
            
            # OKX V5 parameters for closing
            td_mode = 'cash' if self.acct_lv == '1' else 'cross'
            params = {
                'tdMode': td_mode,
                'reduceOnly': True
            }
            if self.pos_mode == 'long_short_mode':
                params['posSide'] = pos['posSide']
            
            logging.info(f"Trader: Closing position {symbol} {pos['side']} (Amount: {amount})")
            return self.exchange.create_market_order(symbol, side, amount, params)
        except Exception as e:
            logging.error(f"Close position error: {e}")
            return str(e)

    def cancel_algo_orders(self, symbol):
        """
        Cancels all pending algo orders (TP/SL) for a specific symbol.
        """
        try:
            # We need the EXCHANGE-SPECIFIC instId (e.g., BTC-USDT-SWAP)
            # CCXT's market() method gives us the correct ID.
            market = self.exchange.market(symbol)
            inst_id = market['id']
            
            logging.info(f"Trader: Checking pending algo orders for {inst_id}...")
            
            pending = self.exchange.private_get_trade_orders_algo_pending({
                'instId': inst_id,
                'ordType': 'conditional'
            })
            
            orders = pending.get('data', [])
            if not orders:
                return "No algo orders to cancel."
                
            cancel_list = []
            for o in orders:
                cancel_list.append({
                    'algoId': o['algoId'],
                    'instId': o['instId']
                })
            
            if cancel_list:
                logging.info(f"Trader: Canceling {len(cancel_list)} existing algo orders...")
                return self.exchange.private_post_trade_cancel_algos(cancel_list)
        except Exception as e:
            logging.warning(f"Trader: Cancel Algos error: {e}")
            return str(e)

    def sync_sl_tp(self, pos, tp_pct=0.3, sl_pct=0.2):
        """
        Sets or updates Take Profit and Stop Loss for an existing position.
        Prevents duplicates by canceling old ones first.
        """
        try:
            symbol = pos['symbol']
            side = pos['side'] # 'long' or 'short'
            entry_price = float(pos['entryPrice'])
            contracts = pos['contracts']
            
            # 0. Clean up old orders FIRST to prevent duplication
            self.cancel_algo_orders(symbol)
            
            if side == 'long':
                tp_price = entry_price * (1 + tp_pct)
                sl_price = entry_price * (1 - sl_pct)
            else:
                tp_price = entry_price * (1 - tp_pct)
                sl_price = entry_price * (1 + sl_pct)
            
            # Identify market type for tdMode
            self.exchange.load_markets()
            market = self.exchange.market(symbol)
            m_type = market.get('type', 'swap')

            # Match tdMode logic with working execute_order
            td_mode = 'cash' if (self.acct_lv == '1' and m_type == 'spot') else 'cross'

            logging.info(f"Trader: Syncing Hard TP/SL for {symbol}. TP: {tp_price:.2f}, SL: {sl_price:.2f}")
            
            common_params = {
                'tdMode': td_mode,
                'ordType': 'conditional',
                'reduceOnly': True # Protective orders for existing positions SHOULD be True
            }

            if self.pos_mode == 'long_short_mode':
                pos_side = pos.get('posSide') or pos.get('info', {}).get('posSide')
                if pos_side:
                    common_params['posSide'] = pos_side

            # 1. Place Take Profit Order
            tp_params = {**common_params, 'tpTriggerPx': f"{tp_price:.2f}", 'tpOrdPx': '-1'}
            tp_res = self.exchange.create_order(
                symbol=symbol, type='market', side='sell' if side == 'long' else 'buy',
                amount=contracts, params=tp_params
            )
            
            # 2. Place Stop Loss Order
            sl_params = {**common_params, 'slTriggerPx': f"{sl_price:.2f}", 'slOrdPx': '-1'}
            sl_res = self.exchange.create_order(
                symbol=symbol, type='market', side='sell' if side == 'long' else 'buy',
                amount=contracts, params=sl_params
            )
            
            return {"tp": tp_res.get('id'), "sl": sl_res.get('id')}

        except Exception as e:
            logging.error(f"Sync TP/SL error: {e}")
            return str(e)



    def execute_order(self, symbol, side, budget_usdt):
        """
        Executes a market order based on a USDT budget.
        Calculates required contracts and sets leverage.
        """
        side = side.upper()
        if side == "WAIT":
            return "No order executed (WAIT signal)."

        try:
            # 1. Refresh config and load market data
            self.exchange.load_markets()
            market = self.exchange.market(symbol)
            current_price = self.get_ticker(symbol)
            
            if not current_price:
                return "Error: Could not fetch price for contract calculation."

            # 2. Set Leverage (Crucial for small budgets)
            try:
                self.exchange.set_leverage(self.leverage, symbol, {'mgnMode': 'cross'})
                logging.info(f"Trader: Leverage set to {self.leverage}x for {symbol}")
            except Exception as e:
                logging.warning(f"Trader: Could not set leverage (might be already set): {e}")

            # 3. Calculate Contracts (sz)
            # OKX Formula: sz = amount_usdt / (contract_size * price)
            contract_pt_value = float(market.get('contractSize', 1))
            
            # We want to spend 'budget_usdt', but with leverage we have more power
            # To be safe, we calculate contracts based on nominal value
            raw_sz = budget_usdt / (contract_pt_value * current_price)
            
            # Multiply by leverage to see how much we CAN buy
            total_sz = raw_sz * self.leverage
            
            # Floor to minimum lot size
            min_sz = float(market['limits']['amount']['min'] or 1)
            sz = max(min_sz, round(total_sz / min_sz) * min_sz)
            
            actual_cost = sz * contract_pt_value * current_price / self.leverage
            logging.info(f"Trader: Budget ${budget_usdt} -> Target {sz} contracts (~${actual_cost:.2f} margin)")

            # 4. Prepare params
            # Important: tdMode depends on account level and market type
            # acctLv '1' is simple (only 'cash'), acctLv '2'/'3' permit 'cross' or 'isolated'
            td_mode = 'cash' if (self.acct_lv == '1' and m_type == 'spot') else 'cross'
            params = {'tdMode': td_mode}
            
            m_type = market.get('type')
            is_derivative = m_type in ['swap', 'future']

            if is_derivative and self.pos_mode == 'long_short_mode':
                params['posSide'] = 'long' if side == "BUY" else 'short'
            
            logging.info(f"Trader: Executing {side} on {symbol} (Contracts: {sz})")
            
            if side == "BUY":
                return self.exchange.create_market_buy_order(symbol, sz, params)
            elif side == "SELL":
                return self.exchange.create_market_sell_order(symbol, sz, params)
                
            return f"Unknown side: {side}"
                
        except Exception as e:
            error_msg = f"Execution Error: {str(e)}"
            logging.error(f"Trader: {error_msg}")
            return error_msg



# Initialize trader
trader = Trader()
