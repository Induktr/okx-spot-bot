import json
import logging
import os
from src.app.config import config
from src.features.trade_executor.trader import traders

class ProfitScout:
    """
    Monitors trade history across all active exchanges to find 'viral-worthy' wins.
    Matches the Task 1 requirement: ROI > 30% trigger.
    """
    def __init__(self, processed_trades_file="src/data/processed_wins.json"):
        self.processed_trades_file = processed_trades_file
        self._ensure_file()

    def _ensure_file(self):
        if not os.path.exists(os.path.dirname(self.processed_trades_file)):
            os.makedirs(os.path.dirname(self.processed_trades_file))
        if not os.path.exists(self.processed_trades_file):
            with open(self.processed_trades_file, "w") as f:
                json.dump([], f)

    def get_already_processed_ids(self):
        with open(self.processed_trades_file, "r") as f:
            return set(json.load(f))

    def mark_as_processed(self, trade_id):
        processed = list(self.get_already_processed_ids())
        processed.append(trade_id)
        with open(self.processed_trades_file, "w") as f:
            json.dump(processed, f)

    def find_big_wins(self):
        """
        Scans all exchanges for trades with ROI > threshold.
        Extracts: Symbol, Entry Price, Exit Price, Profit, Timestamp.
        """
        big_wins = []
        processed_ids = self.get_already_processed_ids()

        for eid, t in traders.items():
            try:
                history = t.get_history(limit=50)
                for trade in history:
                    # OKX/Binance specific PnL check
                    # We look for trades that have positive PnL and match our ROI criteria
                    # Note: Calculating ROI requires cost vs pnl
                    trade_id = trade.get('id', trade.get('info', {}).get('fillId'))
                    if not trade_id or trade_id in processed_ids:
                        continue
                    
                    pnl = float(trade.get('pnl', 0) or 0)
                    cost = float(trade.get('cost', 0) or 1) # Avoid div by zero
                    
                    if cost > 0:
                        roi = (pnl / cost) * 100
                        if roi >= config.PROFIT_SCOUT_ROI_THRESHOLD:
                            win_data = {
                                "id": trade_id,
                                "exchange": eid,
                                "symbol": trade['symbol'],
                                "pnl": round(pnl, 2),
                                "roi": round(roi, 2),
                                "entry_price": trade.get('price'), # This might be the exit price if it's a 'close' trade
                                "timestamp": trade.get('timestamp'),
                                "raw_trade": trade
                            }
                            big_wins.append(win_data)
                            self.mark_as_processed(trade_id)
                            logging.info(f"🏆 PROFIT SCOUT: Found Big Win on {trade['symbol']} ({roi:.2f}% ROI)")
            except Exception as e:
                logging.error(f"ProfitScout error on {eid}: {e}")

        return big_wins

profit_scout = ProfitScout()
