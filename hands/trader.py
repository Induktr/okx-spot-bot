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
        self.acct_lv = '1' # Default to Simple
        
        if config.USE_SANDBOX:
            self.exchange.set_sandbox_mode(True)
            self.exchange.headers = {
                'x-simulated-trading': '1'
            }
            
            try:
                account_config = self.exchange.private_get_account_config()
                config_data = account_config.get('data', [{}])[0]
                self.acct_lv = config_data.get('acctLv', '1')
                self.pos_mode = config_data.get('posMode', 'net_mode')
                
                logging.info(f"Trader: OKX Account Mode: {self.acct_lv}, Position Mode: {self.pos_mode}")
            except Exception as e:
                logging.warning(f"Trader: Could not fetch account configuration: {e}")
            
            logging.info("Trader: OKX Sandbox mode enabled with headers.")

    def get_balance(self):
        """Fetches account balance for USDT."""
        try:
            balance = self.exchange.fetch_balance()
            return balance.get('USDT', {}).get('free', 0.0)
        except Exception as e:
            logging.error(f"Balance fetch error: {e}")
            return 0.0

    def get_ticker(self, symbol=None):
        """Fetches current market price for the symbol."""
        if symbol is None:
            symbol = config.SYMBOL
        try:
            ticker = self.exchange.fetch_ticker(symbol)
            return ticker['last']
        except Exception as e:
            logging.error(f"Ticker fetch error: {e}")
            return None

    def get_positions(self):
        """Fetches all open positions on the account."""
        try:
            # We filter for the symbol we are interested in
            positions = self.exchange.fetch_positions()
            return [p for p in positions if p['symbol'].startswith(config.SYMBOL.split('/')[0])]
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

    def sync_sl_tp(self, pos, tp_pct=0.3, sl_pct=0.2):
        """
        Sets or updates Take Profit and Stop Loss for an existing position.
        Uses separate orders for TP and SL to ensure both are accepted by OKX.
        """
        try:
            symbol = pos['symbol']
            side = pos['side'] # 'long' or 'short'
            entry_price = float(pos['entryPrice'])
            contracts = pos['contracts']
            
            if side == 'long':
                tp_price = entry_price * (1 + tp_pct)
                sl_price = entry_price * (1 - sl_pct)
            else:
                tp_price = entry_price * (1 - tp_pct)
                sl_price = entry_price * (1 + sl_pct)
            
            logging.info(f"Trader: Syncing Hard TP/SL for {symbol}. TP: {tp_price:.2f}, SL: {sl_price:.2f}")
            
            common_params = {
                'tdMode': 'cash' if self.acct_lv == '1' else 'cross',
                'ordType': 'conditional',
                'reduceOnly': True
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


    def execute_order(self, side: str, amount: float, tp_pct=0.3, sl_pct=0.2):
        """
        Executes a market order with attached TP/SL.
        side: 'BUY' or 'SELL'
        amount: Volume to trade
        """
        side = side.upper()
        if side == "WAIT":
            return "No order executed (WAIT signal)."

        try:
            symbol = config.SYMBOL
            td_mode = 'cash' if self.acct_lv == '1' else 'cross'
            current_price = self.get_ticker(symbol)
            
            params = {
                'tdMode': td_mode 
            }
            
            if td_mode != 'cash' and self.pos_mode == 'long_short_mode':
                params['posSide'] = 'long' if side == "BUY" else 'short'
            
            if current_price:
                if side == "BUY":
                    tp_price = current_price * (1 + tp_pct)
                    sl_price = current_price * (1 - sl_pct)
                else:
                    tp_price = current_price * (1 - tp_pct)
                    sl_price = current_price * (1 + sl_pct)

                params.update({
                    'tpTriggerPx': f"{tp_price:.2f}",
                    'tpOrdPx': '-1',
                    'slTriggerPx': f"{sl_price:.2f}",
                    'slOrdPx': '-1'
                })
                logging.info(f"Trader: Attaching SL({sl_price:.2f}) and TP({tp_price:.2f})")
            
            logging.info(f"Trader: Sending {side} order for {symbol} (Amount: {amount})")
            
            if side == "BUY":
                return self.exchange.create_market_buy_order(symbol, amount, params)
            elif side == "SELL":
                return self.exchange.create_market_sell_order(symbol, amount, params)
                
            return f"Unknown side: {side}"
                
        except Exception as e:
            error_msg = f"Execution Error: {str(e)}"
            logging.error(f"Trader: {error_msg}")
            return error_msg

# Initialize trader
trader = Trader()
